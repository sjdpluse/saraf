"""
سرویس محاسبهٔ نرخ خرید و فروش استیبل‌کوین‌های پشتیبانی‌شدهٔ صراف.

در حال حاضر دو دارایی پشتیبانی می‌شوند:
  - USDT (Tether)
  - USDC (USD Coin)

برای حفظ سازگاری با نسخه‌های قبلی، نام ماژول و تنظیمات USDT_* تغییر نکرده‌اند.
هر دو دارایی با مدل قیمت‌گذاری فعلی صراف بر مبنای نرخ لحظه‌یی دالر محلی محاسبه
می‌شوند و محدودیت مبلغ/پلکان کارمزد فعلی برای هر دو یکسان است.
"""
import logging
from decimal import Decimal

from config import USDT_BUY_FEE_TIERS, USDT_MIN_AMOUNT, USDT_MAX_AMOUNT
from services import rate_engine
from services.money import D, to_float, quantize_afn, quantize_usd, quantize_rate, quantize_percent

logger = logging.getLogger(__name__)

BUY_FEE_DISCOUNT_PERCENT = Decimal("0.5")
SUPPORTED_ASSETS = ("USDT", "USDC")
ASSET_NAMES_FA = {
    "USDT": "تتر",
    "USDC": "یو‌اس‌دی کوین",
}


class UsdtAmountError(ValueError):
    """نام legacy برای سازگاری با کدهای موجود؛ برای USDT و USDC استفاده می‌شود."""


class StablecoinAssetError(ValueError):
    pass


def normalize_asset(asset: str | None) -> str:
    value = str(asset or "USDT").strip().upper()
    if value not in SUPPORTED_ASSETS:
        raise StablecoinAssetError("دارایی انتخاب‌شده پشتیبانی نمی‌شود؛ فقط USDT و USDC قابل معامله‌اند.")
    return value


def asset_name_fa(asset: str | None) -> str:
    normalized = normalize_asset(asset)
    return ASSET_NAMES_FA[normalized]


def validate_amount(amount: float, asset: str = "USDT") -> None:
    asset = normalize_asset(asset)
    if amount is None or amount < USDT_MIN_AMOUNT or amount > USDT_MAX_AMOUNT:
        raise UsdtAmountError(
            f"مقدار باید بین {USDT_MIN_AMOUNT:g} تا {USDT_MAX_AMOUNT:g} {asset} باشد."
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


async def get_buy_quote(amount: float, asset: str = "USDT") -> dict:
    """نرخ خرید USDT/USDC با محاسبات Decimal و خروجی quantize‌شده."""
    asset = normalize_asset(asset)
    validate_amount(amount, asset)
    quote = await rate_engine.get_full_quote("usd")
    usd_sell_rate: Decimal = D(quote["saraf_quote"]["sell"])
    amount_d: Decimal = D(amount)
    original_fee_pct: Decimal = D(get_original_buy_fee_percent(amount))
    fee_pct: Decimal = max(original_fee_pct - BUY_FEE_DISCOUNT_PERCENT, Decimal("0"))

    base_afn = amount_d * usd_sell_rate
    fee_afn = base_afn * fee_pct / D(100)
    total_afn = base_afn + fee_afn

    return {
        "asset": asset,
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


async def get_sell_quote(amount: float, asset: str = "USDT") -> dict:
    asset = normalize_asset(asset)
    validate_amount(amount, asset)
    quote = await rate_engine.get_full_quote("usd")
    usd_buy_rate: Decimal = D(quote["saraf_quote"]["buy"])
    amount_d: Decimal = D(amount)
    total_afn = amount_d * usd_buy_rate

    return {
        "asset": asset,
        "amount": to_float(amount_d),
        "usd_rate": to_float(quantize_rate(usd_buy_rate)),
        "total_afn": to_float(quantize_afn(total_afn)),
        "total_usd": to_float(quantize_usd(amount_d)),
        "basis": quote["saraf_quote"]["basis"],
    }
