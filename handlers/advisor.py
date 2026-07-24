import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import TRACKED_CURRENCIES
from services import currency_service, gold_service, ai_advisor

logger = logging.getLogger(__name__)

AWAITING_QUESTION = "awaiting_advisor_question"

PROMPT_TEXT = (
    "🤖 *مشاور هوشمند صراف*\n\n"
    "سوال خود را دربارهٔ طلا، ارز یا زمان مناسب خرید/فروش بنویسید — "
    "پاسخ بر مبنای داده‌های لحظه‌یی بازار و اصول مدیریت ریسک داده می‌شود.\n"

)


async def advisor_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[AWAITING_QUESTION] = True
    await update.message.reply_text(PROMPT_TEXT, parse_mode="Markdown")


async def _build_market_context() -> str:
    parts = []
    try:
        rates, source = await currency_service.get_afn_rates()
        for code, name in TRACKED_CURRENCIES.items():
            if code in rates:
                parts.append(f"{name} ({code.upper()}): {rates[code]:,.2f} افغانی")
    except Exception:
        logger.exception("خطا در دریافت نرخ ارز برای مشاور")

    try:
        price_usd = await gold_service.get_gold_price_usd_per_oz()
        rates, _ = await currency_service.get_afn_rates()
        afn_per_usd = rates.get("usd")
        if afn_per_usd:
            breakdown = gold_service.build_gold_breakdown(price_usd, afn_per_usd)
            parts.append(
                f"طلای عیار ۲۴: {breakdown['karats'][24]['afn_per_gram']:,.0f} "
                f"افغانی به ازای هر گرم (قیمت جهانی: {price_usd:,.2f} دالر/اونس)"
            )
    except Exception:
        logger.exception("خطا در دریافت نرخ طلا برای مشاور")

    return "\n".join(parts) if parts else "داده‌های لحظه‌یی در حال حاضر در دسترس نیست."


async def handle_advisor_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر کاربر در حالت انتظار برای سوال بود، پاسخ می‌دهد و True برمی‌گرداند."""
    if not context.user_data.get(AWAITING_QUESTION):
        return False

    context.user_data[AWAITING_QUESTION] = False
    question = update.message.text

    thinking_msg = await update.message.reply_text("در حال بررسی داده‌های بازار... ⏳")
    market_context = await _build_market_context()
    answer = await ai_advisor.get_financial_advice(question, market_context)

    await thinking_msg.edit_text(answer)
    return True
