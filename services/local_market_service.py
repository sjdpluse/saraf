"""
سرویس نرخ واقعی بازارهای محلی افغانستان (وب‌اسکرپینگ از sarafi.af).

منبع: https://sarafi.af/fa/exchange-rates/sarai-shahzada
این صفحه به‌طور هم‌زمان سه بازار را نمایش می‌دهد و همه را در یک درخواست استخراج می‌کنیم:
  - سرای شهزاده (کابل)      -> market key: "sarai_shahzada"   (منبع اصلی/اولویت اول)
  - مارکیت خراسان (هرات)     -> market key: "khorasan_market"
  - د افغانستان بانک (رسمی)  -> market key: "da_afg_bank"

خروجی هر بازار: {"usd": {"buy": 65.90, "sell": 65.95}, ...}
مقادیر «افغانی به ازای ۱ واحد ارز خارجی» است (نرخ خرید/فروش صرافی، نه نرخ مرجع بین‌المللی).

نکات مهم:
  - این یک وب‌اسکرپر است و به ساختار HTML سایت وابسته است؛ اگر سایت تغییر کند ممکن
    است نیاز به به‌روزرسانی HREF_RE یا منطق پارس داشته باشد.
  - نتیجه به مدت CACHE_TTL_SECONDS در حافظه کش می‌شود تا فشار زیادی به سایت مبدأ
    وارد نشود (رعایت ادب در اسکرپینگ).
  - در صورت شکست اسکرپ (تغییر ساختار سایت، قطعی، مسدودشدن و...) استثنا پرتاب می‌شود
    تا لایه‌های بالاتر بتوانند به نرخ مرجع بین‌المللی (currency_service) بازگردند.
"""
import logging
import re
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SARAFI_URL = "https://sarafi.af/fa/exchange-rates/sarai-shahzada"
_TIMEOUT = 12.0
CACHE_TTL_SECONDS = 300  # ۵ دقیقه

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "fa,en;q=0.8",
}

HREF_RE = re.compile(
    r"/exchange-rates/(sarai-shahzada|khorasan-market|da-afg-bank)/([A-Za-z]{3})-AFN"
)

_MARKET_KEY = {
    "sarai-shahzada": "sarai_shahzada",
    "khorasan-market": "khorasan_market",
    "da-afg-bank": "da_afg_bank",
}

# نام بازارها برای نمایش در پیام‌های ربات
MARKET_LABELS = {
    "sarai_shahzada": "سرای شهزاده (کابل)",
    "khorasan_market": "مارکیت خراسان (هرات)",
    "da_afg_bank": "د افغانستان بانک",
}

# بازار پیش‌فرض/اولویت‌دار برای نرخ «واقعی صرافی»
PRIMARY_MARKET = "sarai_shahzada"

_cache: dict = {"data": None, "fetched_at": 0.0}


def _to_float(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.strip().replace(",", ""))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_html(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    result: dict = {key: {} for key in _MARKET_KEY.values()}

    for a_tag in soup.find_all("a", href=True):
        match = HREF_RE.search(a_tag["href"])
        if not match:
            continue
        market_slug, code = match.groups()
        market_key = _MARKET_KEY[market_slug]
        code = code.lower()

        row = a_tag.find_parent("tr")
        if row is None:
            continue
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        buy = _to_float(cells[1].get_text())
        sell = _to_float(cells[2].get_text())
        if buy is None or sell is None or buy <= 0 or sell <= 0:
            continue

        # ارزهایی مثل تومان/کلدار/ین که به‌صورت «هزار واحد» نمایش داده می‌شوند
        # را به نرخ «هر ۱ واحد» عادی‌سازی می‌کنیم (هم‌راستا با currency_service)
        if "هزار" in a_tag.get_text():
            buy /= 1000
            sell /= 1000

        if code not in result[market_key]:
            result[market_key][code] = {"buy": round(buy, 6), "sell": round(sell, 6)}

    return result


async def _fetch_and_parse() -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(SARAFI_URL)
        resp.raise_for_status()

    data = _parse_html(resp.text)

    if not any(data[key] for key in data):
        raise RuntimeError(
            "هیچ نرخی از sarafi استخراج نشد؛ احتمالاً ساختار سایت تغییر کرده است."
        )
    return data


async def get_local_market_rates(force_refresh: bool = False) -> dict:
    """
    نرخ‌های واقعی بازارهای محلی را برمی‌گرداند (با کش ۵ دقیقه‌یی).
    خروجی: {"sarai_shahzada": {...}, "khorasan_market": {...}, "da_afg_bank": {...}}
    در صورت شکست اسکرپ و نبود کش معتبر، استثنا پرتاب می‌شود.
    """
    now = time.monotonic()
    is_fresh = _cache["data"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS

    if not force_refresh and is_fresh:
        return _cache["data"]

    try:
        data = await _fetch_and_parse()
        _cache["data"] = data
        _cache["fetched_at"] = now
        return data
    except Exception as exc:
        logger.warning("خطا در اسکرپ saraf: %s", exc)
        if _cache["data"] is not None:
            logger.info("استفاده از کش قدیمی نرخ‌های محلی به‌جای شکست کامل.")
            return _cache["data"]
        raise


async def get_primary_market_rate(code: str) -> Optional[dict]:
    """نرخ خرید/فروش یک ارز خاص را از بازار اصلی (سرای شهزاده) برمی‌گرداند، یا None."""
    data = await get_local_market_rates()
    return data.get(PRIMARY_MARKET, {}).get(code.lower())
