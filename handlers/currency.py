import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import TRACKED_CURRENCIES, CURRENCY_FLAGS, THOUSAND_UNIT_CURRENCIES
from keyboards import currency_list_keyboard, currency_quote_keyboard
from persian_date import get_afghan_datetime_str
from services import rate_engine

logger = logging.getLogger(__name__)

DIVIDER = "━━━━━━━━━━"

AWAITING_CURRENCY_CALC = "awaiting_currency_calc_amount"
CURRENCY_CALC_CODE = "currency_calc_code"


def _unit_amount(code: str) -> int:
    return 1000 if code in THOUSAND_UNIT_CURRENCIES else 1


def _scale(code: str, value: float) -> float:
    return value * _unit_amount(code)


def _format_quote_block(code: str, name: str, quote: dict) -> str:
    flag = CURRENCY_FLAGS.get(code, "")
    amount = _unit_amount(code)
    date_str = get_afghan_datetime_str()

    lines = [
        f"{flag} *({amount}) {name} — نرخ ارزها ربات صراف*",
        date_str,
        "",
    ]

    # ۱) نرخ سرای شهزاده
    local = quote.get("local")
    if local:
        lines.append(f"🏛 *نرخ {local['market_label']}*")
        lines.append(
            f"خرید: {_scale(code, local['buy']):,.2f}   |   "
            f"فروش: {_scale(code, local['sell']):,.2f}"
        )
        lines.append(DIVIDER)
        lines.append("")

    # ۲) نرخ خرید/فروش صرافی‌های محلی (نرخ Saraf)
    saraf = quote["saraf_quote"]
    lines.append("💱 *نرخ صرافی‌های محلی*")
    lines.append(
        f"خرید: {_scale(code, saraf['buy']):,.2f}   |   "
        f"فروش: {_scale(code, saraf['sell']):,.2f}"
    )
    lines.append(DIVIDER)
    lines.append("")

    # ۳) نرخ بازار آزاد جهانی
    if quote.get("reference_rate"):
        lines.append("🌍 *نرخ بازار آزاد جهانی*")
        lines.append(f"{_scale(code, quote['reference_rate']):,.2f} افغانی")

    return "\n".join(lines)


def _format_quote_block_for_all(code: str, name: str, quote: dict) -> str:
    """فرمت هر ارز برای پیام «نمایش همهٔ نرخ‌ها» — بدون تاریخ تکراری،
    خط جداکننده فقط در ابتدا و انتهای بلوکِ هر ارز قرار می‌گیرد."""
    flag = CURRENCY_FLAGS.get(code, "")
    amount = _unit_amount(code)

    lines = [
        DIVIDER,
        f"{flag} *({amount}) {name}*",
        "",
    ]

    # ۱) نرخ سرای شهزاده
    local = quote.get("local")
    if local:
        lines.append(f"🏛 *نرخ {local['market_label']}*")
        lines.append(
            f"خرید: {_scale(code, local['buy']):,.2f}   |   "
            f"فروش: {_scale(code, local['sell']):,.2f}"
        )
        lines.append("")

    # ۲) نرخ خرید/فروش صرافی‌های محلی (نرخ Saraf)
    saraf = quote["saraf_quote"]
    lines.append("💱 *نرخ صرافی‌های محلی*")
    lines.append(
        f"خرید: {_scale(code, saraf['buy']):,.2f}   |   "
        f"فروش: {_scale(code, saraf['sell']):,.2f}"
    )
    lines.append("")

    # ۳) نرخ بازار آزاد جهانی
    if quote.get("reference_rate"):
        lines.append("🌍 *نرخ بازار آزاد جهانی*")
        lines.append(f"{_scale(code, quote['reference_rate']):,.2f} افغانی")

    lines.append(DIVIDER)

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

    if code == "list":
        await query.edit_message_text(
            "کدام ارز مدنظر شماست؟ یا «نمایش همهٔ نرخ‌ها» را بزنید.",
            reply_markup=currency_list_keyboard(),
        )
        return

    if code == "all":
        await query.edit_message_text("در حال دریافت نرخ‌ها... ⏳")
        quotes = await rate_engine.get_full_quotes(list(TRACKED_CURRENCIES.keys()))
        if not quotes:
            await query.edit_message_text("⚠️ در حال حاضر هیچ نرخی در دسترس نیست.")
            return

        date_str = get_afghan_datetime_str()
        header = f"💵 *(Saraf) نرخ ارزهای خارجی در برابر پول افغانی امروز — صراف*\n{date_str}\n"

        blocks = []
        for c, name in TRACKED_CURRENCIES.items():
            if c in quotes:
                blocks.append(_format_quote_block_for_all(c, name, quotes[c]))

        text = header + "\n" + "\n\n".join(blocks)
        # برای حالت «نمایش همهٔ نرخ‌ها» دیگر کیبورد لیست ارزها نمایش داده نمی‌شود
        reply_markup = None
    else:
        name = TRACKED_CURRENCIES.get(code, code.upper())
        await query.edit_message_text("در حال دریافت نرخ... ⏳")
        try:
            quote = await rate_engine.get_full_quote(code)
        except Exception as exc:
            logger.exception("خطا در دریافت نرخ ارز")
            await query.edit_message_text(f"⚠️ خطا در دریافت نرخ ارز: {exc}")
            return
        text = _format_quote_block(code, name, quote)
        reply_markup = currency_quote_keyboard(code)

    if len(text) > 4000:
        text = text[:3990] + "\n…"

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def currency_calc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """وقتی کاربر دکمهٔ «🧮 صراف» را می‌زند."""
    query = update.callback_query
    await query.answer()
    _, code = query.data.split(":", 1)

    name = TRACKED_CURRENCIES.get(code, code.upper())
    context.user_data[AWAITING_CURRENCY_CALC] = True
    context.user_data[CURRENCY_CALC_CODE] = code

    date_str = get_afghan_datetime_str()

    await query.edit_message_text(
        f"{name} شما به افغانی چند می‌شود؟\n"
        f"{date_str}\n\n"
        f"لطفاً مقدار {name} که می‌خواهید به افغانی تبدیل کنید، را فقط بصورت عدد "
        f"بنویسید. مثلاً (100)"
    )


async def handle_currency_calc_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر کاربر در حالت انتظار برای وارد کردن مقدار محاسبه بود، محاسبه را انجام می‌دهد و True برمی‌گرداند."""
    if not context.user_data.get(AWAITING_CURRENCY_CALC):
        return False

    code = context.user_data.get(CURRENCY_CALC_CODE)
    context.user_data[AWAITING_CURRENCY_CALC] = False

    if not code:
        return False

    text = update.message.text.strip().replace(",", ".")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ لطفاً یک عدد مثبت معتبر بنویسید (مثال: 100)")
        return True

    name = TRACKED_CURRENCIES.get(code, code.upper())
    flag = CURRENCY_FLAGS.get(code, "")
    thinking_msg = await update.message.reply_text("در حال محاسبه... ⏳")

    try:
        quote = await rate_engine.get_full_quote(code)
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ برای محاسبه")
        await thinking_msg.edit_text(f"⚠️ خطا در دریافت نرخ: {exc}")
        return True

    lines = [f"{flag} *نتیجهٔ محاسبه — {amount:,.2f} {name}*", ""]

    local = quote.get("local")
    if local:
        sell_afn = amount * local["buy"]
        buy_afn = amount * local["sell"]
        lines.append(f"🏛 *بر اساس نرخ {local['market_label']}*")
        lines.append(
            f"اگر بفروشید: {sell_afn:,.1f} افغانی\n"
            f"اگر بخرید: {buy_afn:,.1f} افغانی"
        )
        lines.append(DIVIDER)

    saraf = quote["saraf_quote"]
    sell_afn = amount * saraf["buy"]
    buy_afn = amount * saraf["sell"]
    lines.append("💱 *بر اساس نرخ صرافی‌های محلی*")
    lines.append(
        f"اگر بفروشید: {sell_afn:,.1f} افغانی\n"
        f"اگر بخرید: {buy_afn:,.1f} افغانی"
    )

    await thinking_msg.edit_text("\n".join(lines), parse_mode="Markdown")
    return True