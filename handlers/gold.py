import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards import gold_karat_keyboard, gold_calc_mode_keyboard, gold_calc_karat_keyboard
from services import currency_service, gold_service

logger = logging.getLogger(__name__)

AWAITING_GOLD_GRAMS = "awaiting_gold_grams"
GOLD_CALC_MODE = "gold_calc_mode"
GOLD_CALC_KARAT = "gold_calc_karat"


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
        "عیار مدنظر خود را انتخاب کنید، «نمایش همهٔ عیارها» را بزنید، یا از "
        "ماشین‌حساب خرید/فروش استفاده کنید.",
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

    if karat == "calc":
        await query.edit_message_text(
            "می‌خواهید طلا بخرید یا بفروشید؟", reply_markup=gold_calc_mode_keyboard()
        )
        return

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


async def gold_calc_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, mode = query.data.split(":", 1)
    label = "خرید" if mode == "buy" else "فروش"
    await query.edit_message_text(
        f"عیار طلای مورد نظر برای {label} را انتخاب کنید:",
        reply_markup=gold_calc_karat_keyboard(mode),
    )


async def gold_calc_karat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, mode, karat = query.data.split(":", 2)

    context.user_data[AWAITING_GOLD_GRAMS] = True
    context.user_data[GOLD_CALC_MODE] = mode
    context.user_data[GOLD_CALC_KARAT] = int(karat)

    label = "خرید" if mode == "buy" else "فروش"
    await query.edit_message_text(
        f"چند گرم طلای عیار {karat} می‌خواهید {label} کنید؟ لطفاً فقط عدد را بنویسید "
        f"(مثال: `10` یا `4.6`)",
        parse_mode="Markdown",
    )


async def handle_gold_grams_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر کاربر در حالت انتظار برای وارد کردن گرم بود، محاسبه را انجام می‌دهد و True برمی‌گرداند."""
    if not context.user_data.get(AWAITING_GOLD_GRAMS):
        return False

    context.user_data[AWAITING_GOLD_GRAMS] = False
    mode = context.user_data.pop(GOLD_CALC_MODE, "buy")
    karat = context.user_data.pop(GOLD_CALC_KARAT, 24)

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
        result = gold_service.calculate_gold_transaction(
            breakdown, karat, grams, is_buying=(mode == "buy")
        )
    except Exception as exc:
        logger.exception("خطا در محاسبهٔ خرید/فروش طلا")
        await thinking_msg.edit_text(f"⚠️ خطا: {exc}")
        return True

    label = "خرید" if result["is_buying"] else "فروش"
    text = (
        f"🧮 *نتیجهٔ محاسبهٔ {label} طلا*\n\n"
        f"عیار: {result['karat']} | مقدار: {result['grams']:g} گرم\n"
        f"قیمت پایه: {result['base_afn']:,.0f} افغانی ({result['base_usd']:,.2f}$)\n"
        f"{result['adjustment_label']}: {result['adjustment_pct']:.1f}٪\n\n"
        f"💰 مبلغ نهایی: *{result['final_afn']:,.0f} افغانی* ({result['final_usd']:,.2f}$)"
    )
    await thinking_msg.edit_text(text, parse_mode="Markdown")
    return True
