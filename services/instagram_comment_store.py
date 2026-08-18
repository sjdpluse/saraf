"""
Instagram Comment Event Store
=============================

ذخیره‌سازی idempotency برای سیستم پاسخ خودکار Instagram.

هدف:
- یک comment_id فقط یک بار پردازش شود.
- Webhook و Polling هر دو از یک جدول مشترک استفاده کنند.
- اگر بعداً App Published شد و Webhook فعال شد، همان کامنت دوباره
  توسط Polling و Webhook پردازش نشود.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from services import supabase_service as db


logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_unique_violation(exc: Exception) -> bool:
    """
    تشخیص PostgreSQL unique violation.

    Supabase/PostgREST معمولاً code=23505 برمی‌گرداند.
    """
    code = getattr(exc, "code", None)

    if str(code) == "23505":
        return True

    text = str(exc).lower()

    return (
        "23505" in text
        or "duplicate key" in text
        or "unique constraint" in text
        or "already exists" in text
    )


def claim_comment(
    comment_id: str,
    *,
    media_id: Optional[str] = None,
    commenter_id: Optional[str] = None,
    username: Optional[str] = None,
    text: str = "",
    comment_timestamp: Optional[str] = None,
    source: str = "webhook",
) -> bool:
    """
    comment_id را به‌صورت اتمیک claim می‌کند.

    True:
        این اولین بار است که comment_id دیده می‌شود؛ پردازش ادامه پیدا کند.

    False:
        comment_id قبلاً ثبت شده؛ نباید دوباره DM/Reply ارسال شود.

    خطای واقعی Database عمداً swallow نمی‌شود؛ چون در صورت خراب بودن DB
    نباید سیستم وانمود کند که comment قبلاً پردازش شده است.
    """

    comment_id = str(comment_id).strip()

    if not comment_id:
        raise ValueError("comment_id خالی است")

    row = {
        "comment_id": comment_id,
        "media_id": str(media_id) if media_id else None,
        "commenter_id": str(commenter_id) if commenter_id else None,
        "commenter_username": username or None,
        "comment_text": text or "",
        "comment_timestamp": comment_timestamp or None,
        "source": source or "unknown",
        "dm_sent": False,
        "ai_replied": False,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    try:
        (
            db.get_client()
            .table("ig_comment_events")
            .insert(row)
            .execute()
        )

        logger.info(
            "Instagram comment claimed "
            "comment_id=%s source=%s",
            comment_id,
            source,
        )

        return True

    except Exception as exc:
        if _is_unique_violation(exc):
            logger.info(
                "Instagram duplicate comment ignored "
                "comment_id=%s source=%s",
                comment_id,
                source,
            )
            return False

        logger.exception(
            "خطا در claim کردن Instagram comment_id=%s",
            comment_id,
        )
        raise


def mark_comment(
    comment_id: str,
    *,
    dm_sent: Optional[bool] = None,
    ai_replied: Optional[bool] = None,
    processing_error: Optional[str] = None,
) -> None:
    """
    نتیجه پردازش comment را ثبت می‌کند.
    """

    updates: dict = {
        "updated_at": _now_iso(),
        "processed_at": _now_iso(),
    }

    if dm_sent is not None:
        updates["dm_sent"] = bool(dm_sent)

    if ai_replied is not None:
        updates["ai_replied"] = bool(ai_replied)

    if processing_error is not None:
        updates["processing_error"] = processing_error[:1000]

    try:
        (
            db.get_client()
            .table("ig_comment_events")
            .update(updates)
            .eq("comment_id", str(comment_id))
            .execute()
        )

    except Exception:
        logger.exception(
            "خطا در ثبت نتیجه Instagram comment_id=%s",
            comment_id,
        )