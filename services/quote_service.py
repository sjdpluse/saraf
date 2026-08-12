"""
لایهٔ مشترک Quote — SARAF 2.0 Spec §3 (Quote System) + §26 (حذف duplicate logic).

قبلاً منطق ساخت/بارگذاری/مصرف Quote هم داخل usdt_api_guard.py (برای مینی‌اپ) پیاده
شده بود و هم اصلاً برای ربات چت (handlers/usdt.py) وجود نداشت — یعنی نرخی که ربات
به کاربر نشان می‌داد هرگز در دیتابیس ذخیره نمی‌شد و expiry آن فقط سمت کلاینت
(context.user_data) چک می‌شد. این ماژول تنها منبع حقیقت برای Quote است؛ هم ربات و
هم مینی‌اپ از همین توابع استفاده می‌کنند.
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


class QuoteError(ValueError):
    """خطای Quote با یک کد استاندارد (برای نگاشت به error code های API §16)."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def create_quote(chat_id: int, order_type: str, amount: float, quote: dict) -> dict:
    """Quote محاسبه‌شده توسط usdt_service را در دیتابیس ذخیره می‌کند و quote_id +
    expires_at را به آن اضافه می‌کند. amount/rate/fee/total دقیقاً همان چیزی است که
    usdt_service محاسبه کرده — این تابع فقط persist می‌کند، دوباره محاسبه نمی‌کند."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_QUOTE_TTL_SECONDS)
    try:
        res = (
            db.get_client()
            .table("usdt_quotes")
            .insert(
                {
                    "chat_id": chat_id,
                    "order_type": order_type,
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
        logger.exception("خطا در ذخیرهٔ Quote")
        res = None

    if not res or not res.data:
        raise QuoteError("QUOTE_STORE_FAILED", "ذخیرهٔ نرخ موقت ناموفق بود؛ لطفاً دوباره تلاش کنید.")

    quote_id = res.data[0]["id"]
    audit_service.record(
        action="quote_created",
        entity="usdt_quote",
        entity_id=quote_id,
        actor=chat_id,
        after={"order_type": order_type, "usdt_amount": amount, "total_afn": quote.get("total_afn")},
    )
    result = dict(quote)
    result.update({"quote_id": quote_id, "expires_at": expires_at.isoformat()})
    return result


def load_and_validate(chat_id: int, quote_id: int, order_type: str, amount: float) -> dict:
    """Quote را بارگذاری و طبق §3 اعتبارسنجی می‌کند: مالکیت (chat_id)، نوع
    (buy/sell)، وضعیت (active)، انقضا، و تطابق amount. در هر شکست، QuoteError با
    کد مناسب پرتاب می‌شود (نگاشت مستقیم به error code های استاندارد API)."""
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
    """Quote را atomically مصرف می‌کند (status: active -> consumed). شرط
    `.eq("status", "active")` تضمین می‌کند دو مصرف هم‌زمان یک Quote هر دو موفق
    نشوند — فقط اولی که هنوز active می‌بیند ردیف را تغییر می‌دهد."""
    if not quote_id:
        return
    try:
        db.get_client().table("usdt_quotes").update(
            {"status": "consumed", "consumed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", quote_id).eq("status", "active").execute()
        audit_service.record(
            action="quote_consumed", entity="usdt_quote", entity_id=quote_id, actor=chat_id,
            after={"order_id": order_id},
        )
    except Exception:
        logger.exception("خطا در مصرف Quote %s", quote_id)
