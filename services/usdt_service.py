"""سرویس محاسبهٔ نرخ خرید و فروش استیبل‌کوین‌های پشتیبانی‌شدهٔ صراف.

مدل خرید از ۱۰ سپتمبر ۲۰۲۶ دیگر «۲٪ کمیسیون جداگانه» ندارد. قیمت خرید بر مبنای
حاشیهٔ بازار محلی ساخته می‌شود و همان حاشیه بین تأمین‌کننده، صراف و مشتری تقسیم
می‌گردد:

  - ۵۰٪ حاشیهٔ بازار: سهم تأمین‌کننده
  - ۳۰٪ حاشیهٔ بازار: سهم صراف
  - ۲۰٪ حاشیهٔ بازار: تخفیف مشتری

کالیبراسیون فعلی بر اساس Quoteهای واقعی تأمین‌کنندگان محلی کاربر است:
  - سفارش‌های تا ۵۰ USDT/USDC: حاشیهٔ کل بازار ۲ دالر
  - بالاتر از ۵۰: حاشیهٔ کل بازار ۲.۵٪ از مقدار معامله

Binance عمداً مبنای قیمت‌گذاری نیست؛ خرید کارتی Binance فقط می‌تواند منبع پشتیبان
تأمین نقدینگی باشد و هزینهٔ بالاتر آن نباید روی نرخ عادی مشتری تحمیل شود.
"""
import logging
from decimal import Decimal

from config import USDT_MIN_AMOUNT, USDT_MAX_AMOUNT
from services import rate_engine
from services.money import D, to_float, quantize_afn, quantize_usd, quantize_rate, quantize_percent

logger = logging.getLogger(__name__)

SUPPORTED_ASSETS = ("USDT", "USDC")
ASSET_NAMES_FA = {
    "USDT": "تتر",
    "USDC": "یو‌اس‌دی کوین",
}

# مدل فعلی بازار محلی. این مقادیر باید فقط با Quote واقعی تأمین‌کنندگان به‌روزرسانی شوند.
SMALL_ORDER_MAX = Decimal("50")
SMALL_ORDER_MARKET_MARGIN_USD = Decimal("2")
LARGE_ORDER_MARKET_MARGIN_PERCENT = Decimal("2.5")

SUPPLIER_SHARE_PERCENT = Decimal("50")
SARAF_SHARE_PERCENT = Decimal("30")
CUSTOMER_DISCOUNT_SHARE_PERCENT = Decimal("20")


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


def get_market_margin_usd(amount: float | Decimal) -> Decimal:
    """حاشیهٔ کل بازار قبل از تقسیم بین تأمین‌کننده/صراف/مشتری."""
    amount_d = D(amount)
    if amount_d <= SMALL_ORDER_MAX:
        return SMALL_ORDER_MARKET_MARGIN_USD
    return amount_d * LARGE_ORDER_MARKET_MARGIN_PERCENT / D(100)


def build_buy_pricing(amount: float | Decimal, usd_rate: float | Decimal) -> dict:
    """شکست کامل اقتصاد یک سفارش خرید با Decimal.

    customer_payable = اصل معامله + سهم تأمین‌کننده + سهم صراف
    customer_discount = بخشی از حاشیهٔ بازار که صراف عمداً از آن صرف‌نظر می‌کند.
    """
    amount_d = D(amount)
    rate_d = D(usd_rate)
    market_margin_usd = get_market_margin_usd(amount_d)

    supplier_profit_usd = market_margin_usd * SUPPLIER_SHARE_PERCENT / D(100)
    saraf_profit_usd = market_margin_usd * SARAF_SHARE_PERCENT / D(100)
    customer_discount_usd = market_margin_usd * CUSTOMER_DISCOUNT_SHARE_PERCENT / D(100)

    supplier_payout_usd = amount_d + supplier_profit_usd
    customer_payable_usd = supplier_payout_usd + saraf_profit_usd
    market_price_usd = amount_d + market_margin_usd

    base_afn = amount_d * rate_d
    supplier_profit_afn = supplier_profit_usd * rate_d
    saraf_profit_afn = saraf_profit_usd * rate_d
    customer_discount_afn = customer_discount_usd * rate_d
    supplier_payout_afn = supplier_payout_usd * rate_d
    market_price_afn = market_price_usd * rate_d
    total_afn = customer_payable_usd * rate_d

    effective_premium_percent = (
        ((customer_payable_usd - amount_d) / amount_d) * D(100)
        if amount_d > 0
        else D(0)
    )

    return {
        "market_margin_usd": to_float(quantize_usd(market_margin_usd)),
        "market_margin_percent": to_float(quantize_percent((market_margin_usd / amount_d) * D(100))),
        "supplier_share_percent": to_float(quantize_percent(SUPPLIER_SHARE_PERCENT)),
        "saraf_share_percent": to_float(quantize_percent(SARAF_SHARE_PERCENT)),
        "customer_discount_share_percent": to_float(quantize_percent(CUSTOMER_DISCOUNT_SHARE_PERCENT)),
        "supplier_profit_usd": to_float(quantize_usd(supplier_profit_usd)),
        "saraf_profit_usd": to_float(quantize_usd(saraf_profit_usd)),
        "customer_discount_usd": to_float(quantize_usd(customer_discount_usd)),
        "supplier_payout_usd": to_float(quantize_usd(supplier_payout_usd)),
        "market_price_usd": to_float(quantize_usd(market_price_usd)),
        "customer_payable_usd": to_float(quantize_usd(customer_payable_usd)),
        "effective_premium_percent": to_float(quantize_percent(effective_premium_percent)),
        "base_afn": to_float(quantize_afn(base_afn)),
        "supplier_profit_afn": to_float(quantize_afn(supplier_profit_afn)),
        "saraf_profit_afn": to_float(quantize_afn(saraf_profit_afn)),
        "customer_discount_afn": to_float(quantize_afn(customer_discount_afn)),
        "supplier_payout_afn": to_float(quantize_afn(supplier_payout_afn)),
        "market_price_afn": to_float(quantize_afn(market_price_afn)),
        "total_afn": to_float(quantize_afn(total_afn)),
    }


# Legacy API: کمیسیون جداگانهٔ خرید حذف شده است.
def get_original_buy_fee_percent(amount: float) -> float:
    return 0.0


def get_buy_fee_percent(amount: float) -> float:
    return 0.0


async def get_buy_quote(amount: float, asset: str = "USDT") -> dict:
    """Quote خرید بر اساس بازار محلی + تقسیم حاشیه 50/30/20."""
    asset = normalize_asset(asset)
    validate_amount(amount, asset)
    quote = await rate_engine.get_full_quote("usd")

    # برای خرید استیبل‌کوین، نرخ فروش واقعی بازار محلی از نرخ دارای spread داخلی
    # صراف دقیق‌تر است و مانع اضافه‌شدن حاشیهٔ مخفی جدا از مدل 50/30/20 می‌شود.
    local_sell = (quote.get("local") or {}).get("sell")
    if local_sell is not None:
        usd_sell_rate: Decimal = D(local_sell)
        pricing_basis = "local_sell"
    else:
        usd_sell_rate = D(quote["saraf_quote"]["sell"])
        pricing_basis = quote["saraf_quote"]["basis"]

    amount_d: Decimal = D(amount)
    pricing = build_buy_pricing(amount_d, usd_sell_rate)

    return {
        "asset": asset,
        "amount": to_float(amount_d),
        "usd_rate": to_float(quantize_rate(usd_sell_rate)),
        # فیلدهای legacy برای سازگاری دیتابیس/کلاینت؛ دیگر کمیسیون جداگانه‌ای نداریم.
        "original_fee_percent": 0.0,
        "fee_percent": 0.0,
        "fee_afn": 0.0,
        "total_usd": pricing["customer_payable_usd"],
        "payable_usd": pricing["customer_payable_usd"],
        "pricing_model": "local_margin_share_50_30_20",
        "basis": pricing_basis,
        **pricing,
    }


async def get_sell_quote(amount: float, asset: str = "USDT") -> dict:
    asset = normalize_asset(asset)
    validate_amount(amount, asset)
    quote = await rate_engine.get_full_quote("usd")
    usd_buy_rate: Decimal = D(quote["saraf_quote"]["buy"])
    amount_d: Decimal = D(amount)
    total_afn = amount_d * usd_buy_rate
    receivable_usd = total_afn / usd_buy_rate

    return {
        "asset": asset,
        "amount": to_float(amount_d),
        "usd_rate": to_float(quantize_rate(usd_buy_rate)),
        "total_afn": to_float(quantize_afn(total_afn)),
        "total_usd": to_float(quantize_usd(amount_d)),
        "receivable_usd": to_float(quantize_usd(receivable_usd)),
        "basis": quote["saraf_quote"]["basis"],
    }
