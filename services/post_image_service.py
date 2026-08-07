"""
سرویس تولید تصویر پست فیسبوک (۱۰۸۰×۱۰۸۰) شامل نرخ دالر امریکایی (سرای شهزاده،
صرافی‌های محلی، بازار آزاد جهانی) و طلای ۲۴ عیار — با طراحی UI حرفه‌یی و تم روشن.

نحوهٔ کار:
  ۱) قالب HTML/CSS از services/templates/facebook_post_template.html خوانده می‌شود.
  ۲) فونت فارسی Vazirmatn از assets/fonts به‌صورت base64 داخل CSS جاسازی می‌شود
     (کاملاً آفلاین و مستقل از دسترسی اینترنتی در لحظهٔ رندر).
  ۳) لوگوی Saraf از SARAF_LOGO_URL بارگیری و در حافظه کش می‌شود (۱ ساعت) تا هر بار
     درخواست جدید به سرور لوگو ارسال نشود.
  ۴) با Playwright (کرومیوم headless) قالب پرشده رندر و به PNG تبدیل می‌شود.

نیازمندی‌های استقرار (Deployment):
  - پکیج playwright باید نصب باشد (در requirements.txt اضافه شده).
  - در مرحلهٔ build سرویس (مثلاً Railway) باید یک‌بار دستور زیر اجرا شود تا
    مرورگر Chromium headless دانلود شود:
        playwright install --with-deps chromium
    بدون این مرحله، تولید تصویر با خطا مواجه می‌شود.
"""
import base64
import logging
import time
from pathlib import Path
from typing import Optional

import httpx
from playwright.async_api import async_playwright

from config import SARAF_LOGO_URL

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "assets" / "fonts"
TEMPLATE_PATH = BASE_DIR / "services" / "templates" / "facebook_post_template.html"

# وزن‌های فونت Vazirmatn مورد استفاده در قالب
_FONT_FILES = {
    400: "Vazirmatn-Regular.ttf",
    500: "Vazirmatn-Medium.ttf",
    600: "Vazirmatn-SemiBold.ttf",
    700: "Vazirmatn-Bold.ttf",
    900: "Vazirmatn-Black.ttf",
}

_LOGO_CACHE_TTL_SECONDS = 3600  # ۱ ساعت
_logo_cache: dict = {"data_uri": None, "fetched_at": 0.0}

_fonts_css_cache: Optional[str] = None


def _load_fonts_css() -> str:
    """فونت‌های Vazirmatn را یک‌بار می‌خواند، base64 می‌کند و در حافظه کش می‌کند."""
    global _fonts_css_cache
    if _fonts_css_cache is not None:
        return _fonts_css_cache

    rules = []
    for weight, filename in _FONT_FILES.items():
        path = FONTS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(
                f"فایل فونت یافت نشد: {path}. مطمئن شوید پوشهٔ assets/fonts در ریپازیتوری موجود است."
            )
        b64 = base64.b64encode(path.read_bytes()).decode()
        rules.append(
            f"@font-face {{ font-family:'Vazirmatn'; font-weight:{weight}; "
            f"src:url(data:font/ttf;base64,{b64}) format('truetype'); }}"
        )
    _fonts_css_cache = "\n  ".join(rules)
    return _fonts_css_cache


async def _get_logo_data_uri(force_refresh: bool = False) -> str:
    """
    لوگوی Saraf را از SARAF_LOGO_URL بارگیری کرده و به‌صورت data URI (base64) برمی‌گرداند.
    نتیجه به مدت ۱ ساعت کش می‌شود. در صورت شکست دانلود، اگر نسخهٔ کش‌شدهٔ قبلی موجود
    باشد از آن استفاده می‌شود (تا پست فیسبوک به‌خاطر قطعی موقت سرور لوگو متوقف نشود).
    """
    now = time.monotonic()
    is_fresh = _logo_cache["data_uri"] is not None and (now - _logo_cache["fetched_at"]) < _LOGO_CACHE_TTL_SECONDS

    if not force_refresh and is_fresh:
        return _logo_cache["data_uri"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(SARAF_LOGO_URL)
            resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/webp").split(";")[0].strip()
        b64 = base64.b64encode(resp.content).decode()
        data_uri = f"data:{content_type};base64,{b64}"
        _logo_cache["data_uri"] = data_uri
        _logo_cache["fetched_at"] = now
        return data_uri
    except Exception:
        logger.warning("خطا در بارگیری لوگوی Saraf از %s", SARAF_LOGO_URL, exc_info=True)
        if _logo_cache["data_uri"] is not None:
            logger.info("استفاده از لوگوی کش‌شدهٔ قبلی به‌جای شکست کامل.")
            return _logo_cache["data_uri"]
        raise RuntimeError(
            f"دریافت لوگو از {SARAF_LOGO_URL} ناموفق بود و نسخهٔ کش‌شده‌ای هم در دسترس نیست."
        )


def _fmt2(value: float) -> str:
    return f"{value:,.2f}"


def _build_html(quote: dict, gold_breakdown: dict, logo_data_uri: str, date_str: str) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    local = quote.get("local") or {}
    saraf = quote["saraf_quote"]
    reference_rate = quote.get("reference_rate")

    # نرخ سرای شهزاده (هیرو). اگر بازار محلی در دسترس نبود، با نرخ صرافی‌های Saraf پر می‌شود
    # تا کارت هیرو هرگز خالی نماند (graceful degradation، هم‌راستا با rate_engine).
    ss_buy = local.get("buy")
    ss_sell = local.get("sell")
    if ss_buy is None or ss_sell is None:
        ss_buy, ss_sell = saraf["buy"], saraf["sell"]

    gold_24k = gold_breakdown["karats"][24]

    values = {
        "__FONTS_CSS__": _load_fonts_css(),
        "__LOGO_SRC__": logo_data_uri,
        "__DATE__": date_str,
        "__SS_BUY__": _fmt2(ss_buy),
        "__SS_SELL__": _fmt2(ss_sell),
        "__LOC_BUY__": _fmt2(saraf["buy"]),
        "__LOC_SELL__": _fmt2(saraf["sell"]),
        "__REF_RATE__": _fmt2(reference_rate) if reference_rate else "—",
        "__GOLD_AFN__": f"{gold_24k['afn_per_gram']:,.0f} افغانی",
        "__GOLD_USD__": f"{gold_24k['usd_per_gram']:,.2f} دالر",
    }
    for key, val in values.items():
        template = template.replace(key, val)
    return template


async def generate_facebook_post_image(quote: dict, gold_breakdown: dict, date_str: str) -> bytes:
    """
    تصویر PNG نهایی پست فیسبوک را می‌سازد و بایت‌های آن را برمی‌گرداند.

    quote: خروجی rate_engine.get_full_quote("usd")
    gold_breakdown: خروجی gold_service.build_gold_breakdown(...)
    date_str: رشتهٔ تاریخ/ساعت افغانی (persian_date.get_afghan_datetime_str())
    """
    logo_data_uri = await _get_logo_data_uri()
    html = _build_html(quote, gold_breakdown, logo_data_uri, date_str)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            page = await browser.new_page(
                viewport={"width": 1080, "height": 1080}, device_scale_factor=2
            )
            await page.set_content(html, wait_until="load")
            png_bytes = await page.screenshot(type="png")
            return png_bytes
        finally:
            await browser.close()
