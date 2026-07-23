"""
نقطهٔ ورود اصلی ربات تلگرامی Saraf.

اجرا:
    python bot.py

متغیرهای محیطی لازم در فایل .env (بر اساس .env.example) تنظیم شوند.
"""
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, FETCH_INTERVAL_MINUTES
from keyboards import BTN_CURRENCY, BTN_GOLD, BTN_COMPARE, BTN_ADVISOR, BTN_ABOUT
from handlers import start, currency, gold, compare, advisor, admin
from jobs import fetch_and_store_snapshot

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پیام‌های متنی معمولی را بر اساس دکمهٔ منوی فشرده‌شده هدایت می‌کند."""
    # اول: اگر کاربر منتظر سوال برای مشاور هوشمند بود، پاسخ بده و از تابع خارج شو
    if await advisor.handle_advisor_question(update, context):
        return

    text = update.message.text
    if text == BTN_CURRENCY:
        await currency.currency_menu(update, context)
    elif text == BTN_GOLD:
        await gold.gold_menu(update, context)
    elif text == BTN_COMPARE:
        await compare.compare_menu(update, context)
    elif text == BTN_ADVISOR:
        await advisor.advisor_prompt(update, context)
    elif text == BTN_ABOUT:
        await start.about(update, context)
    else:
        await update.message.reply_text(
            "لطفاً یکی از گزینه‌های منو را انتخاب کنید 👇"
        )


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است. آن را در .env قرار دهید.")

    app = Application.builder().token(BOT_TOKEN).build()

    # دستورات
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("about", start.about))
    app.add_handler(CommandHandler("stop", start.stop))
    app.add_handler(CommandHandler("broadcast", admin.broadcast))
    app.add_handler(CommandHandler("stats", admin.stats))

    # منوی اصلی (متن دکمه‌ها)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_router))

    # کال‌بک‌های اینلاین
    app.add_handler(CallbackQueryHandler(currency.currency_callback, pattern=r"^cur:"))
    app.add_handler(CallbackQueryHandler(gold.gold_callback, pattern=r"^gold:"))
    app.add_handler(
        CallbackQueryHandler(compare.compare_target_callback, pattern=r"^cmp_target:")
    )
    app.add_handler(
        CallbackQueryHandler(compare.compare_period_callback, pattern=r"^cmp_period:")
    )

    # وظیفهٔ زمان‌بندی‌شده برای ذخیرهٔ تاریخچه
    if app.job_queue:
        app.job_queue.run_repeating(
            fetch_and_store_snapshot,
            interval=FETCH_INTERVAL_MINUTES * 60,
            first=10,
        )

    return app


def main() -> None:
    app = build_application()
    logger.info("ربات Saraf در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
