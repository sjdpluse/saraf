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

from config import BOT_TOKEN, FETCH_INTERVAL_MINUTES, LOCAL_MARKET_FETCH_INTERVAL_MINUTES
from keyboards import BTN_CURRENCY, BTN_GOLD, BTN_COMPARE, BTN_CONVERTER, BTN_ABOUT
from handlers import start, currency, gold, compare, admin, converter
from jobs import fetch_and_store_snapshot, fetch_and_store_local_market

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پیام‌های متنی معمولی را بر اساس دکمهٔ منوی فشرده‌شده یا حالت انتظار هدایت می‌کند."""
    if await gold.handle_gold_grams_input(update, context):
        return
    if await currency.handle_currency_calc_input(update, context):
        return
    if await converter.handle_converter_input(update, context):
        return

    text = update.message.text
    if text == BTN_CURRENCY:
        await currency.currency_menu(update, context)
    elif text == BTN_GOLD:
        await gold.gold_menu(update, context)
    elif text == BTN_COMPARE:
        await compare.compare_menu(update, context)
    elif text == BTN_CONVERTER:
        await converter.converter_prompt(update, context)
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
    app.add_handler(CommandHandler("setspread", admin.set_spread))
    app.add_handler(CommandHandler("spreads", admin.list_spreads))

    # منوی اصلی (متن دکمه‌ها)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_router))

    # کال‌بک‌های اینلاین
    app.add_handler(CallbackQueryHandler(currency.currency_callback, pattern=r"^cur:"))
    app.add_handler(
        CallbackQueryHandler(currency.currency_calc_callback, pattern=r"^curcalc:")
    )
    app.add_handler(CallbackQueryHandler(gold.gold_callback, pattern=r"^gold:"))
    app.add_handler(
        CallbackQueryHandler(gold.gold_calc_mode_callback, pattern=r"^goldcalc_mode:")
    )
    app.add_handler(
        CallbackQueryHandler(gold.gold_calc_karat_callback, pattern=r"^goldcalc_karat:")
    )
    app.add_handler(
        CallbackQueryHandler(compare.compare_target_callback, pattern=r"^cmp_target:")
    )
    app.add_handler(
        CallbackQueryHandler(compare.compare_period_callback, pattern=r"^cmp_period:")
    )
    app.add_handler(
        CallbackQueryHandler(converter.converter_from_callback, pattern=r"^convfrom:")
    )
    app.add_handler(
        CallbackQueryHandler(converter.converter_to_callback, pattern=r"^convto:")
    )
    app.add_handler(
        CallbackQueryHandler(converter.converter_amount_callback, pattern=r"^convamt:")
    )

    # وظایف زمان‌بندی‌شده
    if app.job_queue:
        app.job_queue.run_repeating(
            fetch_and_store_snapshot,
            interval=FETCH_INTERVAL_MINUTES * 60,
            first=10,
        )
        app.job_queue.run_repeating(
            fetch_and_store_local_market,
            interval=LOCAL_MARKET_FETCH_INTERVAL_MINUTES * 60,
            first=20,
        )

    return app


def main() -> None:
    app = build_application()
    logger.info("ربات Saraf در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()