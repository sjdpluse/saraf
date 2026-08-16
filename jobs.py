"""
وظایف زمان‌بندی‌شده:
  - fetch_and_store_snapshot: نرخ ارز و طلای مرجع (بین‌المللی) را می‌گیرد و ذخیره می‌کند.
  - fetch_and_store_local_market: نرخ واقعی بازارهای محلی افغانستان (اسکرپ sarafi.af)
    را می‌گیرد و ذخیره می‌کند؛ این داده مبنای نمایش bid/ask واقعی و محاسبهٔ نرخ Saraf است.
  - check_and_post_facebook_update: نرخ‌ها را بررسی و در صورت تغییر محسوس، تصویر
    پست فیسبوک (نرخ دالر + طلا + نقره) را می‌سازد و به همراه کپشن کامل منتشر می‌کند.
  - check_and_post_instagram_update: دقیقاً همان کار بالا، اما برای اینستاگرام —
    جدا نگه داشته شده چون آستانهٔ تغییر و زمان‌بندی‌اش می‌تواند مستقل از فیسبوک
    تنظیم شود (INSTAGRAM_CHANGE_THRESHOLD_PERCENT / INSTAGRAM_CHECK_INTERVAL_MINUTES).
"""
import logging
from services import (
    currency_service,
    gold_service,
    silver_service,
    local_market_service,
    rate_engine,
    facebook_service,
    instagram_service,
    supabase_service as db,
)
from config import TRACKED_CURRENCIES
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def fetch_and_store_snapshot(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        rates, _source = await currency_service.get_afn_rates()
        if rates:
            db.insert_currency_snapshot(rates)
            logger.info("تاریخچهٔ نرخ ارز ذخیره شد: %s ارز", len(rates))

        afn_per_usd = rates.get("usd") if rates else None
        if afn_per_usd:
            price_usd = await gold_service.get_gold_price_usd_per_oz()
            breakdown = gold_service.build_gold_breakdown(price_usd, afn_per_usd)
            db.insert_gold_snapshot(price_usd, breakdown["afn_per_gram_24k"])
            logger.info("تاریخچهٔ نرخ طلا ذخیره شد.")
    except Exception:
        logger.exception("خطا در وظیفهٔ زمان‌بندی‌شدهٔ ذخیرهٔ نرخ‌ها")


async def fetch_and_store_local_market(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        data = await local_market_service.get_local_market_rates(force_refresh=True)
        for market, rates in data.items():
            if rates:
                db.insert_local_market_snapshot(market, rates)
                logger.info(
                    "تاریخچهٔ بازار محلی «%s» ذخیره شد: %s ارز", market, len(rates)
                )
    except Exception:
        logger.exception("خطا در وظیفهٔ زمان‌بندی‌شدهٔ ذخیرهٔ نرخ بازار محلی")


async def _get_current_quotes_and_metals():
    """منطق مشترک بین فیسبوک و اینستاگرام: نرخ‌های لحظه‌یی + تفکیک کامل طلا و نقره.
    جدا شده تا هر دو پلتفرم دقیقاً از یک منبع دادهٔ لحظه‌یی استفاده کنند (بدون
    فچ دوبارهٔ جداگانه که ممکن است چند ثانیه اختلاف بین دو پست ایجاد کند)."""
    quotes = await rate_engine.get_full_quotes(list(TRACKED_CURRENCIES.keys()))
    if not quotes:
        return None, None, None

    gold_breakdown = None
    silver_breakdown = None
    usd_quote = quotes.get("usd")
    afn_per_usd = None
    if usd_quote:
        afn_per_usd = usd_quote.get("reference_rate") or usd_quote["saraf_quote"]["basis_rate"]
    if afn_per_usd:
        price_usd_gold = await gold_service.get_gold_price_usd_per_oz()
        gold_breakdown = gold_service.build_gold_breakdown(price_usd_gold, afn_per_usd)
        try:
            price_usd_silver = await silver_service.get_silver_price_usd_per_oz()
            silver_breakdown = silver_service.build_silver_breakdown(price_usd_silver, afn_per_usd)
        except Exception:
            # نبود نرخ نقره نباید کل پست (که دالر + طلا دارد) را متوقف کند —
            # facebook_service/instagram_service با silver_breakdown=None هم به‌درستی کار می‌کنند.
            logger.exception("خطا در دریافت نرخ نقره؛ پست بدون بخش نقره ادامه می‌یابد.")

    return quotes, gold_breakdown, silver_breakdown


async def check_and_post_facebook_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        quotes, gold_breakdown, silver_breakdown = await _get_current_quotes_and_metals()
        if not quotes:
            return
        await facebook_service.check_and_maybe_post(quotes, gold_breakdown, silver_breakdown)
    except Exception:
        logger.exception("خطا در وظیفهٔ بررسی/ارسال پست فیسبوک")


async def check_and_post_instagram_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        quotes, gold_breakdown, silver_breakdown = await _get_current_quotes_and_metals()
        if not quotes:
            return
        await instagram_service.check_and_maybe_post(quotes, gold_breakdown, silver_breakdown)
    except Exception:
        logger.exception("خطا در وظیفهٔ بررسی/ارسال پست اینستاگرام")
