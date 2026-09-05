"""ربات مدیریت Saraf برای سفارش‌های USDT / USDC و بررسی KYC."""
import logging

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import ADMIN_BOT_TOKEN, ADMIN_CHAT_IDS, BOT_TOKEN, SUPPORT_TELEGRAM_USERNAME
from keyboards import admin_order_complete_keyboard, usdt_rating_keyboard
from services import supabase_service as db
from services import order_transition_service, usdt_service
from services.order_state_machine import InvalidStateTransition

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

_customer_bot: Bot | None = None

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
        try:
            order_transition_service.transition_order_status(order_id, "completed", changed_by=admin_id)
        except InvalidStateTransition:
            await query.answer("این سفارش قابل تکمیل نیست (وضعیت تغییر کرده).", show_alert=True)
            return
        db.record_order_outcome(order["chat_id"], float(order["usdt_amount"]), success=True)
        await query.answer("تکمیل شد 📦")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"📦 سفارش {order_code} تکمیل شد.")
        try:
            await customer_bot.send_message(
                chat_id=order["chat_id"],
                text=f"📦 سفارش {asset} شما (`{order_code}`) با موفقیت تکمیل شد. از خرید/فروش شما متشکریم!\n\nلطفاً تجربهٔ خود را با یک امتیاز به ما بگویید:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=usdt_rating_keyboard(order_id),
            )
        except Exception:
            logger.exception("خطا در اطلاع‌رسانی تکمیل سفارش/درخواست امتیاز از کاربر")


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
    return app


def main() -> None:
    app = build_admin_application()
    logger.info("ربات مدیریت Saraf در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
