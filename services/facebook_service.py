"""
سرویس ارسال خودکار پست به صفحهٔ فیسبوک.

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
    FACEBOOK_PAGE_ID,
    FACEBOOK_PAGE_ACCESS_TOKEN,
    FACEBOOK_CHANGE_THRESHOLD_PERCENT,
    FACEBOOK_POST_SITE_URL,
)
from persian_date import get_afghan_datetime_str
from services import supabase_service as db

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v19.0/{page_id}/feed"
_TIMEOUT = 15.0


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


def _build_current_state(quotes: dict, gold_afn_gram: Optional[float]) -> dict:
    state = {}
    for code, quote in quotes.items():
        rate = _primary_rate(quote)
        if rate:
            state[code] = rate
    if gold_afn_gram:
        state["gold_24k"] = gold_afn_gram
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


def _build_message(quotes: dict, gold_afn_gram: Optional[float]) -> str:
    date_str = get_afghan_datetime_str()
    lines = ["💠 نرخ لحظه‌یی ارز و طلا — Saraf", date_str, ""]

    for code, name in TRACKED_CURRENCIES.items():
        quote = quotes.get(code)
        if not quote:
            continue
        buy = _primary_rate(quote)
        sell = _primary_sell(quote)
        if not buy:
            continue
        flag = CURRENCY_FLAGS.get(code, "")
        lines.append(f"{flag} {name}: خرید {buy:,.2f}  |  فروش {sell:,.2f}")

    if gold_afn_gram:
        lines.append("")
        lines.append(f"🥇 طلای ۲۴ عیار: {gold_afn_gram:,.0f} افغانی (هر گرم)")

    lines.append("")
    lines.append("همهٔ نرخ‌ها و مبدل ارز جهانی، لحظه‌یی:")
    if FACEBOOK_POST_SITE_URL:
        lines.append(FACEBOOK_POST_SITE_URL)

    return "\n".join(lines)


async def _post_to_page(message: str) -> bool:
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.warning("FACEBOOK_PAGE_ID یا FACEBOOK_PAGE_ACCESS_TOKEN تنظیم نشده؛ پست انجام نشد.")
        return False

    url = GRAPH_API_URL.format(page_id=FACEBOOK_PAGE_ID)
    payload = {"message": message, "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    if FACEBOOK_POST_SITE_URL:
        payload["link"] = FACEBOOK_POST_SITE_URL

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, data=payload)
            resp.raise_for_status()
        logger.info("پست فیسبوک با موفقیت ارسال شد.")
        return True
    except Exception:
        logger.exception("خطا در ارسال پست به فیسبوک")
        return False


async def check_and_maybe_post(quotes: dict, gold_afn_gram: Optional[float]) -> None:
    if not quotes:
        return

    current_state = _build_current_state(quotes, gold_afn_gram)
    if not current_state:
        return

    last_state = db.get_fb_post_state()

    if not _has_significant_change(current_state, last_state):
        return

    message = _build_message(quotes, gold_afn_gram)
    if await _post_to_page(message):
        db.set_fb_post_state(current_state)