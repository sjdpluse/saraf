"""
سرویس نرخ نقره.
همان منبع gold_service.py یعنی gold-api.com — کاملاً رایگان، بدون کلید —
فقط با نماد XAG (نقره) به‌جای XAU (طلا): https://api.gold-api.com/price/XAG

برخلاف طلا که در بازار افغانستان با چند عیار رایج (۲۴/۲۲/۲۱/۱۸) معامله و در
gold_service.py مدل شده، برای نقره فقط یک عیار (خالص/۹۹۹ — رایج‌ترین شکل
عرضهٔ جهانی/سرمایه‌گذاری نقره) نمایش داده می‌شود، چون دادهٔ معتبری از رایج
بودن عیارهای دیگر برای نقره در بازار محلی در دسترس نبود؛ اگر بعداً این
اطلاعات مشخص شد، همین ماژول را می‌توان به همان شکل GOLD_KARATS گسترش داد.
"""
import logging

import httpx

from config import (
    GRAMS_PER_TROY_OUNCE,
    GRAMS_PER_METHQAL,
    SILVER_MAKING_CHARGE_PERCENT,
    SILVER_SELL_DEDUCTION_PERCENT,
)

logger = logging.getLogger(__name__)

SILVER_API_URL = "https://api.gold-api.com/price/XAG"
_TIMEOUT = 10.0


async def get_silver_price_usd_per_oz() -> float:
    """قیمت لحظه‌یی نقره به دالر برای هر اونس تروی را برمی‌گرداند."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(SILVER_API_URL)
        resp.raise_for_status()
        data = resp.json()

    for key in ("price", "rate", "value"):
        if key in data and data[key]:
            return float(data[key])

    raise RuntimeError("قالب پاسخ gold-api.com (نقره) شناسایی نشد؛ لطفاً کد را بازبینی کنید.")


def build_silver_breakdown(price_usd_per_oz: float, afn_per_usd: float) -> dict:
    price_afn_per_oz = price_usd_per_oz * afn_per_usd
    price_afn_per_gram = price_afn_per_oz / GRAMS_PER_TROY_OUNCE
    price_usd_per_gram = price_usd_per_oz / GRAMS_PER_TROY_OUNCE

    return {
        "price_usd_per_oz": round(price_usd_per_oz, 2),
        "price_afn_per_oz": round(price_afn_per_oz, 1),
        "afn_per_gram": round(price_afn_per_gram, 1),
        "usd_per_gram": round(price_usd_per_gram, 4),
        "afn_per_methqal": round(price_afn_per_gram * GRAMS_PER_METHQAL, 1),
        "usd_per_methqal": round(price_usd_per_gram * GRAMS_PER_METHQAL, 2),
    }


def calculate_silver_transaction(breakdown: dict, grams: float, is_buying: bool) -> dict:
    """ماشین‌حساب خرید/فروش نقره — دقیقاً همان منطق gold_service.calculate_gold_transaction."""
    if grams <= 0:
        raise ValueError("مقدار گرم باید بزرگ‌تر از صفر باشد.")

    per_gram_afn = breakdown["afn_per_gram"]
    per_gram_usd = breakdown["usd_per_gram"]

    base_afn = per_gram_afn * grams
    base_usd = per_gram_usd * grams

    if is_buying:
        adjustment_pct = SILVER_MAKING_CHARGE_PERCENT
        final_afn = base_afn * (1 + adjustment_pct / 100)
        final_usd = base_usd * (1 + adjustment_pct / 100)
        adjustment_label = "اجرت ساخت"
    else:
        adjustment_pct = SILVER_SELL_DEDUCTION_PERCENT
        final_afn = base_afn * (1 - adjustment_pct / 100)
        final_usd = base_usd * (1 - adjustment_pct / 100)
        adjustment_label = "کسر صرافی"

    return {
        "grams": grams,
        "is_buying": is_buying,
        "base_afn": round(base_afn, 1),
        "base_usd": round(base_usd, 2),
        "adjustment_pct": adjustment_pct,
        "adjustment_label": adjustment_label,
        "final_afn": round(final_afn, 1),
        "final_usd": round(final_usd, 2),
    }
