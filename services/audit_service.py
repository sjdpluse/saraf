"""
Audit Log عمومی — SARAF 2.0 Spec §6.

`usdt_order_status_history` فقط تغییرات وضعیت سفارش را پوشش می‌دهد. این ماژول
لایهٔ عمومی‌تری است برای هر عملیات حساس دیگر: ساخت/مصرف Quote، بررسی/رد/محدودسازی
KYC، تغییر اطلاعات پرداخت، آپلود رسید، و اکشن‌های ادمین.

اصل طراحی: نوشتن Audit هرگز نباید عملیات اصلی (که موفق شده) را fail کند — فقط لاگ
می‌شود. یک ثبت Audit گم‌شده به‌مراتب بهتر از یک عملیات مالی موفق است که به‌خاطر خطای
ثانویه به کاربر «ناموفق» نشان داده شود.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from services import supabase_service as db

logger = logging.getLogger(__name__)

# فیلدهایی که هرگز نباید خام (unmasked) در Audit Log ذخیره شوند.
_SENSITIVE_KEYS = {"payment_info", "bank_info", "wallet_address", "phone", "tx_proof", "id_document_path", "selfie_path"}


def _mask(value: Any) -> Any:
    if value is None:
        return None
    s = str(value)
    if len(s) <= 4:
        return "*" * len(s)
    return f"{s[:2]}{'*' * (len(s) - 4)}{s[-2:]}"


def mask_dict(data: Optional[dict]) -> Optional[dict]:
    if not data:
        return data
    return {k: (_mask(v) if k in _SENSITIVE_KEYS and v is not None else v) for k, v in data.items()}


def record(
    *,
    action: str,
    entity: str,
    entity_id: Optional[Any] = None,
    actor: Optional[int] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    reason: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """یک رویداد را در جدول audit_log ثبت می‌کند. مقادیر حساس before/after باید قبل
    از فراخوانی با mask_dict() ماسک شده باشند."""
    try:
        db.get_client().table("audit_log").insert(
            {
                "action": action,
                "entity": entity,
                "entity_id": str(entity_id) if entity_id is not None else None,
                "actor": actor,
                "before": before,
                "after": after,
                "reason": reason,
                "request_id": request_id,
            }
        ).execute()
    except Exception:
        logger.exception("خطا در ثبت Audit Log: action=%s entity=%s/%s", action, entity, entity_id)
