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

from config import (
    GRAMS_PER_TROY_OUNCE,
    GRAMS_PER_METHQAL,
    GOLD_KARATS,
    GOLD_MAKING_CHARGE_PERCENT,
    GOLD_SELL_DEDUCTION_PERCENT,
)

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


def calculate_gold_transaction(
    breakdown: dict, karat: int, grams: float, is_buying: bool
) -> dict:
    """
    ماشین‌حساب خرید/فروش طلا.

    is_buying=True  -> مشتری می‌خواهد طلا بخرد: قیمت پایه + اجرت ساخت (GOLD_MAKING_CHARGE_PERCENT)
    is_buying=False -> مشتری می‌خواهد طلای خود را بفروشد: قیمت پایه - کسر صرافی (GOLD_SELL_DEDUCTION_PERCENT)

    خروجی شامل قیمت پایه، کسورات/اضافات، و مبلغ نهایی به افغانی و دالر است.
    """
    if karat not in breakdown["karats"]:
        raise ValueError(f"عیار {karat} پشتیبانی نمی‌شود.")
    if grams <= 0:
        raise ValueError("مقدار گرم باید بزرگ‌تر از صفر باشد.")

    per_gram_afn = breakdown["karats"][karat]["afn_per_gram"]
    per_gram_usd = breakdown["karats"][karat]["usd_per_gram"]

    base_afn = per_gram_afn * grams
    base_usd = per_gram_usd * grams

    if is_buying:
        adjustment_pct = GOLD_MAKING_CHARGE_PERCENT
        final_afn = base_afn * (1 + adjustment_pct / 100)
        final_usd = base_usd * (1 + adjustment_pct / 100)
        adjustment_label = "اجرت ساخت"
    else:
        adjustment_pct = GOLD_SELL_DEDUCTION_PERCENT
        final_afn = base_afn * (1 - adjustment_pct / 100)
        final_usd = base_usd * (1 - adjustment_pct / 100)
        adjustment_label = "کسر صرافی"

    return {
        "karat": karat,
        "grams": grams,
        "is_buying": is_buying,
        "base_afn": round(base_afn, 1),
        "base_usd": round(base_usd, 2),
        "adjustment_pct": adjustment_pct,
        "adjustment_label": adjustment_label,
        "final_afn": round(final_afn, 1),
        "final_usd": round(final_usd, 2),
    }
