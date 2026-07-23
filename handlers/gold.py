import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards import gold_karat_keyboard
from services import currency_service, gold_service

logger = logging.getLogger(__name__)


def _format_all(breakdown: dict) -> str:
    lines = [
        "🥇 *نرخ لحظه‌یی طلا*\n",
        f"قیمت جهانی: *{breakdown['price_usd_per_oz']:,.2f} دالر* برای هر اونس تروی\n",
    ]
    for karat, vals in breakdown["karats"].items():
        lines.append(
            f"▫️ عیار {karat}: *{vals['afn_per_gram']:,.0f} افغانی* "
            f"({vals['usd_per_gram']:,.2f}$) به ازای هر گرم — "
            f"مثقال: {vals['afn_per_methqal']:,.0f} افغانی"
        )
    return "\n".join(lines)


async def gold_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "عیار مدنظر خود را انتخاب کنید یا «نمایش همهٔ عیارها» را بزنید.",
        reply_markup=gold_karat_keyboard(),
    )


async def _get_breakdown() -> tuple[dict, str]:
    price_usd = await gold_service.get_gold_price_usd_per_oz()
    rates, source = await currency_service.get_afn_rates()
    afn_per_usd = rates.get("usd")
    if not afn_per_usd:
        raise RuntimeError("نرخ دالر برای محاسبهٔ طلا در دسترس نیست.")
    breakdown = gold_service.build_gold_breakdown(price_usd, afn_per_usd)
    return breakdown, source


async def gold_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, karat = query.data.split(":", 1)

    try:
        breakdown, source = await _get_breakdown()
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ طلا")
        await query.edit_message_text(f"⚠️ خطا در دریافت نرخ طلا: {exc}")
        return

    if karat == "all":
        text = _format_all(breakdown)
    else:
        k = int(karat)
        vals = breakdown["karats"][k]
        text = (
            f"🥇 *طلای عیار {k}*\n\n"
            f"هر گرم: *{vals['afn_per_gram']:,.0f} افغانی* ({vals['usd_per_gram']:,.2f}$)\n"
            f"هر مثقال: *{vals['afn_per_methqal']:,.0f} افغانی* ({vals['usd_per_methqal']:,.2f}$)"
        )

    await query.edit_message_text(text, parse_mode="Markdown")
