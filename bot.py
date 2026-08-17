"""
نقطهٔ ورود اصلی ربات تلگرامی Saraf.

اجرا:
    python bot.py

متغیرهای محیطی لازم در فایل .env (بر اساس .env.example) تنظیم شوند.
"""
import asyncio
import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)
from config import (
    BOT_TOKEN,
    FETCH_INTERVAL_MINUTES,
    LOCAL_MARKET_FETCH_INTERVAL_MINUTES,
    FACEBOOK_CHECK_INTERVAL_MINUTES,
    INSTAGRAM_CHECK_INTERVAL_MINUTES,
)
from keyboards import BTN_CURRENCY, BTN_GOLD, BTN_SILVER, BTN_CRYPTO, BTN_COMPARE, BTN_CONVERTER, BTN_ABOUT, BTN_USDT, BTN_ADMIN_POST
from handlers import start, currency, gold, silver, crypto, compare, admin, converter, usdt, kyc
from jobs import (
    fetch_and_store_snapshot,
    fetch_and_store_local_market,
    check_and_post_facebook_update,
    check_and_post_instagram_update,
)
from services import supabase_service

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def touch_last_seen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    آخرین بازدید کاربر را روی هر نوع تعامل با ربات به‌روز می‌کند — نه فقط /start.

    قبلاً last_seen_at فقط داخل db.upsert_user (که تنها در handlers/start.py صدا
    زده می‌شد) به‌روز می‌شد؛ یعنی کاربری که فقط روی دکمه‌های نرخ ارز/طلا/تتر کلیک
    می‌کرد ولی /start نمی‌زد، در آمار «آنلاین» / «فعال امروز» دیده نمی‌شد.

    این هندلر با group=-1 روی همهٔ آپدیت‌ها (پیام، callback، عکس، مخاطب و...)
    اجرا می‌شود و قبل از هندلرهای معمولی (group=0) کار می‌کند، بدون این‌که جلوی
    اجرای آن‌ها را بگیرد. برای این‌که یک کلیک ساده باعث کندی پاسخ ربات نشود،
    کوئری Supabase (که sync است) داخل یک ترد جدا و به‌صورت fire-and-forget
    زمان‌بندی می‌شود؛ اگر خطا بخورد فقط لاگ می‌شود و به کاربر چیزی نشان داده
    نمی‌شود.
    """
    user = update.effective_user
    if user is None:
        return

    def _update_last_seen() -> None:
        try:
            supabase_service.get_client().table("users").update(
                {
                    "last_seen_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True,
                }
            ).eq("chat_id", user.id).execute()
        except Exception:
            logger.exception("خطا در به‌روزرسانی last_seen_at")

    context.application.create_task(asyncio.to_thread(_update_last_seen))


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پیام‌های متنی معمولی را بر اساس دکمهٔ منوی فشرده‌شده یا حالت انتظار هدایت می‌کند."""
    if await kyc.handle_first_name(update, context):
        return
    if await kyc.handle_last_name(update, context):
        return
    if await kyc.handle_phone_text(update, context):
        return
    if await kyc.handle_payment_info(update, context):
        return

    if await gold.handle_gold_grams_input(update, context):
        return
    if await silver.handle_silver_grams_input(update, context):
        return
    if await currency.handle_currency_calc_input(update, context):
        return
    if await converter.handle_converter_input(update, context):
        return
    if await usdt.handle_usdt_amount_input(update, context):
        return
    if await usdt.handle_usdt_wallet_address_input(update, context):
        return
    if await usdt.handle_usdt_exchange_custom_input(update, context):
        return
    if await usdt.handle_usdt_network_custom_input(update, context):
        return
    if await usdt.handle_usdt_tx_proof_text(update, context):
        return
    if await usdt.handle_usdt_bank_info_input(update, context):
        return

    text = update.message.text
    if text == BTN_CURRENCY:
        await currency.currency_menu(update, context)
    elif text == BTN_GOLD:
        await gold.gold_menu(update, context)
    elif text == BTN_SILVER:
        await silver.silver_menu(update, context)
    elif text == BTN_CRYPTO:
        await crypto.crypto_menu(update, context)
    elif text == BTN_COMPARE:
        await compare.compare_menu(update, context)
    elif text == BTN_CONVERTER:
        await converter.converter_prompt(update, context)
    elif text == BTN_USDT:
        await usdt.usdt_menu(update, context)
    elif text == BTN_ABOUT:
        await start.about(update, context)
    elif text == BTN_ADMIN_POST:
        await admin.manual_post(update, context)
    else:
        await update.message.reply_text("لطفاً یکی از گزینه‌های منو را انتخاب کنید 👇")


async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await kyc.handle_id_document_photo(update, context):
        return
    if await kyc.handle_selfie_photo(update, context):
        return
    if await usdt.handle_usdt_receipt_photo(update, context):
        return
    if await usdt.handle_usdt_tx_proof_photo(update, context):
        return


async def contact_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await kyc.handle_phone_contact(update, context)


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است. آن را در .env قرار دهید.")

    app = Application.builder().token(BOT_TOKEN).build()

    # group=-1 یعنی قبل از همهٔ هندلرهای دیگر (که در group=0 پیش‌فرض ثبت
    # می‌شوند) اجرا می‌شود، اما چون ApplicationHandlerStop پرتاب نمی‌کند،
    # جلوی اجرای بقیهٔ هندلرها را نمی‌گیرد — روی همهٔ انواع Update کار می‌کند.
    app.add_handler(TypeHandler(Update, touch_last_seen), group=-1)

    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("about", start.about))
    app.add_handler(CommandHandler("stop", start.stop))
    app.add_handler(CommandHandler("broadcast", admin.broadcast))
    app.add_handler(CommandHandler("stats", admin.stats))
    app.add_handler(CommandHandler("setspread", admin.set_spread))
    app.add_handler(CommandHandler("spreads", admin.list_spreads))
    app.add_handler(CommandHandler("usdtpending", admin.usdt_pending))
    app.add_handler(CommandHandler("usdtconfirm", admin.usdt_confirm))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_router))
    app.add_handler(MessageHandler(filters.PHOTO, photo_router))
    app.add_handler(MessageHandler(filters.CONTACT, contact_router))

    app.add_handler(CallbackQueryHandler(start.about_callback, pattern=r"^about:"))
    app.add_handler(CallbackQueryHandler(currency.currency_callback, pattern=r"^cur:"))
    app.add_handler(CallbackQueryHandler(currency.currency_calc_callback, pattern=r"^curcalc:"))
    app.add_handler(CallbackQueryHandler(gold.gold_callback, pattern=r"^gold:"))
    app.add_handler(CallbackQueryHandler(gold.gold_calc_mode_callback, pattern=r"^goldcalc_mode:"))
    app.add_handler(CallbackQueryHandler(gold.gold_calc_karat_callback, pattern=r"^goldcalc_karat:"))
    app.add_handler(CallbackQueryHandler(silver.silver_calc_mode_callback, pattern=r"^silvercalc_mode:"))
    app.add_handler(CallbackQueryHandler(compare.compare_target_callback, pattern=r"^cmp_target:"))
    app.add_handler(CallbackQueryHandler(compare.compare_period_callback, pattern=r"^cmp_period:"))
    app.add_handler(CallbackQueryHandler(converter.converter_from_callback, pattern=r"^convfrom:"))
    app.add_handler(CallbackQueryHandler(converter.converter_to_callback, pattern=r"^convto:"))
    app.add_handler(CallbackQueryHandler(converter.converter_amount_callback, pattern=r"^convamt:"))
    app.add_handler(CallbackQueryHandler(usdt.usdt_action_callback, pattern=r"^usdt_action:"))
    app.add_handler(CallbackQueryHandler(usdt.usdt_continue_callback, pattern=r"^usdt_continue:"))
    app.add_handler(CallbackQueryHandler(usdt.usdt_pay_callback, pattern=r"^usdt_pay:"))
    app.add_handler(CallbackQueryHandler(usdt.usdt_paid_callback, pattern=r"^usdt_paid:"))
    app.add_handler(CallbackQueryHandler(usdt.usdt_network_callback, pattern=r"^usdt_net:"))
    app.add_handler(CallbackQueryHandler(usdt.usdt_exch_callback, pattern=r"^usdt_exch:"))
    app.add_handler(CallbackQueryHandler(usdt.usdt_buy_exch_callback, pattern=r"^usdt_buy_exch:"))
    app.add_handler(CallbackQueryHandler(usdt.usdt_rate_callback, pattern=r"^usdt_rate:"))

    if app.job_queue:
        app.job_queue.run_repeating(fetch_and_store_snapshot, interval=FETCH_INTERVAL_MINUTES * 60, first=10)
        app.job_queue.run_repeating(fetch_and_store_local_market, interval=LOCAL_MARKET_FETCH_INTERVAL_MINUTES * 60, first=20)
        app.job_queue.run_repeating(check_and_post_facebook_update, interval=FACEBOOK_CHECK_INTERVAL_MINUTES * 60, first=90)
        app.job_queue.run_repeating(check_and_post_instagram_update, interval=INSTAGRAM_CHECK_INTERVAL_MINUTES * 60, first=110)

    return app


def main() -> None:
    app = build_application()
    logger.info("ربات Saraf در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()