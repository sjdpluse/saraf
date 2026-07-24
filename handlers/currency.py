import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import TRACKED_CURRENCIES
from keyboards import currency_list_keyboard
from services import rate_engine

logger = logging.getLogger(__name__)

# ارزهایی که باید به ازای هر ۱۰۰۰ واحد نمایش داده شوند
THOUSAND_UNIT_CURRENCIES = {"pkr", "irr", "inr"}


def _unit_label(code: str) -> str:
    return "هزار" if code in THOUSAND_UNIT_CURRENCIES else "یک"


def _scale(code: str, value: float) -> float:
    return value * 1000 if code in THOUSAND_UNIT_CURRENCIES else value


def _format_quote_block(code: str, name: str, quote: dict) -> str:
    unit = _unit_label(code)
    lines = [f"▫️ *{name}*"]

    saraf = quote["saraf_quote"]
    lines.append(
        f"   نرخ Saraf — خرید: *{_scale(code, saraf['buy']):,.2f}* | "
        f"فروش: *{_scale(code, saraf['sell']):,.2f}* افغانی ({unit})"
    )

    local = quote.get("local")
    if local:
        lines.append(
            f"   نرخ واقعی {local['market_label']} — خرید: {_scale(code, local['buy']):,.2f} | "
            f"فروش: {_scale(code, local['sell']):,.2f}"
        )

    if quote.get("reference_rate"):
        lines.append(f"   نرخ بازار آزاد جهانی: {_scale(code, quote['reference_rate']):,.2f}")

    return "\n".join(lines)


async def currency_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "کدام ارز مدنظر شماست؟ یا «نمایش همهٔ نرخ‌ها» را بزنید.",
        reply_markup=currency_list_keyboard(),
    )


async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, code = query.data.split(":", 1)

    if code == "all":
        await query.edit_message_text("در حال دریافت نرخ‌ها... ⏳")
        quotes = await rate_engine.get_full_quotes(list(TRACKED_CURRENCIES.keys()))
        if not quotes:
            await query.edit_message_text("⚠️ در حال حاضر هیچ نرخی در دسترس نیست.")
            return
        blocks = ["💵 *نرخ‌های Saraf — خرید و فروش*\n"]
        for c, name in TRACKED_CURRENCIES.items():
            if c in quotes:
                blocks.append(_format_quote_block(c, name, quotes[c]))
        text = "\n\n".join(blocks)
    else:
        name = TRACKED_CURRENCIES.get(code, code.upper())
        await query.edit_message_text("در حال دریافت نرخ... ⏳")
        try:
            quote = await rate_engine.get_full_quote(code)
        except Exception as exc:
            logger.exception("خطا در دریافت نرخ ارز")
            await query.edit_message_text(f"⚠️ خطا در دریافت نرخ ارز: {exc}")
            return
        text = f"💵 *نرخ {name}*\n\n" + _format_quote_block(code, name, quote)

    # پیام‌های طولانی تلگرام محدودیت طول دارند؛ در صورت نیاز کوتاه می‌کنیم
    if len(text) > 4000:
        text = text[:3990] + "\n…"

    await query.edit_message_text(text, parse_mode="Markdown")
