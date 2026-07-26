"""
موتور یکپارچه‌سازی نرخ طلا — مشابه rate_engine.py برای ارز، اما با یک تفاوت
مهم: منبع محلی طلا (afaaq.af) برای طلای «نو»/استاندارد کابل فقط یک نرخ رسمی
تک‌عددی می‌دهد، نه خرید/فروش. بنابراین برای این عیارها، خرید/فروش «Saraf» با
اعمال اسپرد قابل‌تنظیم روی همان نرخ رسمی ساخته می‌شود. برای طلای آبشده (کابل و
هرات) و سکه‌های کارتی هرات، چون منبع خودش خرید/فروش واقعی می‌دهد، همان مقادیر
واقعی به‌عنوان مبنا استفاده می‌شوند.
"""
import logging

from services import gold_service, gold_market_service, spread_service

logger = logging.getLogger(__name__)


async def _get_reference_breakdown() -> dict:
    from services import currency_service

    price_usd = await gold_service.get_gold_price_usd_per_oz()
    rates, _source = await currency_service.get_afn_rates()
    afn_per_usd = rates.get("usd")
    if not afn_per_usd:
        raise RuntimeError("نرخ دالر برای محاسبهٔ طلا در دسترس نیست.")
    return gold_service.build_gold_breakdown(price_usd, afn_per_usd)


async def get_full_gold_quote(karat: int) -> dict:
    """
    خروجی نمونه برای عیار ۱۸:
    {
      "karat": 18,
      "reference": {"afn_per_gram": 7500.0, "usd_per_gram": 107.5},
      "kabul_official": 7930.0,                 # ممکن است None باشد
      "melted": {
          "kabul": {"buy": 7930.0, "sell": 8030.0},   # ممکن است None باشد
          "herat": {"buy": 7200.0, "sell": 7250.0},   # ممکن است None باشد
      },
      "saraf_quote": {"buy": 7850.0, "sell": 8010.0, "basis": "melted_kabul"},
      "spread_percent": 1.2,
    }
    """
    reference_breakdown = await _get_reference_breakdown()
    reference = reference_breakdown["karats"].get(karat)

    local_data = {}
    try:
        local_data = await gold_market_service.get_gold_market_data()
    except Exception:
        logger.warning("نرخ واقعی طلای افغانستان در دسترس نیست؛ استفاده از نرخ جهانی")

    kabul_official = local_data.get("kabul_official", {}).get(karat)
    melted_kabul = local_data.get("melted", {}).get("kabul", {}).get(karat)
    melted_herat = local_data.get("melted", {}).get("herat", {}).get(karat)

    # اولویت مبنا: طلای آبشدهٔ کابل (واقعی‌ترین) > نرخ رسمی کابل > آبشدهٔ هرات > نرخ جهانی
    if melted_kabul:
        basis_rate = (melted_kabul["buy"] + melted_kabul["sell"]) / 2
        basis = "melted_kabul"
    elif kabul_official:
        basis_rate = kabul_official
        basis = "kabul_official"
    elif melted_herat:
        basis_rate = (melted_herat["buy"] + melted_herat["sell"]) / 2
        basis = "melted_herat"
    elif reference:
        basis_rate = reference["afn_per_gram"]
        basis = "reference"
    else:
        raise RuntimeError(f"هیچ نرخی برای عیار {karat} در دسترس نیست.")

    spread_key = f"gold{karat}"
    saraf_buy, saraf_sell = spread_service.apply_spread(basis_rate, spread_key)
    spread_pct = spread_service.get_spread_percent(spread_key)

    return {
        "karat": karat,
        "reference": reference,
        "kabul_official": kabul_official,
        "melted": {"kabul": melted_kabul, "herat": melted_herat},
        "saraf_quote": {"buy": saraf_buy, "sell": saraf_sell, "basis": basis},
        "spread_percent": spread_pct,
    }


async def get_herat_coins() -> dict:
    """سکه‌های کارتی هرات — این‌ها خودشان خرید/فروش واقعی دارند، بدون نیاز به اسپرد."""
    try:
        local_data = await gold_market_service.get_gold_market_data()
        return local_data.get("herat_coins", {})
    except Exception:
        logger.warning("نرخ سکه‌های کارتی هرات در دسترس نیست")
        return {}
