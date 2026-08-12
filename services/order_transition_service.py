"""
سرویس مرکزی transition وضعیت سفارش تتر — SARAF 2.0 Spec §5.

طبق مشخصات، تمام status change های سفارش باید فقط از یک تابع واحد
(`transition_order_status`) عبور کنند تا:
  - تاریخچه + actor + reason + timestamp همیشه ثبت شود،
  - transitionهای نامعتبر (مثلاً completed -> pending) زودتر و با پیام مناسب رد شوند،
  - و منطق در دو مسیر (ربات چت / ادمین بات / API) واگرا نشود.

دیتابیس (trigger) همچنان آخرین خط دفاع است؛ این ماژول لایهٔ اول (سریع‌تر، با پیام
بهتر) است، نه جایگزین آن.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from services import supabase_service as db
from services import audit_service
from services.order_state_machine import validate_transition, InvalidStateTransition

logger = logging.getLogger(__name__)


class OrderNotFoundError(LookupError):
    pass


# فیلد timestamp اختصاصی هر وضعیت — اگر برای یک وضعیت timestamp اختصاصی در جدول
# usdt_orders تعریف نشده باشد، فقط ستون status به‌روزرسانی می‌شود.
_TIMESTAMP_FIELD = {
    "confirmed": "confirmed_at",
    "completed": "completed_at",
    "cancelled": "cancelled_at",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def transition_order_status(
    order_id: int,
    to_status: str,
    *,
    changed_by: Optional[int] = None,
    reason: Optional[str] = None,
) -> dict:
    """وضعیت یک سفارش تتر را با اعتبارسنجی state machine تغییر می‌دهد، تاریخچه را
    attribute می‌کند و در audit_log عمومی ثبت می‌کند. سفارش به‌روزشده را برمی‌گرداند.

    Raises:
        OrderNotFoundError: سفارش یافت نشد.
        InvalidStateTransition: transition درخواستی مجاز نیست.
    """
    order = db.get_usdt_order_by_id(order_id)
    if not order:
        raise OrderNotFoundError(f"سفارش {order_id} یافت نشد.")

    from_status = order["status"]
    validate_transition(from_status, to_status)  # اگر نامعتبر باشد، InvalidStateTransition پرتاب می‌شود

    if from_status == to_status:
        # no-op idempotent — سفارش را بدون نوشتن دوبارهٔ تاریخچه برمی‌گرداند
        return order

    extra_fields = {}
    ts_field = _TIMESTAMP_FIELD.get(to_status)
    if ts_field:
        extra_fields[ts_field] = _now_iso()

    db.update_usdt_order_status_audited(
        order_id, to_status, changed_by=changed_by, reason=reason, **extra_fields
    )

    audit_service.record(
        action=f"order_{to_status}",
        entity="usdt_order",
        entity_id=order_id,
        actor=changed_by,
        before={"status": from_status},
        after={"status": to_status},
        reason=reason,
    )

    return {**order, "status": to_status, **extra_fields}
