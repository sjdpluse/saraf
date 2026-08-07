"""
وظایف زمان‌بندی‌شده:
  - fetch_and_store_snapshot: نرخ ارز و طلای مرجع (بین‌المللی) را می‌گیرد و ذخیره می‌کند.
  - fetch_and_store_local_market: نرخ واقعی بازارهای محلی افغانستان (اسکرپ sarafi.af)
    را می‌گیرد و ذخیره می‌کند؛ این داده مبنای نمایش bid/ask واقعی و محاسبهٔ نرخ Saraf است.
  - check_and_post_facebook_update: نرخ‌ها را بررسی و در صورت تغییر محسوس، تصویر
    پست فیسبوک (نرخ دالر + طلا) را می‌سازد و به همراه کپشن کامل منتشر می‌کند.
"""
import logging
from services import (
    currency_service,
    gold_service,
    local_market_service,
    rate_engine,
    facebook_service,
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


async def check_and_post_facebook_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        quotes = await rate_engine.get_full_quotes(list(TRACKED_CURRENCIES.keys()))
        if not quotes:
            return

        gold_breakdown = None
        usd_quote = quotes.get("usd")
        afn_per_usd = None
        if usd_quote:
            afn_per_usd = usd_quote.get("reference_rate") or usd_quote["saraf_quote"]["basis_rate"]
        if afn_per_usd:
            price_usd = await gold_service.get_gold_price_usd_per_oz()
            gold_breakdown = gold_service.build_gold_breakdown(price_usd, afn_per_usd)

        # به facebook_service خروجی کامل build_gold_breakdown پاس داده می‌شود (نه فقط یک عدد)
        # چون هم برای طراحی تصویر پست و هم برای تفکیک کامل عیارها در کپشن لازم است.
        await facebook_service.check_and_maybe_post(quotes, gold_breakdown)
    except Exception:
        logger.exception("خطا در وظیفهٔ بررسی/ارسال پست فیسبوک")
