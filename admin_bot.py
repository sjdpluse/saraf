"""
ربات مدیریت Saraf — نسخهٔ اختصاصی ادمین برای بررسی، تایید یا رد سفارش‌های تتر.

این ربات کاملاً جدا از ربات مشتریان (bot.py) اجرا می‌شود تا اعلان‌های حساس مالی
(سفارش‌های تتر) با پیام‌های عمومی مخلوط نشوند و فرآیند تایید با یک لمس ساده
انجام شود.

اجرا:
    python admin_bot.py

⚠️ نکتهٔ مهم: تلگرام اجازه نمی‌دهد رباتی به کاربری که مکالمه را با آن شروع نکرده
پیام بدهد. پس بعد از هر دیپلوی، خودت (با همان چت‌آیدی‌ای که در ADMIN_CHAT_IDS
هست) باید یک‌بار به این ربات پیام /start بفرستی.
"""
import logging

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from config import ADMIN_BOT_TOKEN, ADMIN_CHAT_IDS, BOT_TOKEN, SUPPORT_TELEGRAM_USERNAME
from services import supabase_service as db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_customer_bot: Bot | None = None


def _get_customer_bot() -> Bot:
    global _customer_bot
    if _customer_bot is None:
        _customer_bot = Bot(token=BOT_TOKEN)
    return _customer_bot


def _is_admin(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id in ADMIN_CHAT_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("این ربات فقط برای مدیریت Saraf است.")
        return
    await update.message.reply_text(
        "✅ ربات مدیریت Saraf متصل شد.\nاز این پس اعلان سفارش‌های تتر همین‌جا دریافت می‌شود."
    )


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
    if order["status"] != "pending":
        await query.answer("این سفارش قبلاً بررسی شده است.", show_alert=True)
        return

    order_code = f"USDT-{order_id:05d}"
    customer_bot = _get_customer_bot()

    if action == "admin_confirm":
        db.update_usdt_order_status(order_id, "confirmed")
        await query.answer("تایید شد ✅")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ سفارش {order_code} تایید شد.")
        try:
            await customer_bot.send_message(
                chat_id=order["chat_id"],
                text=(
                    f"✅ سفارش شما (`{order_code}`) تایید و در حال پردازش نهایی است.\n"
                    "طبق زمان‌بندی اعلام‌شده، ظرف کمتر از ۱ ساعت تکمیل خواهد شد."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            logger.exception("خطا در اطلاع‌رسانی تایید سفارش به کاربر")

    elif action == "admin_reject":
        db.update_usdt_order_status(order_id, "cancelled")
        await query.answer("رد شد ❌")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"❌ سفارش {order_code} رد شد.")
        try:
            await customer_bot.send_message(
                chat_id=order["chat_id"],
                text=(
                    f"⚠️ سفارش شما (`{order_code}`) قابل تایید نبود.\n"
                    f"لطفاً برای پیگیری با پشتیبانی تماس بگیرید: {SUPPORT_TELEGRAM_USERNAME}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            logger.exception("خطا در اطلاع‌رسانی رد سفارش به کاربر")


def build_admin_application() -> Application:
    if not ADMIN_BOT_TOKEN:
        raise RuntimeError("ADMIN_BOT_TOKEN تنظیم نشده است. آن را در .env قرار دهید.")
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(review_callback, pattern=r"^admin_(confirm|reject):"))
    return app


def main() -> None:
    app = build_admin_application()
    logger.info("ربات مدیریت Saraf در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
