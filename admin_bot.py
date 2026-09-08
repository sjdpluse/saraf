"""ربات مدیریت Saraf برای سفارش‌های USDT / USDC و بررسی KYC."""
import logging
from io import BytesIO

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from config import ADMIN_BOT_TOKEN, ADMIN_CHAT_IDS, BOT_TOKEN, SUPPORT_TELEGRAM_USERNAME
from keyboards import admin_order_complete_keyboard, usdt_rating_keyboard
from services import supabase_service as db
from services import order_transition_service, usdt_service
from services.order_state_machine import InvalidStateTransition

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

_customer_bot: Bot | None = None
_PENDING_COMPLETION_KEY = "pending_order_completion"
_MAX_COMPLETION_FILE_BYTES = 10 * 1024 * 1024

_KYC_STATUS_LABELS = {
    "pending": "🟡 Pending — بررسی نشده",
    "verified": "🔵 Verified — هویت تایید‌شده",
    "trusted": "🟢 Trusted — مشتری معتمد",
    "restricted": "🔴 Restricted — محدودشده",
}


def _get_customer_bot() -> Bot:
    global _customer_bot
    if _customer_bot is None:
        _customer_bot = Bot(token=BOT_TOKEN)
    return _customer_bot


def _is_admin(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id in ADMIN_CHAT_IDS


def _order_asset(order: dict) -> str:
    try:
        return usdt_service.normalize_asset(order.get("asset"))
    except Exception:
        return "USDT"


def _order_code(order: dict) -> str:
    return f"{_order_asset(order)}-{int(order['id']):05d}"


def _save_completion_proof(order_id: int, *, details: str | None, file_id: str | None, file_type: str | None, file_name: str | None) -> bool:
    """Persist completion evidence before changing the order to completed.

    This intentionally does not swallow database errors: if the migration has
    not been applied or Supabase is unavailable, the order remains confirmed.
    """
    try:
        result = (
            db.get_client()
            .table("usdt_orders")
            .update(
                {
                    "completion_tx_details": details,
                    "completion_proof_file_id": file_id,
                    "completion_proof_file_type": file_type,
                    "completion_proof_file_name": file_name,
                }
            )
            .eq("id", order_id)
            .eq("status", "confirmed")
            .execute()
        )
        return bool(result.data)
    except Exception:
        logger.exception("خطا در ذخیره Transaction Details سفارش %s", order_id)
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("این ربات فقط برای مدیریت Saraf است.")
        return
    await update.message.reply_text(
        "✅ ربات مدیریت Saraf متصل شد.\nاز این پس اعلان سفارش‌های USDT / USDC همین‌جا دریافت می‌شود."
    )


def _format_profile_summary(profile: dict) -> str:
    full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "-"
    status_label = _KYC_STATUS_LABELS.get(profile.get("kyc_status"), profile.get("kyc_status", "-"))
    return (
        f"👤 *{full_name}*\n"
        f"{status_label}\n"
        f"📱 {profile.get('phone') or '-'}\n"
        f"💱 {profile.get('successful_orders', 0)} معاملهٔ موفق | {profile.get('cancelled_orders', 0)} لغوشده\n"
        f"💵 حجم کل معاملات استیبل‌کوین: {float(profile.get('total_volume_usdt', 0)):,.0f} USD\n"
        f"⭐ Trust Score: {profile.get('trust_score', 0)}/100\n"
        f"🗓 عضویت: {str(profile.get('joined_at', '-'))[:10]}\n"
        f"چت‌آیدی: `{profile.get('chat_id')}`"
    )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update): return
    if not context.args:
        await update.message.reply_text("استفاده: /profile <chat_id>")
        return
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ چت‌آیدی نامعتبر است.")
        return
    profile = db.get_user_profile(chat_id)
    if not profile:
        await update.message.reply_text("پروفایلی برای این کاربر یافت نشد.")
        return
    await update.message.reply_text(_format_profile_summary(profile), parse_mode=ParseMode.MARKDOWN)


async def review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_admin(update):
        await query.answer("این عملیات فقط برای مدیران مجاز است.", show_alert=True)
        return
    action, order_id_str = query.data.split(":", 1)
    try:
        order_id = int(order_id_str)
    except ValueError:
        await query.answer("شناسهٔ سفارش نامعتبر است.", show_alert=True)
        return
    order = db.get_usdt_order_by_id(order_id)
    if not order:
        await query.answer("سفارش یافت نشد.", show_alert=True)
        return

    asset = _order_asset(order)
    order_code = _order_code(order)
    customer_bot = _get_customer_bot()
    admin_id = update.effective_user.id

    if action in ("admin_confirm", "admin_reject"):
        if order["status"] != "pending":
            await query.answer("این سفارش قبلاً بررسی شده است.", show_alert=True)
            return

        if action == "admin_confirm":
            try:
                order_transition_service.transition_order_status(order_id, "confirmed", changed_by=admin_id)
            except InvalidStateTransition:
                await query.answer("این سفارش قابل تایید نیست (وضعیت تغییر کرده).", show_alert=True)
                return
            await query.answer("تایید شد ✅")
            await query.edit_message_reply_markup(reply_markup=admin_order_complete_keyboard(order_id))
            await query.message.reply_text(
                f"✅ سفارش {order_code} تایید شد.\nبعد از اینکه {asset}/مبلغ را واقعاً برای مشتری ارسال کردی، دکمهٔ «تکمیل شد» را بزن."
            )
            try:
                await customer_bot.send_message(
                    chat_id=order["chat_id"],
                    text=f"✅ سفارش شما (`{order_code}`) تایید و در حال پردازش نهایی است.\nطبق زمان‌بندی اعلام‌شده، ظرف کمتر از ۱ ساعت تکمیل خواهد شد.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                logger.exception("خطا در اطلاع‌رسانی تایید سفارش به کاربر")
        else:
            try:
                order_transition_service.transition_order_status(order_id, "cancelled", changed_by=admin_id, reason="رد شده توسط ادمین")
            except InvalidStateTransition:
                await query.answer("این سفارش قابل رد کردن نیست (وضعیت تغییر کرده).", show_alert=True)
                return
            db.record_order_outcome(order["chat_id"], float(order["usdt_amount"]), success=False)
            await query.answer("رد شد ❌")
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"❌ سفارش {order_code} رد شد.")
            try:
                await customer_bot.send_message(
                    chat_id=order["chat_id"],
                    text=f"⚠️ سفارش شما (`{order_code}`) قابل تایید نبود.\nلطفاً برای پیگیری با پشتیبانی تماس بگیرید: {SUPPORT_TELEGRAM_USERNAME}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                logger.exception("خطا در اطلاع‌رسانی رد سفارش به کاربر")
        return

    if action == "admin_complete":
        if order["status"] != "confirmed":
            await query.answer("این سفارش در وضعیت قابل‌تکمیل نیست.", show_alert=True)
            return
        context.user_data[_PENDING_COMPLETION_KEY] = {
            "order_id": order_id,
            "chat_id": query.message.chat_id,
            "message_id": query.message.message_id,
        }
        await query.answer("Transaction Details لازم است.")
        await query.message.reply_text(
            f"📎 برای تکمیل سفارش {order_code} ابتدا مدرک تراکنش را ارسال کنید.\n\n"
            "یکی از این دو مورد را همین‌جا بفرستید:\n"
            "• Tx Hash / Transaction ID به‌صورت متن\n"
            "• تصویر یا فایل Transaction Details\n\n"
            "تا قبل از دریافت این مدرک، سفارش تکمیل نمی‌شود."
        )
        return


async def completion_proof_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Finish a confirmed order only after an admin supplies transaction proof."""
    if not _is_admin(update) or not update.message:
        return
    pending = context.user_data.get(_PENDING_COMPLETION_KEY)
    if not pending:
        return

    order_id = int(pending["order_id"])
    order = db.get_usdt_order_by_id(order_id)
    if not order or order.get("status") != "confirmed":
        context.user_data.pop(_PENDING_COMPLETION_KEY, None)
        await update.message.reply_text("این سفارش دیگر در وضعیت قابل‌تکمیل نیست.")
        return

    details = None
    proof_file_id = None
    proof_file_type = None
    proof_file_name = None
    proof_bytes = None

    if update.message.text:
        details = update.message.text.strip()
        if len(details) < 4:
            await update.message.reply_text("Tx Hash / Transaction Details معتبر وارد کنید.")
            return
        if len(details) > 2000:
            await update.message.reply_text("متن Transaction Details نباید بیشتر از ۲۰۰۰ کاراکتر باشد.")
            return
    elif update.message.photo:
        photo = update.message.photo[-1]
        if photo.file_size and photo.file_size > _MAX_COMPLETION_FILE_BYTES:
            await update.message.reply_text("حجم تصویر Transaction Details نباید بیشتر از ۱۰ مگابایت باشد.")
            return
        proof_file_id = photo.file_id
        proof_file_type = "photo"
        proof_file_name = "transaction-details.jpg"
        details = (update.message.caption or "").strip() or None
        try:
            telegram_file = await context.bot.get_file(proof_file_id)
            proof_bytes = bytes(await telegram_file.download_as_bytearray())
        except Exception:
            logger.exception("خطا در دانلود تصویر Transaction Details از ادمین بات")
            await update.message.reply_text("دریافت فایل ناموفق بود؛ لطفاً دوباره ارسال کنید.")
            return
    elif update.message.document:
        document = update.message.document
        if document.file_size and document.file_size > _MAX_COMPLETION_FILE_BYTES:
            await update.message.reply_text("حجم فایل Transaction Details نباید بیشتر از ۱۰ مگابایت باشد.")
            return
        proof_file_id = document.file_id
        proof_file_type = "document"
        proof_file_name = document.file_name or "transaction-details"
        details = (update.message.caption or "").strip() or None
        try:
            telegram_file = await context.bot.get_file(proof_file_id)
            proof_bytes = bytes(await telegram_file.download_as_bytearray())
        except Exception:
            logger.exception("خطا در دانلود فایل Transaction Details از ادمین بات")
            await update.message.reply_text("دریافت فایل ناموفق بود؛ لطفاً دوباره ارسال کنید.")
            return
    else:
        await update.message.reply_text("لطفاً Tx Hash را به‌صورت متن، یا Transaction Details را به‌صورت تصویر/فایل ارسال کنید.")
        return

    if not _save_completion_proof(
        order_id,
        details=details,
        file_id=proof_file_id,
        file_type=proof_file_type,
        file_name=proof_file_name,
    ):
        await update.message.reply_text(
            "⚠️ ذخیره Transaction Details در دیتابیس ناموفق بود؛ سفارش تکمیل نشد. "
            "اتصال دیتابیس و migration مربوط به completion proof را بررسی کنید."
        )
        return

    admin_id = update.effective_user.id
    try:
        order_transition_service.transition_order_status(order_id, "completed", changed_by=admin_id)
    except InvalidStateTransition:
        context.user_data.pop(_PENDING_COMPLETION_KEY, None)
        await update.message.reply_text("این سفارش قابل تکمیل نیست (وضعیت تغییر کرده).")
        return

    db.record_order_outcome(order["chat_id"], float(order["usdt_amount"]), success=True)
    context.user_data.pop(_PENDING_COMPLETION_KEY, None)

    try:
        await context.bot.edit_message_reply_markup(
            chat_id=pending["chat_id"],
            message_id=pending["message_id"],
            reply_markup=None,
        )
    except Exception:
        logger.exception("حذف دکمه تکمیل سفارش %s ناموفق بود", order_id)

    asset = _order_asset(order)
    order_code = _order_code(order)
    await update.message.reply_text(f"📦 سفارش {order_code} با Transaction Details ثبت‌شده تکمیل شد.")

    customer_bot = _get_customer_bot()
    success_text = f"📦 سفارش {asset} شما ({order_code}) با موفقیت تکمیل شد."
    if details:
        success_text += f"\n\n🔎 Transaction Details / Tx Hash:\n{details}"
    if proof_bytes is not None:
        success_text += "\n\n📎 فایل Transaction Details نیز در پیام بعدی ارسال شده است."
    success_text += "\n\nلطفاً تجربهٔ خود را با یک امتیاز به ما بگویید:"

    try:
        await customer_bot.send_message(
            chat_id=order["chat_id"],
            text=success_text,
            reply_markup=usdt_rating_keyboard(order_id),
        )
        if proof_bytes is not None:
            buffer = BytesIO(proof_bytes)
            buffer.name = proof_file_name or "transaction-details"
            caption = f"Transaction Details — {order_code}"
            if proof_file_type == "photo":
                await customer_bot.send_photo(chat_id=order["chat_id"], photo=buffer, caption=caption)
            else:
                await customer_bot.send_document(chat_id=order["chat_id"], document=buffer, caption=caption)
    except Exception:
        logger.exception("خطا در ارسال پیام تکمیل/Transaction Details به کاربر")


async def kyc_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not _is_admin(update):
        await query.answer("این عملیات فقط برای مدیران مجاز است.", show_alert=True)
        return
    action, chat_id_str = query.data.split(":", 1)
    try:
        chat_id = int(chat_id_str)
    except ValueError:
        await query.answer("چت‌آیدی نامعتبر است.", show_alert=True)
        return
    profile = db.get_user_profile(chat_id)
    if not profile:
        await query.answer("پروفایلی یافت نشد.", show_alert=True)
        return
    customer_bot = _get_customer_bot()
    admin_id = update.effective_user.id

    if action == "admin_kyc_verify":
        db.set_kyc_status(chat_id, "verified", verified_by=admin_id)
        await query.answer("هویت تایید شد ✅")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ هویت این کاربر تایید شد.")
        try:
            await customer_bot.send_message(chat_id=chat_id, text="✅ هویت شما تایید شد. از این پس سفارش‌های شما سریع‌تر پردازش می‌شوند.")
        except Exception:
            logger.exception("خطا در اطلاع‌رسانی تایید هویت به کاربر")
    elif action == "admin_kyc_reject":
        db.set_kyc_status(chat_id, "restricted", verified_by=admin_id, reason="رد شده در بررسی اولیهٔ هویت")
        await query.answer("هویت رد شد ❌")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ هویت این کاربر رد شد (وضعیت: Restricted).")
        try:
            await customer_bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ متاسفانه مدارک ارسالی شما تایید نشد.\nلطفاً برای پیگیری با پشتیبانی تماس بگیرید: {SUPPORT_TELEGRAM_USERNAME}",
            )
        except Exception:
            logger.exception("خطا در اطلاع‌رسانی رد هویت به کاربر")


def build_admin_application() -> Application:
    if not ADMIN_BOT_TOKEN:
        raise RuntimeError("ADMIN_BOT_TOKEN تنظیم نشده است. آن را در .env قرار دهید.")
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CallbackQueryHandler(review_callback, pattern=r"^admin_(confirm|reject|complete):"))
    app.add_handler(CallbackQueryHandler(kyc_review_callback, pattern=r"^admin_kyc_(verify|reject):"))
    app.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND) | filters.PHOTO | filters.Document.ALL,
            completion_proof_message,
        )
    )
    return app


def main() -> None:
    app = build_admin_application()
    logger.info("ربات مدیریت Saraf در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
