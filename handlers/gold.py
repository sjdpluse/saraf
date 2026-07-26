import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import GOLD_KARATS
from keyboards import gold_karat_keyboard, gold_calc_mode_keyboard, gold_calc_karat_keyboard
from services import gold_service, gold_rate_engine

logger = logging.getLogger(__name__)

AWAITING_GOLD_GRAMS = "awaiting_gold_grams"
GOLD_CALC_MODE = "gold_calc_mode"
GOLD_CALC_KARAT = "gold_calc_karat"


def _format_quote_block(quote: dict) -> str:
    karat = quote["karat"]
    saraf = quote["saraf_quote"]
    lines = [
        f"▫️ *عیار {karat}*",
        f"   نرخ Saraf — خرید: *{saraf['buy']:,.0f}* | فروش: *{saraf['sell']:,.0f}* افغانی/گرم",
    ]

    melted_kabul = quote["melted"].get("kabul")
    melted_herat = quote["melted"].get("herat")
    if melted_kabul:
        lines.append(
            f"   طلای آبشدهٔ کابل (واقعی) — خرید: {melted_kabul['buy']:,.0f} | "
            f"فروش: {melted_kabul['sell']:,.0f}"
        )
    if melted_herat:
        lines.append(
            f"   طلای آبشدهٔ هرات (واقعی) — خرید: {melted_herat['buy']:,.0f} | "
            f"فروش: {melted_herat['sell']:,.0f}"
        )
    if quote.get("kabul_official"):
        lines.append(f"   نرخ رسمی اتحادیهٔ زرگران کابل: {quote['kabul_official']:,.0f}")
    if quote.get("reference"):
        lines.append(f"   نرخ مرجع جهانی: {quote['reference']['afn_per_gram']:,.0f}")

    return "\n".join(lines)


async def gold_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "عیار مدنظر خود را انتخاب کنید، «نمایش همهٔ عیارها» را بزنید، یا از "
        "ماشین‌حساب خرید/فروش استفاده کنید.",
        reply_markup=gold_karat_keyboard(),
    )


async def gold_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, karat = query.data.split(":", 1)

    if karat == "calc":
        await query.edit_message_text(
            "می‌خواهید طلا بخرید یا بفروشید؟", reply_markup=gold_calc_mode_keyboard()
        )
        return

    await query.edit_message_text("در حال دریافت نرخ طلا... ⏳")

    if karat == "all":
        blocks = ["🥇 *نرخ‌های Saraf — طلا (خرید و فروش هر گرم)*\n"]
        any_success = False
        for k in GOLD_KARATS:
            try:
                quote = await gold_rate_engine.get_full_gold_quote(k)
                blocks.append(_format_quote_block(quote))
                any_success = True
            except Exception:
                logger.exception("خطا در دریافت نرخ طلا برای عیار %s", k)
        if not any_success:
            await query.edit_message_text("⚠️ در حال حاضر هیچ نرخ طلایی در دسترس نیست.")
            return

        coins = await gold_rate_engine.get_herat_coins()
        if coins:
            blocks.append("🪙 *سکه‌های کارتی هرات (خرید/فروش واقعی)*")
            coin_names = {"ربع": "ربع کارتی", "نیم": "نیم کارتی", "کامل": "کامل کارتی"}
            for key, vals in coins.items():
                label = coin_names.get(key, key)
                blocks.append(f"▫️ {label} — خرید: {vals['buy']:,.0f} | فروش: {vals['sell']:,.0f}")

        text = "\n\n".join(blocks)
    else:
        k = int(karat)
        try:
            quote = await gold_rate_engine.get_full_gold_quote(k)
        except Exception as exc:
            logger.exception("خطا در دریافت نرخ طلا")
            await query.edit_message_text(f"⚠️ خطا در دریافت نرخ طلا: {exc}")
            return
        text = f"🥇 *طلای عیار {k}*\n\n" + _format_quote_block(quote)

    if len(text) > 4000:
        text = text[:3990] + "\n…"

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
        quote = await gold_rate_engine.get_full_gold_quote(karat)
        saraf = quote["saraf_quote"]
        result = gold_service.calculate_gold_transaction(
            per_gram_buy_afn=saraf["buy"],
            per_gram_sell_afn=saraf["sell"],
            karat=karat,
            grams=grams,
            is_buying=(mode == "buy"),
            basis=saraf["basis"],
        )
    except Exception as exc:
        logger.exception("خطا در محاسبهٔ خرید/فروش طلا")
        await thinking_msg.edit_text(f"⚠️ خطا: {exc}")
        return True

    label = "خرید" if result["is_buying"] else "فروش"
    basis_labels = {
        "melted_kabul": "طلای آبشدهٔ کابل (واقعی)",
        "kabul_official": "نرخ رسمی اتحادیهٔ زرگران کابل",
        "melted_herat": "طلای آبشدهٔ هرات (واقعی)",
        "reference": "نرخ مرجع جهانی (نبود دادهٔ محلی)",
    }
    text = (
        f"🧮 *نتیجهٔ محاسبهٔ {label} طلا*\n\n"
        f"عیار: {result['karat']} | مقدار: {result['grams']:g} گرم\n"
        f"نرخ هر گرم ({label}): {result['per_gram_afn']:,.0f} افغانی\n"
        f"مبنای محاسبه: {basis_labels.get(result['basis'], result['basis'])}\n\n"
        f"💰 مبلغ نهایی: *{result['final_afn']:,.0f} افغانی*"
    )
    await thinking_msg.edit_text(text, parse_mode="Markdown")
    return True
