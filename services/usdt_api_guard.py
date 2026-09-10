"""Stablecoin Mini App API hardening.

Legacy /api/usdt/* paths remain for compatibility. The guard reads `asset` from
raw request bodies, binds quotes to that asset, validates transfer networks, and
enforces payment-provider rules before api.py can create an order.
"""
from __future__ import annotations

import contextvars
import functools
import json
from typing import Optional

from fastapi import Depends, Header, Request, FastAPI

from config import BOT_TOKEN
from services import (
    quote_service,
    rate_limiter,
    stablecoin_networks,
    usdt_service,
    wallet_validator,
    webapp_auth,
)
from services.money import D, to_float, quantize_afn, quantize_usd
from services.api_errors import ApiError

_quote_context: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("saraf_quote_context", default=None)
_order_context: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("saraf_order_context", default=None)

AZIZI_MIN_STABLECOIN_AMOUNT = 500
_ALLOWED_ONLINE_PROVIDERS = {"hesabpay", "azizi"}

_BUY_PRICING_NUMERIC_FIELDS = (
    "market_margin_usd",
    "supplier_profit_usd",
    "saraf_profit_usd",
    "customer_discount_usd",
    "supplier_payout_usd",
    "market_price_usd",
    "supplier_profit_afn",
    "saraf_profit_afn",
    "customer_discount_afn",
    "supplier_payout_afn",
    "market_price_afn",
)

_QUOTE_ERROR_STATUS = {
    "QUOTE_NOT_FOUND": 400,
    "QUOTE_CONSUMED": 409,
    "QUOTE_EXPIRED": 409,
    "QUOTE_MISMATCH": 400,
    "QUOTE_ASSET_INVALID": 400,
    "QUOTE_ASSET_MISMATCH": 409,
    "QUOTE_STORE_FAILED": 503,
}


def _raise_quote_error(exc: "quote_service.QuoteError") -> None:
    raise ApiError(status_code=_QUOTE_ERROR_STATUS.get(exc.code, 400), code=exc.code, message=exc.message)


def get_order_context() -> Optional[dict]:
    return _order_context.get()


def _idempotency_key(raw: Optional[str]) -> str:
    if not raw or len(raw.strip()) < 16 or len(raw.strip()) > 200:
        raise ApiError(
            status_code=400,
            code="IDEMPOTENCY_KEY_REQUIRED",
            message="Idempotency-Key معتبر برای ثبت سفارش الزامی است.",
        )
    return raw.strip()


def _normalize_asset(raw: Optional[str]) -> str:
    try:
        return usdt_service.normalize_asset(raw)
    except usdt_service.StablecoinAssetError as exc:
        raise ApiError(status_code=400, code="ASSET_NOT_SUPPORTED", message=str(exc))


def _validate_online_provider(payload: dict, action: str, amount: float) -> Optional[str]:
    """Validate the concrete online provider from the raw body.

    api.py intentionally keeps the legacy public vocabulary (``online``), so the
    provider-specific value is validated here before Pydantic discards extra
    fields. This makes the Azizi threshold a server-side rule rather than merely
    a UI condition.
    """
    method_key = "payment_method" if action == "buy" else "receive_method"
    provider_key = "payment_provider" if action == "buy" else "receive_provider"
    method = str(payload.get(method_key) or "").strip()

    if method != "online":
        return None

    provider = str(payload.get(provider_key) or "").strip().lower()
    if provider not in _ALLOWED_ONLINE_PROVIDERS:
        raise ApiError(
            status_code=400,
            code="ONLINE_PROVIDER_REQUIRED",
            message="روش پرداخت/دریافت آنلاین مشخص نیست؛ لطفاً حساب‌پی یا عزیزی بانک را انتخاب کنید.",
        )

    if provider == "azizi" and amount <= AZIZI_MIN_STABLECOIN_AMOUNT:
        raise ApiError(
            status_code=400,
            code="AZIZI_MIN_AMOUNT",
            message=f"عزیزی بانک فقط برای معاملات بیشتر از {AZIZI_MIN_STABLECOIN_AMOUNT} فعال است. برای این مبلغ از حساب‌پی استفاده کنید.",
        )
    return provider


async def _json_body(request: Request) -> dict:
    body = await request.body()
    request._body = body
    try:
        return json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise ApiError(status_code=400, code="VALIDATION_ERROR", message="بدنهٔ درخواست نامعتبر است.")


async def _guard_quote(request: Request, x_telegram_init_data: Optional[str] = Header(None)) -> None:
    try:
        user = webapp_auth.verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise ApiError(status_code=401, code="UNAUTHORIZED", message=str(exc))
    rate_limiter.enforce("quote", request, identity=str(user["id"]))
    payload = await _json_body(request)
    asset = _normalize_asset(payload.get("asset"))
    _quote_context.set({"chat_id": user["id"], "asset": asset})


async def _guard_order(
    request: Request,
    x_telegram_init_data: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> None:
    try:
        user = webapp_auth.verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise ApiError(status_code=401, code="UNAUTHORIZED", message=str(exc))
    rate_limiter.enforce("order", request, identity=str(user["id"]))
    key = _idempotency_key(idempotency_key)
    payload = await _json_body(request)

    quote_id, amount = payload.get("quote_id"), payload.get("amount")
    if not isinstance(quote_id, int) or not isinstance(amount, (int, float)):
        raise ApiError(status_code=400, code="VALIDATION_ERROR", message="quote_id و amount برای ثبت سفارش الزامی است.")

    asset = _normalize_asset(payload.get("asset"))
    action = "buy" if request.url.path.endswith("/buy") else "sell"
    provider = _validate_online_provider(payload, action, float(amount))
    try:
        quote_row = quote_service.load_and_validate(user["id"], quote_id, action, amount, asset=asset)
    except quote_service.QuoteError as exc:
        _raise_quote_error(exc)

    exchange_name = str(payload.get("exchange_name") or "").strip()
    if not exchange_name:
        raise ApiError(status_code=400, code="VALIDATION_ERROR", message="نام صرافی یا کیف پول الزامی است.")

    try:
        network = stablecoin_networks.validate_network(
            asset,
            str(payload.get("network") or ""),
            direction=action,
        )
        if action == "buy":
            wallet_validator.validate_wallet_address(network, str(payload.get("wallet_address") or ""))
    except (ValueError, wallet_validator.WalletValidationError) as exc:
        raise ApiError(status_code=400, code="NETWORK_OR_WALLET_INVALID", message=str(exc))

    _order_context.set(
        {
            "chat_id": user["id"],
            "key": key,
            "quote_id": quote_id,
            "quote": quote_row,
            "asset": asset,
            "network": network,
            "online_provider": provider,
        }
    )


def _patch_quote_service() -> None:
    if getattr(usdt_service, "_saraf_quote_guard_installed", False):
        return
    original_buy, original_sell = usdt_service.get_buy_quote, usdt_service.get_sell_quote

    async def guarded_buy(amount, asset=None):
        ctx = _order_context.get()
        if ctx and ctx["quote"]["order_type"] == "buy":
            q = ctx["quote"]
            q_asset = _normalize_asset(q.get("asset"))
            q_amount = D(q["usdt_amount"])
            rate = D(q["usd_rate"])
            base = q_amount * rate
            total_afn = D(q["total_afn"])
            total_usd = D(q["total_usd"])
            customer_fee_afn = total_afn - base
            customer_fee_usd = total_usd - q_amount

            result = {
                "asset": q_asset,
                "amount": to_float(q_amount),
                "usd_rate": to_float(rate),
                "fee_percent": to_float(D(q["fee_percent"] or 0)),
                "base_afn": to_float(quantize_afn(base)),
                # Legacy fee_afn now represents the full amount charged above
                # principal, not Saraf's net-profit share.
                "fee_afn": to_float(quantize_afn(customer_fee_afn)),
                "customer_fee_usd": to_float(quantize_usd(customer_fee_usd)),
                "customer_fee_afn": to_float(quantize_afn(customer_fee_afn)),
                "total_afn": to_float(total_afn),
                "total_usd": to_float(total_usd),
                "payable_usd": to_float(total_usd),
                "quote_id": q["id"],
                "expires_at": q["expires_at"],
            }
            if q.get("pricing_model") is not None:
                result["pricing_model"] = q["pricing_model"]
            for field in _BUY_PRICING_NUMERIC_FIELDS:
                if q.get(field) is not None:
                    result[field] = to_float(D(q[field]))
            return result

        qctx = _quote_context.get()
        selected_asset = _normalize_asset(asset or (qctx or {}).get("asset"))
        quote = await original_buy(amount, selected_asset)
        return (
            quote_service.create_quote(qctx["chat_id"], "buy", amount, quote, asset=selected_asset)
            if qctx
            else quote
        )

    async def guarded_sell(amount, asset=None):
        ctx = _order_context.get()
        if ctx and ctx["quote"]["order_type"] == "sell":
            q = ctx["quote"]
            q_asset = _normalize_asset(q.get("asset"))
            return {
                "asset": q_asset,
                "amount": to_float(D(q["usdt_amount"])),
                "usd_rate": to_float(D(q["usd_rate"])),
                "total_afn": to_float(D(q["total_afn"])),
                "total_usd": to_float(D(q["total_usd"])),
                "receivable_usd": to_float(D(q["total_usd"])),
                "quote_id": q["id"],
                "expires_at": q["expires_at"],
            }
        qctx = _quote_context.get()
        selected_asset = _normalize_asset(asset or (qctx or {}).get("asset"))
        quote = await original_sell(amount, selected_asset)
        return (
            quote_service.create_quote(qctx["chat_id"], "sell", amount, quote, asset=selected_asset)
            if qctx
            else quote
        )

    usdt_service.get_buy_quote, usdt_service.get_sell_quote = guarded_buy, guarded_sell
    usdt_service._saraf_quote_guard_installed = True


def install() -> None:
    _patch_quote_service()
    if getattr(FastAPI, "_saraf_post_guard_installed", False):
        return
    original_post = FastAPI.post

    @functools.wraps(original_post)
    def guarded_post(self, path: str, *args, **kwargs):
        deps = list(kwargs.pop("dependencies", []) or [])
        if path == "/api/usdt/quote":
            deps.append(Depends(_guard_quote))
        elif path in ("/api/usdt/orders/buy", "/api/usdt/orders/sell"):
            deps.append(Depends(_guard_order))
        return original_post(self, path, *args, dependencies=deps, **kwargs)

    FastAPI.post = guarded_post
    FastAPI._saraf_post_guard_installed = True
