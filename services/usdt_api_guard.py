"""USDT Mini App API hardening installed before FastAPI route registration.

The existing API routes are kept backward-compatible at the Python call level,
while this boundary requires a server-issued quote and Idempotency-Key for
Mini App order submissions. Bot/Telegram conversational orders are untouched.
"""
from __future__ import annotations

import contextvars
import functools
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from fastapi import FastAPI

from config import BOT_TOKEN
from services import supabase_service as db
from services import webapp_auth
from services import usdt_service

_QUOTE_TTL_SECONDS = 10 * 60
_quote_context: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("saraf_quote_context", default=None)
_order_context: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("saraf_order_context", default=None)


def _json_number(value):
    return str(value)


def _create_quote(chat_id: int, action: str, amount: float, quote: dict) -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_QUOTE_TTL_SECONDS)
    row = (
        db.get_client().table("usdt_quotes").insert({
            "chat_id": chat_id,
            "order_type": action,
            "usdt_amount": amount,
            "usd_rate": quote["usd_rate"],
            "fee_percent": quote.get("fee_percent", 0),
            "total_afn": quote["total_afn"],
            "total_usd": quote["total_usd"],
            "status": "active",
            "expires_at": expires_at.isoformat(),
        }).execute()
    )
    if not row.data:
        raise HTTPException(status_code=503, detail="ذخیرهٔ نرخ موقت ناموفق بود؛ لطفاً دوباره تلاش کنید.")
    result = dict(quote)
    result["quote_id"] = row.data[0]["id"]
    result["expires_at"] = expires_at.isoformat()
    return result


def _load_quote(chat_id: int, quote_id: int, action: str, amount: float) -> dict:
    res = (
        db.get_client().table("usdt_quotes")
        .select("*")
        .eq("id", quote_id)
        .eq("chat_id", chat_id)
        .eq("order_type", action)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=400, detail="نرخ انتخاب‌شده معتبر نیست.")
    q = res.data[0]
    if q.get("status") != "active":
        raise HTTPException(status_code=409, detail="این نرخ قبلاً استفاده یا منقضی شده است.")
    try:
        expires_at = datetime.fromisoformat(str(q["expires_at"]).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=409, detail="زمان اعتبار نرخ نامعتبر است.")
    if expires_at <= datetime.now(timezone.utc):
        db.get_client().table("usdt_quotes").update({"status": "expired"}).eq("id", quote_id).eq("status", "active").execute()
        raise HTTPException(status_code=409, detail="نرخ انتخاب‌شده منقضی شده است؛ لطفاً نرخ جدید بگیرید.")
    if abs(float(q["usdt_amount"]) - float(amount)) > 1e-12:
        raise HTTPException(status_code=400, detail="مقدار سفارش با نرخ انتخاب‌شده مطابقت ندارد.")
    return q


def _idempotency_key(raw: Optional[str]) -> str:
    if not raw or len(raw.strip()) < 16 or len(raw.strip()) > 200:
        raise HTTPException(status_code=400, detail="Idempotency-Key معتبر برای ثبت سفارش الزامی است.")
    return raw.strip()


async def _guard_quote(
    x_telegram_init_data: Optional[str] = Header(None),
) -> None:
    try:
        user = webapp_auth.verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    _quote_context.set({"chat_id": user["id"]})


async def _guard_order(
    request: Request,
    x_telegram_init_data: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> None:
    try:
        user = webapp_auth.verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    key = _idempotency_key(idempotency_key)
    body = await request.body()
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="بدنهٔ درخواست نامعتبر است.")
    request._body = body

    quote_id = payload.get("quote_id")
    amount = payload.get("amount")
    if not isinstance(quote_id, int) or not isinstance(amount, (int, float)):
        raise HTTPException(status_code=400, detail="quote_id و amount برای ثبت سفارش الزامی است.")

    action = "buy" if request.url.path.endswith("/buy") else "sell"
    quote = _load_quote(user["id"], quote_id, action, amount)
    _order_context.set({
        "chat_id": user["id"],
        "key": key,
        "quote_id": quote_id,
        "quote": quote,
    })


def _patch_quote_service() -> None:
    original_buy = usdt_service.get_buy_quote
    original_sell = usdt_service.get_sell_quote
    if getattr(usdt_service, "_saraf_quote_guard_installed", False):
        return

    async def guarded_buy(amount):
        ctx = _order_context.get()
        if ctx and ctx["quote"]["order_type"] == "buy":
            q = ctx["quote"]
            return {
                "amount": float(q["usdt_amount"]),
                "usd_rate": float(q["usd_rate"]),
                "fee_percent": float(q["fee_percent"] or 0),
                "base_afn": round(float(q["total_afn"]) - float(q["total_usd"]) * 0, 1),
                "fee_afn": round(float(q["total_afn"]) - float(q["usdt_amount"]) * float(q["usd_rate"]), 1),
                "total_afn": float(q["total_afn"]),
                "total_usd": float(q["total_usd"]),
                "quote_id": q["id"],
                "expires_at": q["expires_at"],
            }
        ctx = _quote_context.get()
        quote = await original_buy(amount)
        if ctx:
            return _create_quote(ctx["chat_id"], "buy", amount, quote)
        return quote

    async def guarded_sell(amount):
        ctx = _order_context.get()
        if ctx and ctx["quote"]["order_type"] == "sell":
            q = ctx["quote"]
            return {
                "amount": float(q["usdt_amount"]),
                "usd_rate": float(q["usd_rate"]),
                "total_afn": float(q["total_afn"]),
                "total_usd": float(q["total_usd"]),
                "quote_id": q["id"],
                "expires_at": q["expires_at"],
            }
        ctx = _quote_context.get()
        quote = await original_sell(amount)
        if ctx:
            return _create_quote(ctx["chat_id"], "sell", amount, quote)
        return quote

    usdt_service.get_buy_quote = guarded_buy
    usdt_service.get_sell_quote = guarded_sell
    usdt_service._saraf_quote_guard_installed = True


def _patch_order_service() -> None:
    from services import usdt_order_service

    if getattr(usdt_order_service, "_saraf_order_guard_installed", False):
        return

    original_buy = usdt_order_service.create_buy_order
    original_sell = usdt_order_service.create_sell_order

    async def guarded_buy(**kwargs):
        ctx = _order_context.get()
        if not ctx or kwargs.get("source") != "miniapp":
            return await original_buy(**kwargs)
        existing = (
            db.get_client().table("usdt_orders").select("*")
            .eq("chat_id", ctx["chat_id"]).eq("idempotency_key", ctx["key"])
            .limit(1).execute()
        )
        if existing.data:
            row = existing.data[0]
            return {"order_id": row["id"], "order_code": usdt_order_service.build_order_code(row["id"]), "message": "سفارش قبلی شما برای همین درخواست موجود است.", "risk_level": row.get("risk_level")}
        result = await original_buy(**kwargs)
        if result.get("order_id"):
            db.get_client().table("usdt_orders").update({"idempotency_key": ctx["key"], "quote_id": ctx["quote_id"]}).eq("id", result["order_id"]).execute()
            db.get_client().table("usdt_quotes").update({"status": "consumed", "consumed_at": datetime.now(timezone.utc).isoformat()}).eq("id", ctx["quote_id"]).eq("status", "active").execute()
        return result

    async def guarded_sell(**kwargs):
        ctx = _order_context.get()
        if not ctx or kwargs.get("source") != "miniapp":
            return await original_sell(**kwargs)
        existing = (
            db.get_client().table("usdt_orders").select("*")
            .eq("chat_id", ctx["chat_id"]).eq("idempotency_key", ctx["key"])
            .limit(1).execute()
        )
        if existing.data:
            row = existing.data[0]
            return {"order_id": row["id"], "order_code": usdt_order_service.build_order_code(row["id"]), "message": "سفارش قبلی شما برای همین درخواست موجود است.", "risk_level": row.get("risk_level")}
        result = await original_sell(**kwargs)
        if result.get("order_id"):
            db.get_client().table("usdt_orders").update({"idempotency_key": ctx["key"], "quote_id": ctx["quote_id"]}).eq("id", result["order_id"]).execute()
            db.get_client().table("usdt_quotes").update({"status": "consumed", "consumed_at": datetime.now(timezone.utc).isoformat()}).eq("id", ctx["quote_id"]).eq("status", "active").execute()
        return result

    usdt_order_service.create_buy_order = guarded_buy
    usdt_order_service.create_sell_order = guarded_sell
    usdt_order_service._saraf_order_guard_installed = True


def install() -> None:
    """Patch FastAPI route registration before api.py declares its routes."""
    _patch_quote_service()
    _patch_order_service()
    original_post = FastAPI.post
    if getattr(FastAPI, "_saraf_post_guard_installed", False):
        return

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
