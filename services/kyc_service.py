"""
سرویس مشترک احراز هویت (KYC) — منبع واحد برای هم جریان گفتگویی ربات (handlers/kyc.py)
و هم API مینی‌اپ (api.py). مسئولیت‌ها:
  1) آپلود مدرک هویتی و سلفی در باکت خصوصی Supabase Storage
  2) ثبت پروفایل کاربر با وضعیت اولیهٔ "pending"
  3) ارسال درخواست بررسی به ادمین (همراه با خودِ عکس‌ها) از طریق ربات مدیریت
"""
import logging
from typing import Optional

from config import ADMIN_CHAT_IDS, USDT_KYC_DOCS_BUCKET
from services import supabase_service as db

logger = logging.getLogger(__name__)


async def complete_kyc(
    *,
    chat_id: int,
    first_name: str,
    last_name: str,
    phone: str,
    payment_info: str,
    id_doc_bytes: bytes,
    id_doc_ext: str,
    id_doc_content_type: str,
    selfie_bytes: bytes,
    selfie_ext: str,
    selfie_content_type: str,
) -> bool:
    """
    مدارک را در باکت خصوصی آپلود، پروفایل را ثبت و درخواست بررسی را برای ادمین
    ارسال می‌کند. خروجی: موفقیت‌آمیز بودن یا نه.
    """
    id_doc_path = db.upload_private_file(
        USDT_KYC_DOCS_BUCKET, id_doc_bytes, f"{chat_id}_id_document.{id_doc_ext}", id_doc_content_type
    )
    selfie_path = db.upload_private_file(
        USDT_KYC_DOCS_BUCKET, selfie_bytes, f"{chat_id}_selfie.{selfie_ext}", selfie_content_type
    )
    if not id_doc_path or not selfie_path:
        logger.error("آپلود مدارک KYC برای کاربر %s ناموفق بود", chat_id)
        return False

    try:
        db.create_user_profile(
            chat_id=chat_id,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            payment_info=payment_info,
            id_document_path=id_doc_path,
            selfie_path=selfie_path,
        )
    except Exception:
        logger.exception("ثبت پروفایل KYC ناموفق بود")
        return False

    await _notify_admins_kyc_review(
        chat_id=chat_id,
        full_name=f"{first_name} {last_name}".strip(),
        phone=phone,
        payment_info=payment_info,
        id_doc_bytes=id_doc_bytes,
        selfie_bytes=selfie_bytes,
    )
    return True


async def save_basic_profile(*, chat_id: int, first_name: str, last_name: str, phone: str) -> None:
    """مینی‌اپ — مرحلهٔ اول: فقط اطلاعات پایه، بدون نیاز به مدرک یا اطلاعات
    پرداخت. کافی است تا کاربر بتواند سفارش‌های زیر آستانهٔ احراز هویت را ثبت
    کند (services/supabase_service.has_basic_profile)."""
    db.save_basic_profile(chat_id=chat_id, first_name=first_name, last_name=last_name, phone=phone)


async def submit_identity_verification(
    *,
    chat_id: int,
    payment_info: Optional[str],
    id_doc_bytes: bytes,
    id_doc_ext: str,
    id_doc_content_type: str,
    selfie_bytes: bytes,
    selfie_ext: str,
    selfie_content_type: str,
) -> bool:
    """مینی‌اپ — مرحلهٔ دوم (اختیاری، فقط وقتی مبلغ سفارش از آستانه بیشتر است):
    مدرک هویتی + سلفی، به‌اضافهٔ اطلاعات پرداخت که *اختیاری* است. نیازمند این
    است که پروفایل پایه (نام/نام‌خانوادگی/شماره تماس) از قبل با
    save_basic_profile ثبت شده باشد."""
    profile = db.get_user_profile(chat_id)
    if not profile or not profile.get("first_name"):
        logger.error("تلاش برای ارسال مدارک احراز هویت بدون پروفایل پایه — chat_id=%s", chat_id)
        return False

    id_doc_path = db.upload_private_file(
        USDT_KYC_DOCS_BUCKET, id_doc_bytes, f"{chat_id}_id_document.{id_doc_ext}", id_doc_content_type
    )
    selfie_path = db.upload_private_file(
        USDT_KYC_DOCS_BUCKET, selfie_bytes, f"{chat_id}_selfie.{selfie_ext}", selfie_content_type
    )
    if not id_doc_path or not selfie_path:
        logger.error("آپلود مدارک احراز هویت برای کاربر %s ناموفق بود", chat_id)
        return False

    try:
        db.save_identity_verification(chat_id, id_doc_path, selfie_path, payment_info=payment_info or None)
    except Exception:
        logger.exception("ثبت مدارک احراز هویت ناموفق بود")
        return False

    full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
    await _notify_admins_kyc_review(
        chat_id=chat_id,
        full_name=full_name,
        phone=profile.get("phone") or "—",
        payment_info=payment_info or "—",
        id_doc_bytes=id_doc_bytes,
        selfie_bytes=selfie_bytes,
    )
    return True


async def _notify_admins_kyc_review(
    *,
    chat_id: int,
    full_name: str,
    phone: str,
    payment_info: str,
    id_doc_bytes: bytes,
    selfie_bytes: bytes,
) -> None:
    # ایمپورت داخل تابع برای جلوگیری از وابستگی حلقوی
    from services.usdt_order_service import get_admin_bot
    from keyboards import kyc_review_keyboard

    try:
        bot = get_admin_bot()
    except RuntimeError:
        logger.exception("ربات مدیریت پیکربندی نشده؛ درخواست بررسی KYC ارسال نشد.")
        return

    caption_summary = (
        f"🆕 *درخواست بررسی هویت جدید*\n\n"
        f"نام: {full_name}\n"
        f"شمارهٔ تماس: {phone}\n"
        f"اطلاعات پرداخت: {payment_info}\n"
        f"چت‌آیدی: `{chat_id}`"
    )

    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_photo(chat_id=admin_id, photo=id_doc_bytes, caption=f"🪪 مدرک هویتی — {full_name}")
            await bot.send_photo(chat_id=admin_id, photo=selfie_bytes, caption=f"🤳 سلفی — {full_name}")
            await bot.send_message(
                chat_id=admin_id,
                text=caption_summary,
                parse_mode="Markdown",
                reply_markup=kyc_review_keyboard(chat_id),
            )
        except Exception:
            logger.exception("خطا در ارسال درخواست بررسی KYC به ادمین %s", admin_id)
