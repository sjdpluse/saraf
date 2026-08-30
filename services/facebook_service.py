"""
سرویس ارسال خودکار پست به صفحهٔ فیسبوک.
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
    FACEBOOK_HASHTAGS,
)
from persian_date import get_afghan_datetime_str
from services import post_image_service
from services import supabase_service as db

logger = logging.getLogger(__name__)

PHOTO_API_URL = "https://graph.facebook.com/v19.0/{page_id}/photos"
_TIMEOUT = 30.0
DIVIDER = "━━━━━━━━━━"
WHATSAPP_CHANNEL_URL = "https://whatsapp.com/channel/0029VbDBaZqC1FuAw0kj2G07"


def _unit_amount(code: str) -> int:
    return 1000 if code in THOUSAND_UNIT_CURRENCIES else 1


def _scale(code: str, value: float) -> float:
    return value * _unit_amount(code)


def _primary_rate(quote: dict) -> Optional[float]:
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
        return True
    for key, value in current.items():
        old = last.get(key)
        if not old:
            continue
        pct = abs(value - old) / old * 100
        if pct >= FACEBOOK_CHANGE_THRESHOLD_PERCENT:
            return True
    return False


def _build_currency_block(code: str, name: str, quote: dict) -> str:
    flag = CURRENCY_FLAGS.get(code, "")
    amount = _unit_amount(code)

    lines = [
        DIVIDER,
        f"{flag} ({amount}) {name}",
        "",
    ]

    local = quote.get("local")
    if local:
        lines.append(f"🏛 نرخ {local['market_label']}")
        lines.append(
            f"خرید: {_scale(code, local['buy']):,.2f}   |   "
            f"فروش: {_scale(code, local['sell']):,.2f}"
        )
        lines.append("")

    saraf = quote["saraf_quote"]
    lines.append("💱 نرخ صرافی‌های محلی")
    lines.append(
        f"خرید: {_scale(code, saraf['buy']):,.2f}   |   "
        f"فروش: {_scale(code, saraf['sell']):,.2f}"
    )
    lines.append("")

    if quote.get("reference_rate"):
        lines.append("🌍 نرخ بازار آزاد جهانی")
        lines.append(f"{_scale(code, quote['reference_rate']):,.2f} افغانی")

    lines.append(DIVIDER)
    return "\n".join(lines)


def _build_caption(quotes: dict, gold_breakdown: Optional[dict], silver_breakdown: Optional[dict] = None) -> str:
    date_str = get_afghan_datetime_str()
    lines = [
        "💵 نرخ ارزهای خارجی در برابر پول افغانی امروز — صراف",
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
    lines.append(f"📱 صراف در واتساپ: {WHATSAPP_CHANNEL_URL}")
    lines.append("")
    lines.append('🚀 برای بهره از تمامی خدمات صراف به‌صورت رایگان، کلمه "صراف" را کامنت کنید.')

    if FACEBOOK_HASHTAGS:
        lines.append("")
        lines.append(FACEBOOK_HASHTAGS)

    return "\n".join(lines)


def _extract_graph_error(resp: httpx.Response) -> str:
    try:
        err = resp.json().get("error", {})
        parts = [err.get("message") or resp.text[:300]]
        if err.get("type"):
            parts.append(f"type={err['type']}")
        if err.get("code") is not None:
            parts.append(f"code={err['code']}")
        if err.get("error_subcode") is not None:
            parts.append(f"subcode={err['error_subcode']}")
        return " | ".join(str(p) for p in parts)
    except Exception:
        return (resp.text or "پاسخ نامشخص از Graph API")[:300]


async def _post_photo_to_page(image_bytes: bytes, caption: str) -> tuple[bool, str]:
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        msg = "FACEBOOK_PAGE_ID یا FACEBOOK_PAGE_ACCESS_TOKEN تنظیم نشده"
        logger.warning(msg)
        return False, msg

    url = PHOTO_API_URL.format(page_id=FACEBOOK_PAGE_ID)
    data = {"caption": caption, "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    files = {"source": ("saraf-rates.png", image_bytes, "image/png")}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, data=data, files=files)
        if resp.status_code >= 400:
            detail = _extract_graph_error(resp)
            logger.error("خطای Graph API هنگام پست فیسبوک (HTTP %s): %s", resp.status_code, detail)
            return False, detail
        logger.info("پست تصویری فیسبوک با موفقیت ارسال شد.")
        return True, "ok"
    except Exception as exc:
        logger.exception("خطا در ارسال پست تصویری به فیسبوک")
        return False, f"خطای شبکه/غیرمنتظره: {exc}"


async def check_and_maybe_post(
    quotes: dict, gold_breakdown: Optional[dict], silver_breakdown: Optional[dict] = None, force: bool = False
) -> tuple[bool, str]:
    if not quotes:
        return False, "نرخی در دسترس نیست"

    current_state = _build_current_state(quotes, gold_breakdown, silver_breakdown)
    if not current_state:
        return False, "نرخی در دسترس نیست"

    last_state = db.get_fb_post_state()

    if not force and not _has_significant_change(current_state, last_state):
        return False, "تغییر محسوس نرخ رخ نداده (پست لازم نبود)"

    usd_quote = quotes.get("usd")
    if not usd_quote or not gold_breakdown:
        msg = "نرخ دالر یا اطلاعات طلا در دسترس نیست"
        logger.warning(msg)
        return False, msg

    try:
        date_str = get_afghan_datetime_str()
        image_bytes = await post_image_service.generate_facebook_post_image(
            usd_quote, gold_breakdown, date_str, silver_breakdown=silver_breakdown
        )
    except Exception as exc:
        logger.exception("خطا در تولید تصویر پست فیسبوک")
        return False, f"خطا در تولید تصویر: {exc}"

    caption = _build_caption(quotes, gold_breakdown, silver_breakdown)

    ok, detail = await _post_photo_to_page(image_bytes, caption)
    if ok:
        db.set_fb_post_state(current_state)
    return ok, detail
