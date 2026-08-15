import logging

from telegram import Update
from telegram.ext import ContextTypes

from persian_date import get_afghan_datetime_str
from services import crypto_service, currency_service

logger = logging.getLogger(__name__)

DIVIDER = "━━━━━━━━━━"


def _format_usd(price: float) -> str:
    """رمزارزهایی مثل شیبا اینو قیمت خیلی کوچکی دارند (مثلاً 0.000018$)، پس رقم
    اعشار بر اساس بزرگی خودِ عدد تعیین می‌شود، نه یک فرمت ثابت برای همه."""
    if price < 0.001:
        return f"{price:,.8f}"
    if price < 1:
        return f"{price:,.4f}"
    return f"{price:,.2f}"


async def crypto_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    thinking_msg = await update.message.reply_text("در حال دریافت نرخ رمزارزها... ⏳")
    try:
        prices = await crypto_service.get_crypto_prices_usd()
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ رمزارزها")
        await thinking_msg.edit_text(f"⚠️ خطا در دریافت نرخ رمزارزها: {exc}")
        return

    afn_per_usd = None
    try:
        rates, _source = await currency_service.get_afn_rates()
        afn_per_usd = rates.get("usd")
    except Exception:
        logger.warning("نرخ دالر/افغانی برای نمایش معادل افغانی رمزارزها در دسترس نیست")

    date_str = get_afghan_datetime_str()
    lines = [f"🪙 *نرخ لحظه‌یی رمزارزها — صراف*\n{date_str}\n"]

    for symbol, price_usd in prices.items():
        name = crypto_service.CRYPTO_NAMES.get(symbol, symbol.upper())
        lines.append(DIVIDER)
        lines.append(f"*{name} ({symbol.upper()})*")
        line = f"{_format_usd(price_usd)}$"
        if afn_per_usd:
            afn_val = price_usd * afn_per_usd
            line += f"   |   {_format_usd(afn_val)} افغانی"
        lines.append(line)

    lines.append(DIVIDER)
    text = "\n".join(lines)
    await thinking_msg.edit_text(text, parse_mode="Markdown")
