import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards import silver_calc_mode_keyboard
from services import currency_service, silver_service

logger = logging.getLogger(__name__)

AWAITING_SILVER_GRAMS = "awaiting_silver_grams"
SILVER_CALC_MODE = "silver_calc_mode"


async def _get_breakdown() -> tuple[dict, str]:
    price_usd = await silver_service.get_silver_price_usd_per_oz()
    rates, source = await currency_service.get_afn_rates()
    afn_per_usd = rates.get("usd")
    if not afn_per_usd:
        raise RuntimeError("نرخ دالر برای محاسبهٔ نقره در دسترس نیست.")
    breakdown = silver_service.build_silver_breakdown(price_usd, afn_per_usd)
    return breakdown, source


async def silver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    thinking_msg = await update.message.reply_text("در حال دریافت نرخ نقره... ⏳")
    try:
        breakdown, _source = await _get_breakdown()
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ نقره")
        await thinking_msg.edit_text(f"⚠️ خطا در دریافت نرخ نقره: {exc}")
        return

    text = (
        "🥈 *نرخ لحظه‌یی نقره (خالص)*\n\n"
        f"قیمت جهانی: *{breakdown['price_usd_per_oz']:,.2f} دالر* برای هر اونس تروی\n\n"
        f"هر گرم: *{breakdown['afn_per_gram']:,.1f} افغانی* ({breakdown['usd_per_gram']:,.4f}$)\n"
        f"هر مثقال: *{breakdown['afn_per_methqal']:,.1f} افغانی* ({breakdown['usd_per_methqal']:,.2f}$)"
    )
    await thinking_msg.edit_text(text, parse_mode="Markdown", reply_markup=silver_calc_mode_keyboard())


async def silver_calc_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, mode = query.data.split(":", 1)
    label = "خرید" if mode == "buy" else "فروش"

    context.user_data[AWAITING_SILVER_GRAMS] = True
    context.user_data[SILVER_CALC_MODE] = mode

    await query.edit_message_text(
        f"چند گرم نقره می‌خواهید {label} کنید؟ لطفاً فقط عدد را بنویسید (مثال: `10` یا `4.6`)",
        parse_mode="Markdown",
    )


async def handle_silver_grams_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر کاربر در حالت انتظار برای وارد کردن گرم نقره بود، محاسبه را انجام می‌دهد و True برمی‌گرداند."""
    if not context.user_data.get(AWAITING_SILVER_GRAMS):
        return False

    context.user_data[AWAITING_SILVER_GRAMS] = False
    mode = context.user_data.pop(SILVER_CALC_MODE, "buy")

    grams_str = update.message.text.strip().replace(",", ".")
    try:
        grams = float(grams_str)
        if grams <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ لطفاً یک عدد مثبت معتبر برای گرم وارد کنید.")
        return True

    thinking_msg = await update.message.reply_text("در حال محاسبه... ⏳")
    try:
        breakdown, _source = await _get_breakdown()
        result = silver_service.calculate_silver_transaction(breakdown, grams, is_buying=(mode == "buy"))
    except Exception as exc:
        logger.exception("خطا در محاسبهٔ خرید/فروش نقره")
        await thinking_msg.edit_text(f"⚠️ خطا: {exc}")
        return True

    label = "خرید" if result["is_buying"] else "فروش"
    text = (
        f"🧮 *نتیجهٔ محاسبهٔ {label} نقره*\n\n"
        f"مقدار: {result['grams']:g} گرم\n"
        f"قیمت پایه: {result['base_afn']:,.1f} افغانی ({result['base_usd']:,.2f}$)\n"
        f"{result['adjustment_label']}: {result['adjustment_pct']:.1f}٪\n\n"
        f"💰 مبلغ نهایی: *{result['final_afn']:,.1f} افغانی* ({result['final_usd']:,.2f}$)"
    )
    await thinking_msg.edit_text(text, parse_mode="Markdown")
    return True
