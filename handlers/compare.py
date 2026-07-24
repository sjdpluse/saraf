import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import TRACKED_CURRENCIES, CURRENCY_FLAGS
from keyboards import compare_target_keyboard, compare_period_keyboard
from services import gold_service, currency_service, rate_engine, spread_service
from services import supabase_service as db

logger = logging.getLogger(__name__)

GOLD_LABEL = "🥇 طلا (عیار ۲۴)"

PERIOD_LABELS = {
    1: "۲۴ ساعت گذشته",
    7: "هفتهٔ گذشته",
    30: "ماه گذشته",
    90: "سه ماه گذشته",
}

BASIS_LABELS = {
    "local": "بازار واقعی صرافی‌های کابل (سرای شهزاده)",
    "reference": "بازار آزاد جهانی",
}


def _label(code: str) -> str:
    name = TRACKED_CURRENCIES.get(code, code.upper())
    flag = CURRENCY_FLAGS.get(code, "")
    return f"{flag} {name}".strip()


async def compare_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📊 چه چیزی را می‌خواهید با گذشته مقایسه کنید؟",
        reply_markup=compare_target_keyboard(),
    )


async def compare_target_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, target = query.data.split(":", 1)
    target_name = GOLD_LABEL if target == "gold" else _label(target)

    await query.edit_message_text(
        f"{target_name}\n\nبا چه زمانی مقایسه شود؟",
        reply_markup=compare_period_keyboard(target, target_name),
    )


def _pct_change(old: float, new: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100


def _arrow(change: float) -> str:
    return "🔺" if change > 0 else ("🔻" if change < 0 else "⏸️")


async def _build_currency_comparison(code: str, days: int, when) -> str:
    label = _label(code)
    period_text = PERIOD_LABELS.get(days, f"{days} روز پیش")

    quote = await rate_engine.get_full_quote(code)
    current_buy = quote["saraf_quote"]["buy"]
    current_sell = quote["saraf_quote"]["sell"]
    current_basis = quote["saraf_quote"]["basis"]
    current_basis_rate = quote["saraf_quote"]["basis_rate"]

    old_basis_rate, old_basis = await rate_engine.get_historical_basis_rate(code, when)

    if old_basis_rate is None:
        return (
            f"📊 *{label}*\n\n"
            f"خرید فعلی: *{current_buy:,.2f}* | فروش فعلی: *{current_sell:,.2f}* افغانی\n"
            f"_(بر اساس {BASIS_LABELS.get(current_basis, current_basis)})_\n\n"
            "هنوز دادهٔ تاریخی کافی برای این بازهٔ زمانی ذخیره نشده است. ربات هر چند "
            "دقیقه یک بار نرخ‌ها را ثبت می‌کند؛ لطفاً کمی بعد دوباره امتحان کنید."
        )

    old_buy, old_sell = spread_service.apply_spread(old_basis_rate, code)
    change = _pct_change(old_basis_rate, current_basis_rate)
    arrow = _arrow(change)

    basis_note = ""
    if old_basis != current_basis:
        basis_note = (
            "\n\n⚠️ _توجه: نرخ فعلی بر اساس "
            f"{BASIS_LABELS.get(current_basis, current_basis)} و نرخ گذشته بر اساس "
            f"{BASIS_LABELS.get(old_basis, old_basis)} محاسبه شده (به‌دلیل نبود دادهٔ "
            "بازار محلی در آن زمان)._"
        )

    return (
        f"📊 *{label}* — مقایسه با {period_text}\n\n"
        f"🕰 *{period_text}*\n"
        f"خرید: {old_buy:,.2f} | فروش: {old_sell:,.2f} افغانی\n\n"
        f"⏱ *اکنون*\n"
        f"خرید: *{current_buy:,.2f}* | فروش: *{current_sell:,.2f}* افغانی\n\n"
        f"تغییر: {arrow} *{change:+.2f}%*\n"
        f"_(بر اساس {BASIS_LABELS.get(current_basis, current_basis)})_"
        f"{basis_note}"
    )


async def _build_gold_comparison(days: int, when) -> str:
    period_text = PERIOD_LABELS.get(days, f"{days} روز پیش")

    price_usd = await gold_service.get_gold_price_usd_per_oz()
    rates, _ = await currency_service.get_afn_rates()
    afn_per_usd = rates.get("usd")
    if not afn_per_usd:
        raise RuntimeError("نرخ دالر برای محاسبهٔ طلا در دسترس نیست.")

    breakdown = gold_service.build_gold_breakdown(price_usd, afn_per_usd)
    current = breakdown["afn_per_gram_24k"]

    old = db.get_closest_gold_rate(when)

    if old is None:
        return (
            f"📊 *{GOLD_LABEL}*\n\n"
            f"نرخ فعلی: *{current:,.1f} افغانی* به ازای هر گرم\n\n"
            "هنوز دادهٔ تاریخی کافی برای این بازهٔ زمانی ذخیره نشده است. لطفاً کمی "
            "بعد دوباره امتحان کنید."
        )

    change = _pct_change(old, current)
    arrow = _arrow(change)

    return (
        f"📊 *{GOLD_LABEL}* — مقایسه با {period_text}\n\n"
        f"🕰 *{period_text}*: {old:,.1f} افغانی (هر گرم)\n"
        f"⏱ *اکنون*: *{current:,.1f} افغانی* (هر گرم)\n\n"
        f"تغییر: {arrow} *{change:+.2f}%*"
    )


async def compare_period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, target, days_str = query.data.split(":", 2)
    days = int(days_str)
    when = db.time_ago(days=days)

    await query.edit_message_text("در حال دریافت اطلاعات مقایسه... ⏳")

    try:
        if target == "gold":
            text = await _build_gold_comparison(days, when)
        else:
            text = await _build_currency_comparison(target, days, when)
    except Exception as exc:
        logger.exception("خطا در مقایسهٔ نرخ‌ها")
        await query.edit_message_text(f"⚠️ خطا در دریافت اطلاعات: {exc}")
        return

    await query.edit_message_text(text, parse_mode="Markdown")