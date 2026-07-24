import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import TRACKED_CURRENCIES, CURRENCY_FLAGS
from keyboards import converter_from_keyboard, converter_to_keyboard, converter_amount_keyboard
from services import converter_service

logger = logging.getLogger(__name__)

AWAITING_CUSTOM_AMOUNT = "awaiting_converter_amount"
CONV_FROM = "converter_from_code"
CONV_TO = "converter_to_code"

INTRO_TEXT = "🔄 *مبدل ارز جهانی*\n\nابتدا ارز مبدأ (چیزی که در اختیار دارید) را انتخاب کنید:"


def _label(code: str) -> str:
    name = TRACKED_CURRENCIES.get(code, code.upper())
    flag = CURRENCY_FLAGS.get(code, "")
    return f"{flag} {name}".strip()


async def converter_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(CONV_FROM, None)
    context.user_data.pop(CONV_TO, None)
    context.user_data[AWAITING_CUSTOM_AMOUNT] = False
    await update.message.reply_text(
        INTRO_TEXT, parse_mode="Markdown", reply_markup=converter_from_keyboard()
    )


async def converter_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, code = query.data.split(":", 1)

    if code == "back":
        await query.edit_message_text(
            INTRO_TEXT, parse_mode="Markdown", reply_markup=converter_from_keyboard()
        )
        return

    context.user_data[CONV_FROM] = code
    await query.edit_message_text(
        f"ارز مبدأ: {_label(code)}\n\nحالا ارز مقصد را انتخاب کنید:",
        reply_markup=converter_to_keyboard(code),
    )


async def converter_to_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, from_code, to_code = query.data.split(":", 2)
    context.user_data[CONV_FROM] = from_code
    context.user_data[CONV_TO] = to_code

    await query.edit_message_text(
        f"{_label(from_code)} ➜ {_label(to_code)}\n\nچه مقداری را می‌خواهید تبدیل کنید؟",
        reply_markup=converter_amount_keyboard(),
    )


async def _do_conversion(edit_func, from_code: str, to_code: str, amount: float) -> None:
    try:
        result = await converter_service.convert(from_code, to_code, amount)
        unit_rate = await converter_service.get_unit_rate(from_code, to_code)
    except Exception as exc:
        await edit_func(f"⚠️ {exc}")
        return

    text = (
        f"🔄 *نتیجهٔ تبدیل*\n\n"
        f"{amount:,.2f} {_label(from_code)} = *{result:,.4f} {_label(to_code)}*\n\n"
        f"نرخ واحد: ۱ {_label(from_code)} = {unit_rate:,.6f} {_label(to_code)}"
    )
    await edit_func(text, parse_mode="Markdown")


async def converter_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, amt_str = query.data.split(":", 1)

    from_code = context.user_data.get(CONV_FROM)
    to_code = context.user_data.get(CONV_TO)
    if not from_code or not to_code:
        await query.edit_message_text("⚠️ لطفاً دوباره از منوی مبدل شروع کنید.")
        return

    if amt_str == "custom":
        context.user_data[AWAITING_CUSTOM_AMOUNT] = True
        await query.edit_message_text(
            f"{_label(from_code)} ➜ {_label(to_code)}\n\n"
            "لطفاً مقدار مورد نظر را فقط به‌صورت عدد بنویسید (مثال: `250`)",
            parse_mode="Markdown",
        )
        return

    amount = float(amt_str)
    await query.edit_message_text("در حال تبدیل... ⏳")
    await _do_conversion(query.edit_message_text, from_code, to_code, amount)


async def handle_converter_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر کاربر در حالت انتظار برای واردکردن مقدار دلخواه بود، تبدیل را انجام می‌دهد."""
    if not context.user_data.get(AWAITING_CUSTOM_AMOUNT):
        return False

    from_code = context.user_data.get(CONV_FROM)
    to_code = context.user_data.get(CONV_TO)
    if not from_code or not to_code:
        context.user_data[AWAITING_CUSTOM_AMOUNT] = False
        return False

    text = update.message.text.strip().replace(",", ".")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ لطفاً یک عدد مثبت معتبر بنویسید (مثال: 250)")
        return True

    context.user_data[AWAITING_CUSTOM_AMOUNT] = False
    thinking_msg = await update.message.reply_text("در حال تبدیل... ⏳")
    await _do_conversion(thinking_msg.edit_text, from_code, to_code, amount)
    return True