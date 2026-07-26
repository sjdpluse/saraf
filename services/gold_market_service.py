"""
سرویس نرخ واقعی طلا در بازار افغانستان (وب‌اسکرپینگ از afaaq.af).

منبع: https://afaaq.af/economic-fa/gold-price/  (صفحهٔ دسته‌بندی که همیشه
تازه‌ترین گزارش روزانه را اول نشان می‌دهد؛ چون آدرس مقالهٔ روزانه ثابت نیست
و هر بار قالب متفاوتی دارد، ابتدا لینک اولین مقاله از این صفحه استخراج و
سپس خودِ مقاله واکشی و پارس می‌شود.)

نکتهٔ مهم دربارهٔ ساختار واقعی بازار (که باید در نمایش به کاربر هم منعکس شود):

  - برای طلای «نو»/استاندارد در کابل (عیار ۲۲، ۲۱، ۱۸، ۱۴) این منبع فقط
    یک عدد «نرخ رسمی اتحادیهٔ زرگران» منتشر می‌کند، نه خرید/فروش جداگانه.
    (این محدودیت منبع است، نه محدودیت کد ما.)
  - برای طلای «آبشده» (دست‌دوم/ذوب‌شده، هم کابل هم هرات) و سکه‌های کارتی
    هرات، خرید و فروش واقعی و جداگانه منتشر می‌شود.

خروجی get_gold_market_data():
{
  "kabul_official": {22: 9820.0, 21: 9409.0, 18: 7930.0, 14: 6300.0},
  "melted": {
      "kabul": {18: {"buy": 7930.0, "sell": 8030.0}},
      "herat": {21: {"buy": 8440.0, "sell": 8500.0}, 18: {"buy": 7200.0, "sell": 7250.0}},
  },
  "herat_coins": {"ربع": {"buy":..,"sell":..}, "نیم": {...}, "کامل": {...}},
  "ounce_usd": 4726.0,
}
"""
import logging
import re
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CATEGORY_URL = "https://afaaq.af/economic-fa/gold-price/"
_TIMEOUT = 12.0
CACHE_TTL_SECONDS = 900  # ۱۵ دقیقه (این منبع مقاله‌ای/روزانه است، نیازی به کش کوتاه نیست)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "fa,en;q=0.8",
}

# نوهای ثابت (nav) که نباید به‌عنوان مقالهٔ روزانه در نظر گرفته شوند
_NAV_PATH_SUFFIXES = {"economic-fa", "economic-fa/exchange-rate", "economic-fa/gold-price"}

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

_cache: dict = {"data": None, "fetched_at": 0.0}


def _to_num(s: str) -> Optional[float]:
    if not s:
        return None
    cleaned = s.translate(PERSIAN_DIGITS).replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


async def _fetch(url: str) -> str:
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def _find_latest_article_url(category_html: str) -> Optional[str]:
    soup = BeautifulSoup(category_html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].rstrip("/")
        if "afaaq.af/economic-fa/" not in href:
            continue
        path = href.split("afaaq.af/")[-1]
        if path in _NAV_PATH_SUFFIXES:
            continue
        # اولین لینک مقالهٔ واقعی که پیدا شود، تازه‌ترین گزارش روزانه است
        return href + "/"
    return None


def _parse_article(text: str) -> dict:
    result = {"kabul_official": {}, "melted": {}, "herat_coins": {}, "ounce_usd": None}

    # ۱) خط تیتر «آبشدهٔ کابل/هرات» — بازار مستقیماً در پرانتز مشخص است
    for market_fa, market_key in (("کابل", "kabul"), ("هرات", "herat")):
        pattern = (
            r"طلای\s*([۰-۹\d]+)\s*عیار\s*\(آبشده\s*" + market_fa + r"\)\s*:\s*"
            r"خرید\s*([۰-۹\d,]+)\s*افغانی\s*\|\s*فروش\s*([۰-۹\d,]+)\s*افغانی"
        )
        m = re.search(pattern, text)
        if m:
            karat = int(m.group(1).translate(PERSIAN_DIGITS))
            result["melted"].setdefault(market_key, {})[karat] = {
                "buy": _to_num(m.group(2)),
                "sell": _to_num(m.group(3)),
            }

    # ۲) نرخ رسمی تک‌عددی کابل (طلای نو/استاندارد)
    kabul_block_match = re.search(
        r"نرخ طلای اعلامی اتحادیه زرگران کابل امروز:(.*?)(?:نرخ طلا در بازار هرات|$)",
        text, re.S,
    )
    if kabul_block_match:
        for m in re.finditer(
            r"طلای\s*[۰-۹\d]+\s*یا\s*([۰-۹\d]+)\s*عیار\**\s*:\s*یک\s*گرم\s*([۰-۹\d,]+)\s*افغانی",
            kabul_block_match.group(1),
        ):
            karat = int(m.group(1).translate(PERSIAN_DIGITS))
            price = _to_num(m.group(2))
            if price:
                result["kabul_official"][karat] = price

    # ۳) بلاک هرات: طلای آبشده (بدون برچسب صریح شهر در همین خط، پس اسکوپ می‌کنیم) + سکه‌های کارتی
    herat_block_match = re.search(
        r"طبق نرخ اتحادیه زرگران هرات:(.*?)(?:قیمت انس جهانی|$)",
        text, re.S,
    )
    if herat_block_match:
        block = herat_block_match.group(1)
        melted_sub = re.search(r"طلای آبشده:(.*?)(?:####|$)", block, re.S)
        if melted_sub:
            for m in re.finditer(
                r"طلای\s*([۰-۹\d]+)\s*عیار\s*:\s*خرید\s*([۰-۹\d,]+)\s*افغانی\s*\|\s*فروش\s*([۰-۹\d,]+)\s*افغانی",
                melted_sub.group(1),
            ):
                karat = int(m.group(1).translate(PERSIAN_DIGITS))
                result["melted"].setdefault("herat", {})[karat] = {
                    "buy": _to_num(m.group(2)),
                    "sell": _to_num(m.group(3)),
                }

        for m in re.finditer(
            r"سکه\s*(ربع|نیم|کامل)\s*کارتی\s*:\s*خرید\s*([۰-۹\d,]+)\s*افغانی\s*\|\s*فروش\s*([۰-۹\d,]+)\s*افغانی",
            block,
        ):
            result["herat_coins"][m.group(1)] = {
                "buy": _to_num(m.group(2)),
                "sell": _to_num(m.group(3)),
            }

    # ۴) انس جهانی (به‌عنوان مرجع اضافی؛ منبع اصلی انس همچنان gold-api.com است)
    ounce_match = re.search(r"یک\s*انس\s*طلا\s*:\s*حدود\s*([۰-۹\d,]+)\s*دلار", text)
    if ounce_match:
        result["ounce_usd"] = _to_num(ounce_match.group(1))

    return result


async def _fetch_and_parse() -> dict:
    category_html = await _fetch(CATEGORY_URL)
    article_url = _find_latest_article_url(category_html)
    if not article_url:
        raise RuntimeError("لینک تازه‌ترین گزارش نرخ طلا در afaaq.af پیدا نشد.")

    article_html = await _fetch(article_url)
    soup = BeautifulSoup(article_html, "lxml")
    text = soup.get_text("\n")

    data = _parse_article(text)
    if not data["kabul_official"] and not data["melted"]:
        raise RuntimeError("هیچ نرخ طلایی از مقالهٔ afaaq.af استخراج نشد؛ احتمالاً قالب صفحه تغییر کرده.")

    data["source_url"] = article_url
    return data


async def get_gold_market_data(force_refresh: bool = False) -> dict:
    """نرخ واقعی طلای افغانستان را برمی‌گرداند (با کش ۱۵ دقیقه‌یی)."""
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
        logger.warning("خطا در اسکرپ afaaq.af (نرخ طلا): %s", exc)
        if _cache["data"] is not None:
            return _cache["data"]
        raise
