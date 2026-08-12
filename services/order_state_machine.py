"""
State machine سفارش‌های تتر — SARAF 2.0 Spec §5.

منبع نهایی حقیقت برای transitionهای مجاز، trigger پایگاه‌داده
(`validate_usdt_order_status_transition` در migration
20260811_001_order_hardening.sql) است — چون حتی اگر یک مسیر کد (مثلاً یک اسکریپت
ادمین جدید در آینده) این ماژول را دور بزند، دیتابیس باز هم جلوی transition نامعتبر
را می‌گیرد.

این ماژول همان جدول را در پایتون تکرار (mirror) می‌کند تا:
  1) خطای «حالت نامعتبر» زودتر (قبل از رفتن به دیتابیس) و با پیام فارسی مناسب کاربر
     بازگردانده شود.
  2) به‌صورت مستقل و بدون نیاز به دیتابیس واقعی قابل تست باشد.

⚠️ اگر trigger دیتابیس تغییر کند، این دیکشنری هم باید هم‌زمان به‌روزرسانی شود.
"""
from __future__ import annotations

ALL_STATUSES = {
    "pending",
    "payment_pending",
    "payment_submitted",
    "under_review",
    "confirmed",
    "approved",
    "processing",
    "completed",
    "cancelled",
    "rejected",
    "expired",
    "failed",
}

TERMINAL_STATUSES = {"completed", "cancelled", "rejected", "expired", "failed"}

# دقیقاً منعکس‌کنندهٔ CASE WHEN های trigger پایگاه‌داده
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"payment_pending", "payment_submitted", "under_review", "confirmed", "cancelled", "rejected", "expired", "failed"},
    "payment_pending": {"payment_submitted", "under_review", "cancelled", "expired", "failed"},
    "payment_submitted": {"under_review", "confirmed", "approved", "cancelled", "rejected", "failed"},
    "under_review": {"approved", "confirmed", "cancelled", "rejected", "failed"},
    "confirmed": {"processing", "completed", "cancelled", "failed"},
    "approved": {"processing", "cancelled", "failed"},
    "processing": {"completed", "failed", "cancelled"},
    # وضعیت‌های پایانی — هیچ transition خروجی مجاز نیست
    "completed": set(),
    "cancelled": set(),
    "rejected": set(),
    "expired": set(),
    "failed": set(),
}


class InvalidStateTransition(ValueError):
    def __init__(self, from_status: str, to_status: str):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Invalid USDT order status transition: {from_status} -> {to_status}")


def is_valid_transition(from_status: str, to_status: str) -> bool:
    if from_status == to_status:
        return True  # no-op، دیتابیس هم این را مجاز می‌داند
    if from_status not in _ALLOWED_TRANSITIONS or to_status not in ALL_STATUSES:
        return False
    return to_status in _ALLOWED_TRANSITIONS[from_status]


def validate_transition(from_status: str, to_status: str) -> None:
    if not is_valid_transition(from_status, to_status):
        raise InvalidStateTransition(from_status, to_status)


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES
