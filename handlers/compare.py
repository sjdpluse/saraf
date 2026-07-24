import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import TRACKED_CURRENCIES, CURRENCY_FLAGS
from keyboards import compare_target_keyboard, compare_period_keyboard
from services import currency_service, gold_service, supabase_service as db

logger = logging.getLogger(__name__)

GOLD_LABEL = "🥇 طلا (عیار ۲۴)"


def _label(code: str) -> str:
    name = TRACKED_CURRENCIES.get(code, code.upper())
    flag = CURRENCY_FLAGS.get(code, "")
    return f"{flag} {name}".strip()


async def compare_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "چه چیزی را می‌خواهید با گذشته مقایسه کنید؟",
        reply_markup=compare_target_keyboard(),
    )


async def compare_target_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, target = query.data.split(":", 1)
    target_name = GOLD_LABEL if target == "gold" else _label(target)

    await query.edit_message_text(
        f"{target_name}\n\nبا چند وقت پیش مقایسه شود؟",
        reply_markup=compare_period_keyboard(target, target_name),
    )


def _pct_change(old: float, new: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100


async def compare_period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, target, days_str = query.data.split(":", 2)
    days = int(days_str)
    when = db.time_ago(days=days)

    try:
        if target == "gold":
            price_usd = await gold_service.get_gold_price_usd_per_oz()
            rates, _ = await currency_service.get_afn_rates()
            afn_per_usd = rates.get("usd")
            breakdown = gold_service.build_gold_breakdown(price_usd, afn_per_usd)
            current = breakdown["afn_per_gram_24k"]
            old = db.get_closest_gold_rate(when)
            label = GOLD_LABEL
        else:
            rates, _ = await currency_service.get_afn_rates()
            current = rates.get(target)
            old = db.get_closest_currency_rate(target, when)
            label = _label(target)
    except Exception as exc:
        logger.exception("خطا در مقایسهٔ نرخ‌ها")
        await query.edit_message_text(f"⚠️ خطا در دریافت اطلاعات: {exc}")
        return

    if current is None:
        await query.edit_message_text("⚠️ متأسفانه نرخ فعلی در دسترس نیست.")
        return

    if old is None:
        text = (
            f"📊 *{label}*\n\n"
            f"نرخ فعلی: *{current:,.2f} افغانی*\n\n"
            "هنوز دادهٔ تاریخی کافی برای این بازهٔ زمانی در پایگاه‌داده ذخیره "
            "نشده است. ربات هر چند دقیقه یک بار نرخ‌ها را ثبت می‌کند؛ لطفاً "
            "بعد از مدتی دوباره امتحان کنید."
        )
    else:
        change = _pct_change(old, current)
        arrow = "🔺" if change > 0 else ("🔻" if change < 0 else "⏸️")
        text = (
            f"📊 *{label}* — مقایسه با {days} روز پیش\n\n"
            f"نرخ {days} روز پیش: *{old:,.2f} افغانی*\n"
            f"نرخ فعلی: *{current:,.2f} افغانی*\n"
            f"تغییر: {arrow} *{change:+.2f}%*"
        )

    await query.edit_message_text(text, parse_mode="Markdown")