"""
سرویس ارسال خودکار پست به صفحهٔ فیسبوک.

از نسخهٔ فعلی به بعد، ربات به‌جای پست متنی ساده، یک تصویر ۱۰۸۰×۱۰۸۰ حرفه‌یی
(طراحی‌شده در post_image_service با داده‌های لحظه‌یی نرخ دالر، طلا و نقره) به همراه
یک کپشن کامل (شامل نرخ همهٔ ارزها، تفکیک کامل عیارهای طلا، نرخ نقره، لینک ربات و
هشتگ‌ها) در صفحهٔ فیسبوک منتشر می‌کند.

بخش نرخ ارزهای کپشن دقیقاً همان قالبی را دارد که در ربات تلگرام («نمایش همهٔ
نرخ‌ها») نمایش داده می‌شود: برای هر ارز یک بلوکِ جداگانه شامل نرخ سرای شهزاده،
نرخ صرافی‌های محلی (Saraf) و نرخ بازار آزاد جهانی، با خط‌جداکننده در ابتدا و
انتهای هر بلوک.

فقط زمانی پست جدید ارسال می‌شود که تغییر محسوس نرخ (بیشتر یا مساوی
FACEBOOK_CHANGE_THRESHOLD_PERCENT) نسبت به آخرین پست ارسال‌شده رخ داده باشد؛
این وضعیت در جدول Supabase (`fb_post_state`) نگهداری می‌شود تا با ری‌استارت
شدن پردازه از بین نرود.

نیازمند: FACEBOOK_PAGE_ID و FACEBOOK_PAGE_ACCESS_TOKEN (راهنمای ساخت در README).
"""
import logging
from typing import Optional

import httpx

from config import (
    TRACKED_CURRENCIES,
    CURRENCY_FLAGS,
    THOUSAND_UNIT_CURRENCIES,
    FACEBOOK_PAGE_ID,
    FACEBOOK_PAGE_ACCESS_TOKEN,
    FACEBOOK_CHANGE_THRESHOLD_PERCENT,
    FACEBOOK_POST_SITE_URL,
    FACEBOOK_HASHTAGS,
    TELEGRAM_BOT_LINK,
)
from persian_date import get_afghan_datetime_str
from services import post_image_service
from services import supabase_service as db

logger = logging.getLogger(__name__)

PHOTO_API_URL = "https://graph.facebook.com/v19.0/{page_id}/photos"
_TIMEOUT = 30.0
DIVIDER = "━━━━━━━━━━"


def _unit_amount(code: str) -> int:
    """ارزهایی مثل تومان/کلدار/روپیه به ازای هر ۱۰۰۰ واحد نمایش داده می‌شوند
    (هم‌راستا با handlers/currency.py تا کپشن فیسبوک با ربات تلگرام یکسان باشد)."""
    return 1000 if code in THOUSAND_UNIT_CURRENCIES else 1


def _scale(code: str, value: float) -> float:
    return value * _unit_amount(code)


def _primary_rate(quote: dict) -> Optional[float]:
    """اولویت نمایش: سرای شهزاده، در نبود آن صرافی‌های محلی."""
    local = quote.get("local")
    if local:
        return local["buy"]
    saraf = quote.get("saraf_quote")
    return saraf["buy"] if saraf else None


def _primary_sell(quote: dict) -> Optional[float]:
    local = quote.get("local")
    if local:
        return local["sell"]
    saraf = quote.get("saraf_quote")
    return saraf["sell"] if saraf else None


def _build_current_state(quotes: dict, gold_breakdown: Optional[dict], silver_breakdown: Optional[dict] = None) -> dict:
    state = {}
    for code, quote in quotes.items():
        rate = _primary_rate(quote)
        if rate:
            state[code] = rate
    if gold_breakdown:
        state["gold_24k"] = gold_breakdown["karats"][24]["afn_per_gram"]
    if silver_breakdown:
        state["silver"] = silver_breakdown["afn_per_gram"]
    return state


def _has_significant_change(current: dict, last: dict) -> bool:
    if not last:
        return True  # اولین اجرا -> همیشه پست شود
    for key, value in current.items():
        old = last.get(key)
        if not old:
            continue
        pct = abs(value - old) / old * 100
        if pct >= FACEBOOK_CHANGE_THRESHOLD_PERCENT:
            return True
    return False


def _build_currency_block(code: str, name: str, quote: dict) -> str:
    """دقیقاً هم‌شکل با _format_quote_block_for_all در handlers/currency.py؛
    برای اینکه کپشن فیسبوک هم مثل «نمایش همهٔ نرخ‌ها» در ربات تلگرام نمایش داده شود."""
    flag = CURRENCY_FLAGS.get(code, "")
    amount = _unit_amount(code)

    lines = [
        DIVIDER,
        f"{flag} ({amount}) {name}",
        "",
    ]

    # ۱) نرخ سرای شهزاده
    local = quote.get("local")
    if local:
        lines.append(f"🏛 نرخ {local['market_label']}")
        lines.append(
            f"خرید: {_scale(code, local['buy']):,.2f}   |   "
            f"فروش: {_scale(code, local['sell']):,.2f}"
        )
        lines.append("")

    # ۲) نرخ خرید/فروش صرافی‌های محلی (نرخ Saraf)
    saraf = quote["saraf_quote"]
    lines.append("💱 نرخ صرافی‌های محلی")
    lines.append(
        f"خرید: {_scale(code, saraf['buy']):,.2f}   |   "
        f"فروش: {_scale(code, saraf['sell']):,.2f}"
    )
    lines.append("")

    # ۳) نرخ بازار آزاد جهانی
    if quote.get("reference_rate"):
        lines.append("🌍 نرخ بازار آزاد جهانی")
        lines.append(f"{_scale(code, quote['reference_rate']):,.2f} افغانی")

    lines.append(DIVIDER)

    return "\n".join(lines)


def _build_caption(quotes: dict, gold_breakdown: Optional[dict], silver_breakdown: Optional[dict] = None) -> str:
    """کپشن کامل پست فیسبوک: نرخ همهٔ ارزها (به‌سبک نمایش تلگرام) + تفکیک کامل
    طلا + نرخ نقره + لینک ربات + هشتگ‌ها."""
    date_str = get_afghan_datetime_str()
    lines = [
        "💵 (Saraf) نرخ ارزهای خارجی در برابر پول افغانی امروز — صراف",
        date_str,
        "",
    ]

    for code, name in TRACKED_CURRENCIES.items():
        quote = quotes.get(code)
        if not quote:
            continue
        lines.append(_build_currency_block(code, name, quote))
        lines.append("")

    if gold_breakdown:
        lines.append("🥇 نرخ لحظه‌یی طلا")
        lines.append("")
        lines.append(
            f"قیمت جهانی: {gold_breakdown['price_usd_per_oz']:,.2f} دالر برای هر اونس تروی"
        )
        lines.append("")
        for karat in sorted(gold_breakdown["karats"].keys(), reverse=True):
            vals = gold_breakdown["karats"][karat]
            lines.append(
                f"▫️ عیار {karat}: {vals['afn_per_gram']:,.0f} افغانی "
                f"({vals['usd_per_gram']:,.2f}$) به ازای هر گرم — "
                f"مثقال: {vals['afn_per_methqal']:,.0f} افغانی"
            )

    if silver_breakdown:
        lines.append("")
        lines.append("🥈 نرخ لحظه‌یی نقره (خالص/۹۹۹)")
        lines.append("")
        lines.append(
            f"قیمت جهانی: {silver_breakdown['price_usd_per_oz']:,.2f} دالر برای هر اونس تروی"
        )
        lines.append(
            f"▫️ {silver_breakdown['afn_per_gram']:,.0f} افغانی "
            f"({silver_breakdown['usd_per_gram']:,.2f}$) به ازای هر گرم — "
            f"مثقال: {silver_breakdown['afn_per_methqal']:,.0f} افغانی"
        )

    lines.append("")
    lines.append("🚀 نمایش همهٔ نرخ‌ها، مبدل ارز جهانی و ماشین‌حساب طلا، کاملاً رایگان و لحظه‌یی؛")
    lines.append("همین حالا به ربات صراف بپیوندید:")
    lines.append(TELEGRAM_BOT_LINK)

    if FACEBOOK_POST_SITE_URL:
        lines.append(FACEBOOK_POST_SITE_URL)

    if FACEBOOK_HASHTAGS:
        lines.append("")
        lines.append(FACEBOOK_HASHTAGS)

    return "\n".join(lines)


async def _post_photo_to_page(image_bytes: bytes, caption: str) -> bool:
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.warning("FACEBOOK_PAGE_ID یا FACEBOOK_PAGE_ACCESS_TOKEN تنظیم نشده؛ پست انجام نشد.")
        return False

    url = PHOTO_API_URL.format(page_id=FACEBOOK_PAGE_ID)
    data = {"caption": caption, "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    files = {"source": ("saraf-rates.png", image_bytes, "image/png")}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, data=data, files=files)
            resp.raise_for_status()
        logger.info("پست تصویری فیسبوک با موفقیت ارسال شد.")
        return True
    except Exception:
        logger.exception("خطا در ارسال پست تصویری به فیسبوک")
        return False


async def check_and_maybe_post(
    quotes: dict, gold_breakdown: Optional[dict], silver_breakdown: Optional[dict] = None, force: bool = False
) -> bool:
    """
    gold_breakdown: خروجی کامل gold_service.build_gold_breakdown(...) —
    نه فقط یک عدد، چون هم برای طراحی تصویر و هم برای کپشن (تفکیک همهٔ عیارها) لازم است.
    silver_breakdown: خروجی کامل silver_service.build_silver_breakdown(...) — اختیاری؛
        اگر داده نشود، پیل نقرهٔ تصویر خط تیره نمایش می‌دهد و کپشن بخش نقره ندارد.
    force: اگر True باشد، بررسی «تغییر محسوس نرخ» نادیده گرفته می‌شود و پست
        همیشه منتشر می‌شود — برای نشر دستی (دکمهٔ ادمین در ربات) استفاده می‌شود.

    خروجی: True اگر پست واقعاً با موفقیت منتشر شد، در غیر این صورت False (چه
    به‌خاطر نبود تغییر محسوس، چه به‌خاطر خطا) — برای نمایش نتیجه به ادمین در
    دکمهٔ نشر دستی لازم است.
    """
    if not quotes:
        return False

    current_state = _build_current_state(quotes, gold_breakdown, silver_breakdown)
    if not current_state:
        return False

    last_state = db.get_fb_post_state()

    if not force and not _has_significant_change(current_state, last_state):
        return False

    usd_quote = quotes.get("usd")
    if not usd_quote or not gold_breakdown:
        logger.warning("نرخ دالر یا اطلاعات طلا در دسترس نیست؛ تولید تصویر پست فیسبوک ممکن نیست.")
        return False

    try:
        date_str = get_afghan_datetime_str()
        image_bytes = await post_image_service.generate_facebook_post_image(
            usd_quote, gold_breakdown, date_str, silver_breakdown=silver_breakdown
        )
    except Exception:
        logger.exception("خطا در تولید تصویر پست فیسبوک")
        return False

    caption = _build_caption(quotes, gold_breakdown, silver_breakdown)

    if await _post_photo_to_page(image_bytes, caption):
        db.set_fb_post_state(current_state)
        return True
    return False