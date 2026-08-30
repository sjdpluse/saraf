"""
سرویس محاسبهٔ نرخ خرید و فروش تتر (USDT).

مبنا: نرخ لحظه‌یی دالر در صرافی‌های محلی (rate_engine -> saraf_quote) که خودش
از نرخ واقعی سرای شهزاده یا در نبود آن نرخ مرجع جهانی به‌دست می‌آید.

خرید تتر (کاربر تتر می‌خرد، افغانی/دالر پرداخت می‌کند):
    مبنا = نرخ فروش دالر صرافی (saraf_quote.sell) + کارمزد پلکانی تخفیفی.
    پله‌های اصلی از config خوانده می‌شوند و فعلاً ۰.۵ واحد درصد تخفیف روی هر پله
    اعمال می‌شود؛ یعنی ۲.۵/۲/۱.۵ به ۲/۱.۵/۱ درصد تبدیل می‌شود.

فروش تتر (کاربر تتر می‌فروشد، افغانی دریافت می‌کند):
    مبنا = نرخ خرید دالر صرافی (saraf_quote.buy) — بدون کارمزد اضافه
"""
import logging
from decimal import Decimal

from config import USDT_BUY_FEE_TIERS, USDT_MIN_AMOUNT, USDT_MAX_AMOUNT
from services import rate_engine
from services.money import D, to_float, quantize_afn, quantize_usd, quantize_rate, quantize_percent

logger = logging.getLogger(__name__)

BUY_FEE_DISCOUNT_PERCENT = Decimal("0.5")


class UsdtAmountError(ValueError):
    pass


def validate_amount(amount: float) -> None:
    # مقایسهٔ کران‌ها روی مقدار خام کافی است (فقط validation، نه محاسبهٔ مالی)؛
    # محاسبهٔ واقعی مبلغ همیشه با Decimal انجام می‌شود.
    if amount is None or amount < USDT_MIN_AMOUNT or amount > USDT_MAX_AMOUNT:
        raise UsdtAmountError(
            f"مقدار باید بین {USDT_MIN_AMOUNT:g} تا {USDT_MAX_AMOUNT:g} USDT باشد."
        )


def get_original_buy_fee_percent(amount: float) -> float:
    for lo, hi, pct in USDT_BUY_FEE_TIERS:
        if lo <= amount <= hi:
            return pct
    if amount > USDT_BUY_FEE_TIERS[-1][1]:
        return USDT_BUY_FEE_TIERS[-1][2]
    return USDT_BUY_FEE_TIERS[0][2]


def get_buy_fee_percent(amount: float) -> float:
    original = D(get_original_buy_fee_percent(amount))
    discounted = max(original - BUY_FEE_DISCOUNT_PERCENT, Decimal("0"))
    return to_float(discounted)


async def get_buy_quote(amount: float) -> dict:
    """
    تمام محاسبات پولی این تابع با Decimal انجام می‌شود (SARAF 2.0 Spec §13).
    گرد کردن (rounding) فقط در انتها و روی هر فیلد با دقت مخصوص خودش انجام می‌شود؛
    خروجی JSON/UI به float تبدیل می‌شود، اما همان مقدار Decimal quantize‌شده است.
    """
    validate_amount(amount)
    quote = await rate_engine.get_full_quote("usd")
    usd_sell_rate: Decimal = D(quote["saraf_quote"]["sell"])
    amount_d: Decimal = D(amount)
    original_fee_pct: Decimal = D(get_original_buy_fee_percent(amount))
    fee_pct: Decimal = max(original_fee_pct - BUY_FEE_DISCOUNT_PERCENT, Decimal("0"))

    base_afn = amount_d * usd_sell_rate
    fee_afn = base_afn * fee_pct / D(100)
    total_afn = base_afn + fee_afn

    return {
        "amount": to_float(amount_d),
        "usd_rate": to_float(quantize_rate(usd_sell_rate)),
        "original_fee_percent": to_float(quantize_percent(original_fee_pct)),
        "fee_percent": to_float(quantize_percent(fee_pct)),
        "base_afn": to_float(quantize_afn(base_afn)),
        "fee_afn": to_float(quantize_afn(fee_afn)),
        "total_afn": to_float(quantize_afn(total_afn)),
        "total_usd": to_float(quantize_usd(amount_d)),
        "basis": quote["saraf_quote"]["basis"],
    }


async def get_sell_quote(amount: float) -> dict:
    validate_amount(amount)
    quote = await rate_engine.get_full_quote("usd")
    usd_buy_rate: Decimal = D(quote["saraf_quote"]["buy"])
    amount_d: Decimal = D(amount)
    total_afn = amount_d * usd_buy_rate

    return {
        "amount": to_float(amount_d),
        "usd_rate": to_float(quantize_rate(usd_buy_rate)),
        "total_afn": to_float(quantize_afn(total_afn)),
        "total_usd": to_float(quantize_usd(amount_d)),
        "basis": quote["saraf_quote"]["basis"],
    }