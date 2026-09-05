"""
لایهٔ مشترک Quote — منبع واحد نرخ موقت برای ربات و مینی‌اپ.

نام جدول‌ها و فیلدهای usdt_* برای سازگاری عقب‌رو حفظ شده‌اند، اما هر Quote از این
پس به asset مشخص (USDT یا USDC) متصل است تا نرخ یک دارایی نتواند برای دارایی دیگر
مصرف شود.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import USDT_QUOTE_VALIDITY_MINUTES
from services import supabase_service as db
from services import audit_service
from services.money import money_equal

logger = logging.getLogger(__name__)

_QUOTE_TTL_SECONDS = int(USDT_QUOTE_VALIDITY_MINUTES * 60)
_SUPPORTED_ASSETS = {"USDT", "USDC"}


class QuoteError(ValueError):
    """خطای Quote با یک کد استاندارد برای نگاشت به API."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _normalize_asset(asset: Optional[str]) -> str:
    value = str(asset or "USDT").strip().upper()
    if value not in _SUPPORTED_ASSETS:
        raise QuoteError("QUOTE_ASSET_INVALID", "دارایی انتخاب‌شده پشتیبانی نمی‌شود.")
    return value


def create_quote(
    chat_id: int,
    order_type: str,
    amount: float,
    quote: dict,
    asset: Optional[str] = None,
) -> dict:
    """Quote محاسبه‌شده را ذخیره و به کاربر، نوع معامله و دارایی متصل می‌کند."""
    asset = _normalize_asset(asset or quote.get("asset"))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_QUOTE_TTL_SECONDS)
    try:
        res = (
            db.get_client()
            .table("usdt_quotes")
            .insert(
                {
                    "chat_id": chat_id,
                    "order_type": order_type,
                    "asset": asset,
                    "usdt_amount": amount,
                    "usd_rate": quote["usd_rate"],
                    "fee_percent": quote.get("fee_percent", 0),
                    "total_afn": quote["total_afn"],
                    "total_usd": quote["total_usd"],
                    "status": "active",
                    "expires_at": expires_at.isoformat(),
                }
            )
            .execute()
        )
    except Exception:
        logger.exception("خطا در ذخیرهٔ Quote برای %s", asset)
        res = None

    if not res or not res.data:
        raise QuoteError("QUOTE_STORE_FAILED", "ذخیرهٔ نرخ موقت ناموفق بود؛ لطفاً دوباره تلاش کنید.")

    quote_id = res.data[0]["id"]
    audit_service.record(
        action="quote_created",
        entity="usdt_quote",
        entity_id=quote_id,
        actor=chat_id,
        after={
            "order_type": order_type,
            "asset": asset,
            "usdt_amount": amount,
            "total_afn": quote.get("total_afn"),
        },
    )
    result = dict(quote)
    result.update({"asset": asset, "quote_id": quote_id, "expires_at": expires_at.isoformat()})
    return result


def load_and_validate(
    chat_id: int,
    quote_id: int,
    order_type: str,
    amount: float,
    asset: Optional[str] = None,
) -> dict:
    """مالکیت، نوع معامله، دارایی، وضعیت، انقضا و amount یک Quote را بررسی می‌کند."""
    asset = _normalize_asset(asset)
    res = (
        db.get_client()
        .table("usdt_quotes")
        .select("*")
        .eq("id", quote_id)
        .eq("chat_id", chat_id)
        .eq("order_type", order_type)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise QuoteError("QUOTE_NOT_FOUND", "نرخ انتخاب‌شده معتبر نیست.")

    q = res.data[0]
    quote_asset = _normalize_asset(q.get("asset"))
    if quote_asset != asset:
        raise QuoteError(
            "QUOTE_ASSET_MISMATCH",
            f"این نرخ برای {quote_asset} صادر شده است؛ لطفاً برای {asset} نرخ جدید بگیرید.",
        )
    if q.get("status") == "consumed":
        raise QuoteError("QUOTE_CONSUMED", "این نرخ قبلاً استفاده شده است.")
    if q.get("status") != "active":
        raise QuoteError("QUOTE_EXPIRED", "این نرخ قبلاً منقضی یا لغو شده است.")

    try:
        expires_at = datetime.fromisoformat(str(q["expires_at"]).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise QuoteError("QUOTE_EXPIRED", "زمان اعتبار نرخ نامعتبر است.")

    if expires_at <= datetime.now(timezone.utc):
        _mark_expired(quote_id, chat_id)
        raise QuoteError("QUOTE_EXPIRED", "نرخ انتخاب‌شده منقضی شده است؛ لطفاً نرخ جدید بگیرید.")

    if not money_equal(q["usdt_amount"], amount):
        raise QuoteError("QUOTE_MISMATCH", "مقدار سفارش با نرخ انتخاب‌شده مطابقت ندارد.")

    q["asset"] = quote_asset
    return q


def _mark_expired(quote_id: int, chat_id: Optional[int] = None) -> None:
    try:
        db.get_client().table("usdt_quotes").update({"status": "expired"}).eq("id", quote_id).eq(
            "status", "active"
        ).execute()
        audit_service.record(action="quote_expired", entity="usdt_quote", entity_id=quote_id, actor=chat_id)
    except Exception:
        logger.exception("خطا در ثبت انقضای Quote %s", quote_id)


def consume(quote_id: Optional[int], *, chat_id: Optional[int] = None, order_id: Optional[int] = None) -> None:
    if not quote_id:
        return
    try:
        db.get_client().table("usdt_quotes").update(
            {"status": "consumed", "consumed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", quote_id).eq("status", "active").execute()
        audit_service.record(
            action="quote_consumed",
            entity="usdt_quote",
            entity_id=quote_id,
            actor=chat_id,
            after={"order_id": order_id},
        )
    except Exception:
        logger.exception("خطا در مصرف Quote %s", quote_id)
