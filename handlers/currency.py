import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import TRACKED_CURRENCIES
from keyboards import currency_list_keyboard
from services import currency_service

logger = logging.getLogger(__name__)

# ارزهایی که باید به ازای هر ۱۰۰۰ واحد نمایش داده شوند
THOUSAND_UNIT_CURRENCIES = {"pkr", "irr", "inr"}


def _format_all(rates: dict[str, float], source: str) -> str:
    lines = ["💵 *نرخ لحظه‌یی ارزها در برابر افغانی*\n"]
    for code, name in TRACKED_CURRENCIES.items():
        rate = rates.get(code)
        if rate is not None:
            # برای تومان، نرخ ریال را به تومان تبدیل می‌کنیم (۱ تومان = ۱۰ ریال)
            if code == "irr":
                rate *= 10

            if code in THOUSAND_UNIT_CURRENCIES:
                lines.append(
                    f"▫️ هزار {name}: *{rate * 1000:,.4f}* افغانی"
                )
            else:
                lines.append(f"▫️ {name}: *{rate:,.2f}* افغانی")
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

    try:
        rates, source = await currency_service.get_afn_rates()
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ ارز")
        await query.edit_message_text(f"⚠️ خطا در دریافت نرخ ارز: {exc}")
        return

    if code == "all":
        text = _format_all(rates, source)
    else:
        name = TRACKED_CURRENCIES.get(code, code.upper())
        rate = rates.get(code)
        if rate is None:
            text = f"متأسفانه در حال حاضر نرخ {name} در دسترس نیست."
        else:
            # برای تومان، نرخ ریال را به تومان تبدیل می‌کنیم (۱ تومان = ۱۰ ریال)
            if code == "irr":
                rate *= 10

            if code in THOUSAND_UNIT_CURRENCIES:
                text = (
                    f"💵 *نرخ {name}*\n\n"
                    f"هزار ({name}): *{rate * 1000:,.4f}* افغانی"
                )
            else:
                text = (
                    f"💵 *نرخ {name}*\n\n"
                    f"یک ({name}): *{rate:,.2f}* افغانی"
                )

    await query.edit_message_text(text, parse_mode="Markdown")
