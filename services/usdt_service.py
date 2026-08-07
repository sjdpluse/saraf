"""
سرویس محاسبهٔ نرخ خرید و فروش تتر (USDT).

مبنا: نرخ لحظه‌یی دالر در صرافی‌های محلی (rate_engine -> saraf_quote) که خودش
از نرخ واقعی سرای شهزاده یا در نبود آن نرخ مرجع جهانی به‌دست می‌آید.

خرید تتر (کاربر تتر می‌خرد، افغانی/دالر پرداخت می‌کند):
    مبنا = نرخ فروش دالر صرافی (saraf_quote.sell) + کارمزد پلکانی USDT_BUY_FEE_TIERS

فروش تتر (کاربر تتر می‌فروشد، افغانی دریافت می‌کند):
    مبنا = نرخ خرید دالر صرافی (saraf_quote.buy) — بدون کارمزد اضافه
"""
import logging

from config import USDT_BUY_FEE_TIERS, USDT_MIN_AMOUNT, USDT_MAX_AMOUNT
from services import rate_engine

logger = logging.getLogger(__name__)


class UsdtAmountError(ValueError):
    pass


def validate_amount(amount: float) -> None:
    if amount < USDT_MIN_AMOUNT or amount > USDT_MAX_AMOUNT:
        raise UsdtAmountError(
            f"مقدار باید بین {USDT_MIN_AMOUNT:g} تا {USDT_MAX_AMOUNT:g} USDT باشد."
        )


def get_buy_fee_percent(amount: float) -> float:
    for lo, hi, pct in USDT_BUY_FEE_TIERS:
        if lo <= amount <= hi:
            return pct
    if amount > USDT_BUY_FEE_TIERS[-1][1]:
        return USDT_BUY_FEE_TIERS[-1][2]
    return USDT_BUY_FEE_TIERS[0][2]


async def get_buy_quote(amount: float) -> dict:
    validate_amount(amount)
    quote = await rate_engine.get_full_quote("usd")
    usd_sell_rate = quote["saraf_quote"]["sell"]
    fee_pct = get_buy_fee_percent(amount)

    base_afn = amount * usd_sell_rate
    fee_afn = base_afn * fee_pct / 100
    total_afn = base_afn + fee_afn

    return {
        "amount": amount,
        "usd_rate": round(usd_sell_rate, 4),
        "fee_percent": fee_pct,
        "base_afn": round(base_afn, 1),
        "fee_afn": round(fee_afn, 1),
        "total_afn": round(total_afn, 1),
        "total_usd": round(amount, 2),
        "basis": quote["saraf_quote"]["basis"],
    }


async def get_sell_quote(amount: float) -> dict:
    validate_amount(amount)
    quote = await rate_engine.get_full_quote("usd")
    usd_buy_rate = quote["saraf_quote"]["buy"]
    total_afn = amount * usd_buy_rate

    return {
        "amount": amount,
        "usd_rate": round(usd_buy_rate, 4),
        "total_afn": round(total_afn, 1),
        "total_usd": round(amount, 2),
        "basis": quote["saraf_quote"]["basis"],
    }