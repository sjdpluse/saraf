"""
سرویس نرخ طلا.
منبع اصلی: gold-api.com — کاملاً رایگان، بدون کلید، بدون محدودیت درخواست برای قیمت لحظه‌یی.
(https://api.gold-api.com/price/XAU)

قیمت به دالر امریکایی به ازای هر اونس تروی (Troy Ounce) برگردانده می‌شود؛
سپس با نرخ دالر/افغانی (از currency_service) به افغانی و گرم/مثقال در عیارهای
مختلف (۲۴، ۲۲، ۲۱، ۱۸) تبدیل می‌گردد.
"""
import logging
from typing import Optional

import httpx

from config import GRAMS_PER_TROY_OUNCE, GRAMS_PER_METHQAL, GOLD_KARATS

logger = logging.getLogger(__name__)

GOLD_API_URL = "https://api.gold-api.com/price/XAU"
_TIMEOUT = 10.0


async def get_gold_price_usd_per_oz() -> float:
    """قیمت لحظه‌یی طلا به دالر برای هر اونس تروی را برمی‌گرداند."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(GOLD_API_URL)
        resp.raise_for_status()
        data = resp.json()

    # ساختار دقیق پاسخ ممکن است با گذشت زمان کمی تغییر کند، بنابراین چند کلید رایج را می‌آزماییم
    for key in ("price", "rate", "value"):
        if key in data and data[key]:
            return float(data[key])

    raise RuntimeError("قالب پاسخ gold-api.com شناسایی نشد؛ لطفاً کد را بازبینی کنید.")


def build_gold_breakdown(price_usd_per_oz: float, afn_per_usd: float) -> dict:
    """
    خروجی: دیکشرنی کامل شامل قیمت هر عیار به ازای گرم و مثقال، به دالر و افغانی.
    """
    price_afn_per_oz = price_usd_per_oz * afn_per_usd
    price_afn_per_gram_24k = price_afn_per_oz / GRAMS_PER_TROY_OUNCE
    price_usd_per_gram_24k = price_usd_per_oz / GRAMS_PER_TROY_OUNCE

    karats = {}
    for karat, factor in GOLD_KARATS.items():
        afn_gram = price_afn_per_gram_24k * factor
        usd_gram = price_usd_per_gram_24k * factor
        karats[karat] = {
            "afn_per_gram": round(afn_gram, 1),
            "usd_per_gram": round(usd_gram, 2),
            "afn_per_methqal": round(afn_gram * GRAMS_PER_METHQAL, 1),
            "usd_per_methqal": round(usd_gram * GRAMS_PER_METHQAL, 2),
        }

    return {
        "price_usd_per_oz": round(price_usd_per_oz, 2),
        "price_afn_per_oz": round(price_afn_per_oz, 1),
        "afn_per_gram_24k": round(price_afn_per_gram_24k, 1),
        "karats": karats,
    }
