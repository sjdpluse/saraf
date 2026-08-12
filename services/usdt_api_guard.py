"""
USDT Mini App API hardening — نصب می‌شود قبل از register شدن route های FastAPI.

معماری (به‌روزرسانی‌شده — SARAF 2.0 Spec §26):
  - تنها یک منطق monkey-patch باقی مانده: patch کردن FastAPI.post برای تزریق
    خودکار Dependency های auth/idempotency روی مسیرهای quote و order، چون این
    پروژه route ها را با دکوریتور @app.post ثبت می‌کند و امکان تزریق دستی
    Depends() در هر endpoint بدون تغییر امضای هر تابع وجود ندارد؛ این الگو در
    خود این‌جا و قبلاً هم استفاده شده بود (کم‌ریسک، چون فقط dependencies اضافه
    می‌کند، رفتار endpoint را تغییر نمی‌دهد).
  - patch کردن usdt_service.get_buy_quote/get_sell_quote: وقتی context یک سفارش
    فعال باشد (یعنی endpoint فعلی /orders/buy یا /orders/sell است)، این توابع به
    جای محاسبهٔ نرخ زنده، Quote از قبل ذخیره‌شده در دیتابیس را بازسازی می‌کنند —
    این دقیقاً همان مکانیزمی است که تضمین می‌کند rate/fee/total ارسالی Client
    هرگز مستقیماً اعتماد نشود.

منطق idempotency/duplicate-order که قبلاً این‌جا (با monkey-patch کردن
usdt_order_service.create_buy_order/create_sell_order و db.insert_usdt_order)
تکرار شده بود، حذف و به‌طور کامل به services/usdt_order_service.py منتقل شد —
تنها منبع idempotency حالا همان‌جاست و توسط هم ربات و هم مینی‌اپ استفاده می‌شود
(به services/quote_service.py هم برای منطق مشترک Quote مراجعه کنید).
"""
from __future__ import annotations

import contextvars
import functools
import json
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, FastAPI

from config import BOT_TOKEN
from services import supabase_service as db
from services import webapp_auth, usdt_service, quote_service, rate_limiter
from services.money import D, to_float, quantize_afn
from services.api_errors import ApiError

_quote_context: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("saraf_quote_context", default=None)
_order_context: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("saraf_order_context", default=None)

_QUOTE_ERROR_STATUS = {
    "QUOTE_NOT_FOUND": 400,
    "QUOTE_CONSUMED": 409,
    "QUOTE_EXPIRED": 409,
    "QUOTE_MISMATCH": 400,
    "QUOTE_STORE_FAILED": 503,
}


def _raise_quote_error(exc: "quote_service.QuoteError") -> None:
    raise ApiError(status_code=_QUOTE_ERROR_STATUS.get(exc.code, 400), code=exc.code, message=exc.message)


def get_order_context() -> Optional[dict]:
    """برای استفادهٔ api.py: idempotency_key/quote_id مربوط به درخواست جاری را
    برمی‌گرداند (یا None اگر این دو Dependency فعال نبوده‌اند)."""
    return _order_context.get()


def _idempotency_key(raw: Optional[str]) -> str:
    if not raw or len(raw.strip()) < 16 or len(raw.strip()) > 200:
        raise ApiError(status_code=400, code="IDEMPOTENCY_KEY_REQUIRED", message="Idempotency-Key معتبر برای ثبت سفارش الزامی است.")
    return raw.strip()


async def _guard_quote(request: Request, x_telegram_init_data: Optional[str] = Header(None)) -> None:
    try:
        user = webapp_auth.verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise ApiError(status_code=401, code="UNAUTHORIZED", message=str(exc))
    rate_limiter.enforce("quote", request, identity=str(user["id"]))
    _quote_context.set({"chat_id": user["id"]})


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
    body = await request.body()
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise ApiError(status_code=400, code="VALIDATION_ERROR", message="بدنهٔ درخواست نامعتبر است.")
    request._body = body
    quote_id, amount = payload.get("quote_id"), payload.get("amount")
    if not isinstance(quote_id, int) or not isinstance(amount, (int, float)):
        raise ApiError(status_code=400, code="VALIDATION_ERROR", message="quote_id و amount برای ثبت سفارش الزامی است.")
    action = "buy" if request.url.path.endswith("/buy") else "sell"
    try:
        quote_row = quote_service.load_and_validate(user["id"], quote_id, action, amount)
    except quote_service.QuoteError as exc:
        _raise_quote_error(exc)
    _order_context.set({"chat_id": user["id"], "key": key, "quote_id": quote_id, "quote": quote_row})


def _patch_quote_service() -> None:
    if getattr(usdt_service, "_saraf_quote_guard_installed", False):
        return
    original_buy, original_sell = usdt_service.get_buy_quote, usdt_service.get_sell_quote

    async def guarded_buy(amount):
        ctx = _order_context.get()
        if ctx and ctx["quote"]["order_type"] == "buy":
            # سفارش از یک Quote از قبل ذخیره‌شده در دیتابیس تغذیه می‌شود — rate/fee/total
            # از همان رکورد بازسازی می‌شوند، نه از amount ارسالی Client؛ محاسبه با Decimal.
            q = ctx["quote"]
            rate = D(q["usd_rate"])
            base = D(q["usdt_amount"]) * rate
            fee_afn = D(q["total_afn"]) - base
            return {"amount": to_float(D(q["usdt_amount"])), "usd_rate": to_float(rate),
                    "fee_percent": to_float(D(q["fee_percent"] or 0)), "base_afn": to_float(quantize_afn(base)),
                    "fee_afn": to_float(quantize_afn(fee_afn)),
                    "total_afn": to_float(D(q["total_afn"])), "total_usd": to_float(D(q["total_usd"])),
                    "quote_id": q["id"], "expires_at": q["expires_at"]}
        ctx = _quote_context.get()
        quote = await original_buy(amount)
        return quote_service.create_quote(ctx["chat_id"], "buy", amount, quote) if ctx else quote

    async def guarded_sell(amount):
        ctx = _order_context.get()
        if ctx and ctx["quote"]["order_type"] == "sell":
            q = ctx["quote"]
            return {"amount": to_float(D(q["usdt_amount"])), "usd_rate": to_float(D(q["usd_rate"])),
                    "total_afn": to_float(D(q["total_afn"])), "total_usd": to_float(D(q["total_usd"])),
                    "quote_id": q["id"], "expires_at": q["expires_at"]}
        ctx = _quote_context.get()
        quote = await original_sell(amount)
        return quote_service.create_quote(ctx["chat_id"], "sell", amount, quote) if ctx else quote

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
