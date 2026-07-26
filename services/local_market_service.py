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

نکتهٔ مهم دربارهٔ استحکام پارسر:
  منبع همیشه ترتیب «خرید ... | فروش ...» را رعایت نمی‌کند و گاهی فاصله‌بندی
  یا حتی ترتیب را عوض می‌کند. به همین دلیل به‌جای فرض ثابت روی ترتیب متن،
  مقدار «خرید» و «فروش» را مستقل از هم و بر اساس برچسبشان استخراج می‌کنیم
  (تابع _extract_buy_sell) و اگر به هر دلیلی خرید از فروش بزرگ‌تر درآمد
  (که در بازار طلا منطقاً غلط است)، آن دو را جابه‌جا می‌کنیم تا داده‌ی
  نمایش‌داده‌شده به کاربر همیشه منطقی باشد.

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
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CATEGORY_URL = "https://afaaq.af/economic-fa/gold-price/"
_TIMEOUT = 12.0
CACHE_TTL_SECONDS = 900  # ۱۵ دقیقه (این منبع مقاله‌ای/روزانه است، نیازی به کش کوتاه نیست)

# اگر بیش از این مدت اسکرپ پی‌درپی شکست بخورد، داده‌ی کش‌شده را «بسیار قدیمی»
# در نظر می‌گیریم و به‌جای warning ساده، ERROR واضح در لاگ ثبت می‌کنیم تا
# در Railway/هر جای دیگر فوراً دیده شود.
STALE_ALERT_SECONDS = 3 * 60 * 60  # ۳ ساعت

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

_cache: dict = {"data": None, "fetched_at": 0.0, "last_success_wall": None}


def _to_num(s: str) -> Optional[float]:
    if not s:
        return None
    cleaned = s.translate(PERSIAN_DIGITS).replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_buy_sell(segment: str) -> Optional[dict]:
    """
    با جستجوی مستقل «خرید» و «فروش» در یک تکه از متن (بدون فرض بر ترتیب
    ظاهرشدنشان)، جفت (buy, sell) را استخراج می‌کند.

    اگر منبع یک روز به‌اشتباه ترتیب را برعکس نوشته باشد و در نتیجه خرید از
    فروش بزرگ‌تر دربیاید (که از نظر بازار طلا منطقاً نادرست است، چون صراف
    هیچ‌وقت گران‌تر نمی‌خرد تا ارزان‌تر بفروشد)، این دو مقدار جابه‌جا
    می‌شوند تا داده‌ی نهایی همیشه منطقی باشد.
    """
    buy_m = re.search(r"خرید\s*([۰-۹\d,]+)", segment)
    sell_m = re.search(r"فروش\s*([۰-۹\d,]+)", segment)
    if not buy_m or not sell_m:
        return None

    buy = _to_num(buy_m.group(1))
    sell = _to_num(sell_m.group(1))
    if buy is None or sell is None or buy <= 0 or sell <= 0:
        return None

    if buy > sell:
        logger.warning(
            "خرید (%s) از فروش (%s) بزرگ‌تر بود؛ مقادیر جابه‌جا شدند تا داده منطقی بماند.",
            buy, sell,
        )
        buy, sell = sell, buy

    return {"buy": round(buy, 1), "sell": round(sell, 1)}


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

    # ۱) خط تیتر «آبشدهٔ کابل/هرات» — بازار مستقیماً در پرانتز مشخص است.
    #    از finditer استفاده می‌کنیم (نه search) چون ممکن است بیش از یک عیار
    #    در این قالب ظاهر شود، و خرید/فروش را مستقل از ترتیب استخراج می‌کنیم.
    for market_fa, market_key in (("کابل", "kabul"), ("هرات", "herat")):
        pattern = (
            r"طلای\s*([۰-۹\d]+)\s*عیار\s*\(آبشده\s*" + market_fa + r"\)\s*:\s*(.*?)(?=\n|$)"
        )
        for m in re.finditer(pattern, text):
            karat = int(m.group(1).translate(PERSIAN_DIGITS))
            pair = _extract_buy_sell(m.group(2))
            if pair:
                result["melted"].setdefault(market_key, {})[karat] = pair

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
                r"طلای\s*([۰-۹\d]+)\s*عیار\s*:\s*(.*?)(?=\n|$)",
                melted_sub.group(1),
            ):
                karat = int(m.group(1).translate(PERSIAN_DIGITS))
                pair = _extract_buy_sell(m.group(2))
                if pair:
                    result["melted"].setdefault("herat", {})[karat] = pair

        for m in re.finditer(
            r"سکه\s*(ربع|نیم|کامل)\s*کارتی\s*:\s*(.*?)(?=\n|$)",
            block,
        ):
            pair = _extract_buy_sell(m.group(2))
            if pair:
                result["herat_coins"][m.group(1)] = pair

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
        _cache["last_success_wall"] = datetime.now(timezone.utc)
        return data
    except Exception as exc:
        if _cache["data"] is not None:
            age_seconds = (
                (datetime.now(timezone.utc) - _cache["last_success_wall"]).total_seconds()
                if _cache["last_success_wall"]
                else None
            )
            if age_seconds is not None and age_seconds > STALE_ALERT_SECONDS:
                logger.error(
                    "اسکرپ نرخ طلای afaaq.af پی‌درپی شکست می‌خورد؛ داده‌ی نمایش‌داده‌شده "
                    "حدود %.1f ساعت قدیمی است! خطای آخر: %s",
                    age_seconds / 3600, exc,
                )
            else:
                logger.warning("خطا در اسکرپ afaaq.af (نرخ طلا)، استفاده از کش اخیر: %s", exc)
            return _cache["data"]
        logger.exception("خطا در اسکرپ afaaq.af (نرخ طلا) و نبود هیچ کش قبلی")
        raise


def get_cache_age_seconds() -> Optional[float]:
    """برای دیباگ/دستور ادمین: چند ثانیه از آخرین اسکرپ موفق گذشته است."""
    if _cache["last_success_wall"] is None:
        return None
    return (datetime.now(timezone.utc) - _cache["last_success_wall"]).total_seconds()