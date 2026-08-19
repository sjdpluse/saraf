"""
وظایف زمان‌بندی‌شده:
  - fetch_and_store_snapshot: نرخ ارز و طلای مرجع (بین‌المللی) را می‌گیرد و ذخیره می‌کند.
  - fetch_and_store_local_market: نرخ واقعی بازارهای محلی افغانستان (اسکرپ sarafi.af)
    را می‌گیرد و ذخیره می‌کند؛ این داده مبنای نمایش bid/ask واقعی و محاسبهٔ نرخ Saraf است.
  - check_and_post_facebook_update: فقط تغییر محسوس نرخ دالر را به‌عنوان Trigger
    بررسی می‌کند؛ اگر دالر به آستانه برسد، پست کامل فیسبوک با آخرین نرخ‌های موجود
    (دالر + سایر ارزها + طلا + نقره) منتشر می‌شود.
  - check_and_post_instagram_update: همان Trigger دالر برای اینستاگرام، با آستانهٔ
    مستقل INSTAGRAM_CHANGE_THRESHOLD_PERCENT.

تغییر طلا، نقره، یورو، کلدار، درهم یا سایر ارزها به‌تنهایی دیگر باعث پست
خودکار جدید نمی‌شود. نشر دستی ادمین همچنان مستقل و بدون این محدودیت است.
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
from config import (
    TRACKED_CURRENCIES,
    FACEBOOK_CHANGE_THRESHOLD_PERCENT,
    INSTAGRAM_CHANGE_THRESHOLD_PERCENT,
)
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

            try:
                price_usd_silver = await silver_service.get_silver_price_usd_per_oz()
                silver_breakdown = silver_service.build_silver_breakdown(
                    price_usd_silver, afn_per_usd
                )
                db.insert_silver_snapshot(price_usd_silver, silver_breakdown["afn_per_gram"])
                logger.info("تاریخچهٔ نرخ نقره ذخیره شد.")
            except Exception:
                # نبود نرخ نقره نباید ذخیرهٔ ارز/طلا را متوقف کند.
                logger.exception("خطا در ذخیرهٔ تاریخچهٔ نقره")
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


async def get_current_quotes_and_metals():
    """منطق مشترک بین فیسبوک، اینستاگرام، و دکمهٔ «نشر پست» دستی ادمین: نرخ‌های
    لحظه‌یی + تفکیک کامل طلا و نقره. جدا شده تا همه از یک منبع دادهٔ لحظه‌یی
    استفاده کنند (بدون فچ دوبارهٔ جداگانه که ممکن است چند ثانیه اختلاف بین دو
    پست ایجاد کند)."""
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


def _usd_primary_buy(quotes: dict):
    """همان نرخ خرید اصلی دالر که سرویس پست برای state استفاده می‌کند:
    اول نرخ بازار محلی/سرای شهزاده، و در نبود آن نرخ صرافی‌های محلی."""
    usd_quote = (quotes or {}).get("usd") or {}
    local = usd_quote.get("local") or {}
    if local.get("buy") is not None:
        return float(local["buy"])

    local_quote = usd_quote.get("saraf_quote") or {}
    if local_quote.get("buy") is not None:
        return float(local_quote["buy"])
    return None


def _usd_has_significant_change(quotes: dict, last_state: dict, threshold_percent: float) -> bool:
    """فقط USD را با آخرین state پست مقایسه می‌کند.

    stateهای قبلی از قبل کلید `usd` دارند؛ بنابراین این تغییر بدون migration و
    بدون reset کردن جدول‌های fb_post_state / ig_post_state کار می‌کند.
    """
    current_usd = _usd_primary_buy(quotes)
    if current_usd is None:
        return False

    if not last_state:
        return True

    old_usd = last_state.get("usd")
    if not old_usd:
        # برای state قدیمی/ناقص یک بار اجازهٔ پست بده تا state سالم ذخیره شود.
        return True

    pct = abs(current_usd - float(old_usd)) / float(old_usd) * 100
    return pct >= threshold_percent


async def check_and_post_facebook_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        quotes, gold_breakdown, silver_breakdown = await get_current_quotes_and_metals()
        if not quotes:
            return

        last_state = db.get_fb_post_state()
        if not _usd_has_significant_change(
            quotes,
            last_state,
            FACEBOOK_CHANGE_THRESHOLD_PERCENT,
        ):
            logger.info(
                "Facebook auto-post skipped: USD change below %.4f%% threshold; "
                "changes in other currencies/metals do not trigger posts.",
                FACEBOOK_CHANGE_THRESHOLD_PERCENT,
            )
            return

        # Trigger قبلاً فقط با USD تأیید شده؛ force=True مانع از این می‌شود که
        # تغییر سایر ارزها/فلزات دوباره در سرویس معیار تصمیم‌گیری قرار بگیرد.
        await facebook_service.check_and_maybe_post(
            quotes,
            gold_breakdown,
            silver_breakdown,
            force=True,
        )
    except Exception:
        logger.exception("خطا در وظیفهٔ بررسی/ارسال پست فیسبوک")


async def check_and_post_instagram_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        quotes, gold_breakdown, silver_breakdown = await get_current_quotes_and_metals()
        if not quotes:
            return

        last_state = db.get_ig_post_state()
        if not _usd_has_significant_change(
            quotes,
            last_state,
            INSTAGRAM_CHANGE_THRESHOLD_PERCENT,
        ):
            logger.info(
                "Instagram auto-post skipped: USD change below %.4f%% threshold; "
                "changes in other currencies/metals do not trigger posts.",
                INSTAGRAM_CHANGE_THRESHOLD_PERCENT,
            )
            return

        await instagram_service.check_and_maybe_post(
            quotes,
            gold_breakdown,
            silver_breakdown,
            force=True,
        )
    except Exception:
        logger.exception("خطا در وظیفهٔ بررسی/ارسال پست اینستاگرام")