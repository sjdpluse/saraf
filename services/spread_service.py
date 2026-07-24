"""
سرویس «حاشیهٔ سود صراف» (spread) — درصد تنظیم‌شده به ازای هر ارز که روی نرخ مرجع
اعمال می‌شود تا نرخ خرید/فروش قابل‌ارائهٔ ربات (نرخ Saraf) به‌دست آید.

نرخ خرید صراف = نرخ مرجع × (۱ - spread/2/100)
نرخ فروش صراف = نرخ مرجع × (۱ + spread/2/100)

یعنی spread یک درصد "کل فاصلهٔ" بین خرید و فروش است (نه فقط یک طرف)، که رایج‌ترین
برداشت از مفهوم bid/ask spread است.

تنظیمات از جدول Supabase (`spread_settings`) خوانده می‌شود؛ در صورت نبود مقدار
برای یک ارز خاص، از DEFAULT_SPREADS استفاده می‌شود.
"""
import logging
import time

from services import supabase_service as db

logger = logging.getLogger(__name__)

# مقادیر پیش‌فرض منطقی (٪) — ارزهای پرمعامله اسپرد کمتر، ارزهای کم‌معامله بیشتر
DEFAULT_SPREADS: dict[str, float] = {
    "usd": 0.6,
    "eur": 0.8,
    "gbp": 1.0,
    "aed": 0.8,
    "sar": 0.8,
    "pkr": 1.5,
    "irr": 2.0,
    "inr": 1.5,
    "try": 1.5,
    "cny": 1.5,
    "aud": 1.2,
    "cad": 1.2,
    "chf": 1.2,
    "sek": 1.8,
}
FALLBACK_DEFAULT_SPREAD = 1.5

_CACHE_TTL_SECONDS = 120
_cache: dict = {"data": None, "fetched_at": 0.0}


def _load_settings() -> dict[str, float]:
    now = time.monotonic()
    if _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL_SECONDS:
        return _cache["data"]
    try:
        data = db.get_all_spread_settings()
    except Exception:
        logger.exception("خطا در بارگذاری تنظیمات اسپرد؛ استفاده از مقادیر پیش‌فرض")
        data = {}
    _cache["data"] = data
    _cache["fetched_at"] = now
    return data


def get_spread_percent(currency: str) -> float:
    settings = _load_settings()
    code = currency.lower()
    if code in settings:
        return settings[code]
    return DEFAULT_SPREADS.get(code, FALLBACK_DEFAULT_SPREAD)


def set_spread_percent(currency: str, spread_percent: float) -> None:
    if spread_percent < 0 or spread_percent > 20:
        raise ValueError("درصد اسپرد باید بین ۰ تا ۲۰ باشد.")
    db.set_spread(currency.lower(), spread_percent)
    # کش را باطل می‌کنیم تا تغییر فوراً اعمال شود
    _cache["data"] = None


def apply_spread(reference_rate: float, currency: str) -> tuple[float, float]:
    """با گرفتن نرخ مرجع، (نرخ_خرید, نرخ_فروش) صراف را برمی‌گرداند."""
    spread_pct = get_spread_percent(currency)
    half = spread_pct / 2 / 100
    buy = reference_rate * (1 - half)
    sell = reference_rate * (1 + half)
    return round(buy, 4), round(sell, 4)


def get_all_effective_spreads(currencies: list[str]) -> dict[str, float]:
    return {code: get_spread_percent(code) for code in currencies}
