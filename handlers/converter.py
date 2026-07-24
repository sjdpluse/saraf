import logging

from telegram import Update
from telegram.ext import ContextTypes

from services import converter_service

logger = logging.getLogger(__name__)

AWAITING_CONVERSION = "awaiting_converter_input"

PROMPT_TEXT = (
    "🔄 *مبدل ارز جهانی*\n\n"
    "به این شکل بنویسید:\n"
    "`مقدار کد_ارز_مبدأ کد_ارز_مقصد`\n\n"
    "مثال: `100 usd pkr` یا `50 eur try`\n"
    "_(می‌توانید از کد هر ارز رسمی یا حتی رمزارز پشتیبانی‌شده استفاده کنید)_"
)


async def converter_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[AWAITING_CONVERSION] = True
    await update.message.reply_text(PROMPT_TEXT, parse_mode="Markdown")


async def handle_converter_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر کاربر در حالت انتظار برای ورودی مبدل بود، تبدیل را انجام می‌دهد و True برمی‌گرداند."""
    if not context.user_data.get(AWAITING_CONVERSION):
        return False

    context.user_data[AWAITING_CONVERSION] = False
    text = update.message.text.strip()
    parts = text.replace(",", ".").split()

    if len(parts) != 3:
        await update.message.reply_text(
            "⚠️ قالب پیام درست نیست. لطفاً به این شکل بنویسید: `100 usd pkr`",
            parse_mode="Markdown",
        )
        return True

    amount_str, from_code, to_code = parts
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ مقدار وارد‌شده باید یک عدد مثبت باشد.")
        return True

    thinking_msg = await update.message.reply_text("در حال تبدیل... ⏳")
    try:
        result = await converter_service.convert(from_code, to_code, amount)
        unit_rate = await converter_service.get_unit_rate(from_code, to_code)
    except Exception as exc:
        await thinking_msg.edit_text(f"⚠️ {exc}")
        return True

    text = (
        f"🔄 *نتیجهٔ تبدیل*\n\n"
        f"{amount:,.2f} {from_code.upper()} = *{result:,.4f} {to_code.upper()}*\n\n"
        f"نرخ واحد: ۱ {from_code.upper()} = {unit_rate:,.6f} {to_code.upper()}"
    )
    await thinking_msg.edit_text(text, parse_mode="Markdown")
    return True
