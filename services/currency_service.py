"""
سرویس نرخ ارز — با زنجیرهٔ منابع پشتیبان (fallback chain) کاملاً رایگان و بدون نیاز به کلید:

  1) fawazahmed0/currency-api  (jsdelivr CDN)   — منبع اصلی، بدون محدودیت درخواست
  2) همان پروژه روی آینهٔ pages.dev              — پشتیبان اول
  3) exchangerate-api.com (open access, v4)      — پشتیبان دوم

خروجی نهایی همیشه یک دیکشنری از نوع:
    {"usd": 71.23, "eur": 77.50, ...}
یعنی «چند افغانی به ازای ۱ واحد آن ارز» — همان شکلی که صرافی‌های افغانستان نمایش می‌دهند.
"""
import logging
from typing import Optional

import httpx

from config import TRACKED_CURRENCIES

logger = logging.getLogger(__name__)

JSDELIVR_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/afn.json"
PAGES_DEV_URL = "https://latest.currency-api.pages.dev/v1/currencies/afn.json"
EXCHANGERATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

_TIMEOUT = 10.0


async def _fetch_json(url: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("خطا در دریافت %s: %s", url, exc)
        return None


async def _from_afn_base(url: str) -> Optional[dict[str, float]]:
    """پاسخ این منابع به شکل {"afn": {"usd": 0.0143, ...}} است -> معکوس می‌کنیم."""
    data = await _fetch_json(url)
    if not data or "afn" not in data:
        return None
    afn_rates = data["afn"]
    result = {}
    for code in TRACKED_CURRENCIES:
        val = afn_rates.get(code)
        if val and val > 0:
            result[code] = round(1 / val, 4)
    return result if result else None


async def _from_exchangerate_api() -> Optional[dict[str, float]]:
    """این منبع بر مبنای USD است: rates["afn"] و rates[code] هر دو نسبت به ۱ دالر.
    afn_per_unit(code) = rates["afn"] / rates[code]
    """
    data = await _fetch_json(EXCHANGERATE_API_URL)
    if not data or "rates" not in data:
        return None
    rates = data["rates"]
    afn_per_usd = rates.get("AFN")
    if not afn_per_usd:
        return None
    result = {}
    for code in TRACKED_CURRENCIES:
        unit_rate = rates.get(code.upper())
        if code == "usd":
            result[code] = round(afn_per_usd, 4)
        elif unit_rate and unit_rate > 0:
            result[code] = round(afn_per_usd / unit_rate, 4)
    return result if result else None


async def get_afn_rates() -> tuple[dict[str, float], str]:
    """
    نرخ‌های لحظه‌یی افغانی در برابر ارزهای پیگیری‌شده را برمی‌گرداند.
    خروجی: (دیکشنری نرخ‌ها, نام منبع استفاده‌شده)
    در صورت شکست همهٔ منابع، یک استثنا پرتاب می‌شود.
    """
    rates = await _from_afn_base(JSDELIVR_URL)
    if rates:
        return rates, "fawazahmed0/currency-api (jsdelivr)"

    rates = await _from_afn_base(PAGES_DEV_URL)
    if rates:
        return rates, "fawazahmed0/currency-api (pages.dev)"

    rates = await _from_exchangerate_api()
    if rates:
        return rates, "exchangerate-api.com"

    raise RuntimeError(
        "هیچ‌یک از منابع نرخ ارز در دسترس نبودند. لطفاً دقایقی دیگر تلاش کنید."
    )
