"""
ربات مدیریت Saraf — نسخهٔ اختصاصی ادمین برای بررسی، تایید/رد و تکمیل سفارش‌های تتر.

جریان کار (Timeline واقعی، نه فقط ظاهری):
  1) سفارش ثبت می‌شود → وضعیت "pending" → دکمه‌های «تایید / رد» نمایش داده می‌شود.
  2) با زدن «تایید» → وضعیت "confirmed" (+ زمان دقیق ثبت می‌شود) → دکمهٔ «تکمیل شد»
     جایگزین می‌شود. این دکمه فقط وقتی زده شود که ادمین واقعاً تتر/پول را ارسال
     کرده باشد.
  3) با زدن «تکمیل شد» → وضعیت "completed" (+ زمان دقیق) → به مشتری پیام تکمیل
     همراه با درخواست امتیازدهی (⭐️ ۱ تا ۵) ارسال می‌شود.
  4) با زدن «رد» در هر مرحله → وضعیت "cancelled" + پیام مؤدبانه با آی‌دی پشتیبانی.

این ربات کاملاً جدا از ربات مشتریان (bot.py) اجرا می‌شود تا اعلان‌های حساس مالی با
پیام‌های عمومی مخلوط نشوند.

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
from keyboards import admin_order_complete_keyboard, usdt_rating_keyboard
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

    order_code = f"USDT-{order_id:05d}"
    customer_bot = _get_customer_bot()

    # ---------------------------------------------------------------
    # مرحلهٔ ۱: تایید یا رد سفارش pending
    # ---------------------------------------------------------------
    if action in ("admin_confirm", "admin_reject"):
        if order["status"] != "pending":
            await query.answer("این سفارش قبلاً بررسی شده است.", show_alert=True)
            return

        if action == "admin_confirm":
            db.mark_usdt_order_confirmed(order_id)
            await query.answer("تایید شد ✅")
            await query.edit_message_reply_markup(reply_markup=admin_order_complete_keyboard(order_id))
            await query.message.reply_text(
                f"✅ سفارش {order_code} تایید شد.\n"
                "بعد از اینکه تتر/مبلغ را واقعاً برای مشتری ارسال کردی، دکمهٔ «تکمیل شد» را بزن."
            )
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

        else:  # admin_reject
            db.mark_usdt_order_cancelled(order_id)
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
        return

    # ---------------------------------------------------------------
    # مرحلهٔ ۲: تکمیل نهایی (بعد از ارسال واقعی تتر/پول)
    # ---------------------------------------------------------------
    if action == "admin_complete":
        if order["status"] != "confirmed":
            await query.answer("این سفارش در وضعیت قابل‌تکمیل نیست.", show_alert=True)
            return

        db.mark_usdt_order_completed(order_id)
        await query.answer("تکمیل شد 📦")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"📦 سفارش {order_code} تکمیل شد.")

        try:
            await customer_bot.send_message(
                chat_id=order["chat_id"],
                text=(
                    f"📦 سفارش شما (`{order_code}`) با موفقیت تکمیل شد. از خرید/فروش شما متشکریم!\n\n"
                    "لطفاً تجربهٔ خود را با یک امتیاز به ما بگویید:"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=usdt_rating_keyboard(order_id),
            )
        except Exception:
            logger.exception("خطا در اطلاع‌رسانی تکمیل سفارش/درخواست امتیاز از کاربر")


def build_admin_application() -> Application:
    if not ADMIN_BOT_TOKEN:
        raise RuntimeError("ADMIN_BOT_TOKEN تنظیم نشده است. آن را در .env قرار دهید.")
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(review_callback, pattern=r"^admin_(confirm|reject|complete):"))
    return app


def main() -> None:
    app = build_admin_application()
    logger.info("ربات مدیریت Saraf در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
