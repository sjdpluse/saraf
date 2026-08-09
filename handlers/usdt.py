import logging
import time

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from config import (
    IN_PERSON_ADDRESS,
    IN_PERSON_PHONE,
    BANK_NAME,
    BANK_ACCOUNT_HOLDER,
    BANK_ACCOUNT_NUMBER,
    USDT_MIN_AMOUNT,
    USDT_MAX_AMOUNT,
    USDT_QUOTE_VALIDITY_MINUTES,
    USDT_DEPOSIT_WALLETS,
)
from keyboards import (
    usdt_menu_keyboard,
    usdt_continue_keyboard,
    usdt_payment_method_keyboard,
    usdt_in_person_paid_keyboard,
    usdt_network_keyboard,
    usdt_exchange_keyboard,
    usdt_buy_exchange_keyboard,
    usdt_phone_keyboard,
)
from services import usdt_service, usdt_order_service
from services import supabase_service as db

logger = logging.getLogger(__name__)

# --- کلیدهای user_data ---
AMOUNT = "usdt_amount"
QUOTE = "usdt_quote"
QUOTE_TIME = "usdt_quote_time"
PAYMENT_METHOD = "usdt_payment_method"
NETWORK = "usdt_network"
EXCHANGE = "usdt_exchange"
WALLET_ADDRESS = "usdt_wallet_address"
BANK_INFO = "usdt_bank_info"
TX_PROOF = "usdt_tx_proof"
RECEIPT_FILE_ID = "usdt_receipt_file_id"
PHONE = "usdt_phone"

AWAITING_AMOUNT = "usdt_awaiting_amount"
AWAITING_WALLET = "usdt_awaiting_wallet"
AWAITING_EXCHANGE_CUSTOM = "usdt_awaiting_exchange_custom"  # مقدار: "buy" یا "sell" یا None
AWAITING_NETWORK_CUSTOM = "usdt_awaiting_network_custom"
AWAITING_TX_PROOF = "usdt_awaiting_tx_proof"
AWAITING_RECEIPT = "usdt_awaiting_receipt"
AWAITING_BANK_INFO = "usdt_awaiting_bank_info"
AWAITING_PHONE = "usdt_awaiting_phone"

# مرحله‌یی که باید بعد از دریافت شمارهٔ تماس نهایی شود: "buy" یا "sell"
PENDING_FINALIZE = "usdt_pending_finalize"
# یادداشت کمکی برای مرحلهٔ نهایی‌سازی فروش (روش دریافت پول: حضوری/آنلاین)
PENDING_FINALIZE_NOTE = "usdt_pending_finalize_note"

_ALL_KEYS = (
    AMOUNT, QUOTE, QUOTE_TIME, PAYMENT_METHOD, NETWORK, EXCHANGE,
    WALLET_ADDRESS, BANK_INFO, TX_PROOF, RECEIPT_FILE_ID, PHONE,
    AWAITING_AMOUNT, AWAITING_WALLET, AWAITING_EXCHANGE_CUSTOM,
    AWAITING_NETWORK_CUSTOM, AWAITING_TX_PROOF, AWAITING_RECEIPT,
    AWAITING_BANK_INFO, AWAITING_PHONE, PENDING_FINALIZE, PENDING_FINALIZE_NOTE,
)


def _reset_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in _ALL_KEYS:
        context.user_data.pop(key, None)


def _quote_expired(context: ContextTypes.DEFAULT_TYPE) -> bool:
    ts = context.user_data.get(QUOTE_TIME)
    if not ts:
        return True
    return (time.time() - ts) > USDT_QUOTE_VALIDITY_MINUTES * 60


# ---------------------------------------------------------------------------
# ورودی منو
# ---------------------------------------------------------------------------
async def usdt_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _reset_state(context)
    await update.message.reply_text(
        "🪙 *خرید و فروش تتر (USDT)*\n\n"
        f"حداقل مقدار معامله: {USDT_MIN_AMOUNT:g} USDT | حداکثر: {USDT_MAX_AMOUNT:g} USDT\n\n"
        "می‌خواهید تتر بخرید یا بفروشید؟",
        parse_mode="Markdown",
        reply_markup=usdt_menu_keyboard(),
    )


async def usdt_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, action = query.data.split(":", 1)
    _reset_state(context)
    context.user_data[AWAITING_AMOUNT] = action

    verb = "خرید" if action == "buy" else "فروش"
    await query.edit_message_text(
        f"چند USDT می‌خواهید {verb} کنید؟\n\n"
        f"(بین {USDT_MIN_AMOUNT:g} تا {USDT_MAX_AMOUNT:g} — فقط عدد بنویسید، مثال: `50`)",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# دریافت مقدار و نمایش نرخ
# ---------------------------------------------------------------------------
async def handle_usdt_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    action = context.user_data.get(AWAITING_AMOUNT)
    if not action:
        return False

    text = update.message.text.strip().replace(",", ".")
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("⚠️ لطفاً یک عدد معتبر بنویسید (مثال: 50)")
        return True

    try:
        if action == "buy":
            quote = await usdt_service.get_buy_quote(amount)
        else:
            quote = await usdt_service.get_sell_quote(amount)
    except usdt_service.UsdtAmountError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
        return True
    except Exception as exc:
        logger.exception("خطا در محاسبهٔ نرخ تتر")
        await update.message.reply_text(f"⚠️ خطا در دریافت نرخ: {exc}")
        return True

    context.user_data[AWAITING_AMOUNT] = None
    context.user_data[AMOUNT] = amount
    context.user_data[QUOTE] = quote
    context.user_data[QUOTE_TIME] = time.time()

    if action == "buy":
        text_out = (
            f"🟢 *خرید {amount:g} USDT*\n\n"
            f"نرخ دالر (صرافی محلی): {quote['usd_rate']:,.2f}\n"
            f"مبلغ پایه: {quote['base_afn']:,.0f} افغانی\n"
            f"کارمزد ({quote['fee_percent']}٪): {quote['fee_afn']:,.0f} افغانی\n\n"
            f"💰 مبلغ نهایی قابل پرداخت: *{quote['total_afn']:,.0f} افغانی*\n\n"
            f"_این نرخ برای {USDT_QUOTE_VALIDITY_MINUTES} دقیقه معتبر است._"
        )
    else:
        text_out = (
            f"🔴 *فروش {amount:g} USDT*\n\n"
            f"{amount:g} تتر شما به نرخ روز، *{quote['usd_rate']:,.2f}* دالر برای هر واحد "
            f"و مجموعاً *{quote['total_afn']:,.0f} افغانی* می‌شود.\n\n"
            f"_این نرخ برای {USDT_QUOTE_VALIDITY_MINUTES} دقیقه معتبر است._"
        )

    await update.message.reply_text(
        text_out, parse_mode="Markdown", reply_markup=usdt_continue_keyboard(action)
    )
    return True


async def usdt_continue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, action = query.data.split(":", 1)

    if action == "buy":
        await query.edit_message_text(
            "روش پرداخت خود را انتخاب کنید:",
            reply_markup=usdt_payment_method_keyboard("buy"),
        )
    else:
        await query.edit_message_text(
            "معاملهٔ خود را از کدام صرافی انجام می‌دهید؟",
            reply_markup=usdt_exchange_keyboard(),
        )


# ---------------------------------------------------------------------------
# خرید — روش پرداخت
# ---------------------------------------------------------------------------
async def usdt_pay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, action, method = query.data.split(":", 2)
    context.user_data[PAYMENT_METHOD] = method

    quote = context.user_data.get(QUOTE)
    if not quote:
        await query.edit_message_text("⚠️ لطفاً دوباره از منوی تتر شروع کنید.")
        return

    if action == "buy":
        if method == "in_person":
            await query.edit_message_text(
                "🏢 *پرداخت حضوری*\n\n"
                f"لطفاً مبلغ *{quote['total_afn']:,.0f} افغانی* را به نمایندهٔ حضوری صراف "
                "به آدرس زیر پرداخت کنید:\n\n"
                f"📍 {IN_PERSON_ADDRESS}\n"
                f"📞 {IN_PERSON_PHONE}\n\n"
                "پس از پرداخت، دکمهٔ زیر را بزنید:",
                parse_mode="Markdown",
                reply_markup=usdt_in_person_paid_keyboard("buy"),
            )
        else:
            context.user_data[AWAITING_RECEIPT] = True
            await query.edit_message_text(
                "🏦 *پرداخت آنلاین (بانکی)*\n\n"
                f"لطفاً مبلغ *{quote['total_afn']:,.0f} افغانی* را به حساب بانکی زیر واریز کنید:\n\n"
                f"🏦 بانک: {BANK_NAME}\n"
                f"👤 صاحب حساب: {BANK_ACCOUNT_HOLDER}\n"
                f"🔢 شماره حساب: `{BANK_ACCOUNT_NUMBER}`\n\n"
                "پس از واریز، لطفاً *عکس رسید بانکی* را همینجا ارسال کنید.",
                parse_mode="Markdown",
            )
        return

    # action == "sell" -> این مرحله دربارهٔ نحوهٔ دریافت مبلغ فروش است
    if method == "in_person":
        await query.edit_message_text(
            "🏢 *دریافت حضوری*\n\nبرای تکمیل سفارش، فقط یک قدم باقی مانده...",
            parse_mode="Markdown",
        )
        await _request_phone(context, query.message.chat_id, pending="sell", note="حضوری")
    else:
        context.user_data[AWAITING_BANK_INFO] = True
        await query.edit_message_text(
            "🏦 *دریافت آنلاین*\n\n"
            "لطفاً نام صاحب حساب و شمارهٔ حساب بانکی خود را برای واریز مبلغ ارسال کنید\n"
            "(مثال: `احمد احمدی — 0123456789 — بانک ...`)",
            parse_mode="Markdown",
        )


async def usdt_paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, action = query.data.split(":", 1)
    if action != "buy":
        return
    await query.edit_message_text(
        "بسیار خوب ✅\n\nتتر خود را در کدام صرافی یا کیف پول می‌خواهید دریافت کنید؟",
        reply_markup=usdt_buy_exchange_keyboard(),
    )


async def handle_usdt_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_RECEIPT):
        return False
    context.user_data[AWAITING_RECEIPT] = False
    context.user_data[RECEIPT_FILE_ID] = update.message.photo[-1].file_id
    await update.message.reply_text(
        "✅ رسید پرداخت شما دریافت شد.\n\nتتر خود را در کدام صرافی یا کیف پول می‌خواهید دریافت کنید؟",
        reply_markup=usdt_buy_exchange_keyboard(),
    )
    return True


# ---------------------------------------------------------------------------
# خرید — انتخاب صرافی/کیف‌پول مقصد
# ---------------------------------------------------------------------------
async def usdt_buy_exch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, exch = query.data.split(":", 1)

    if exch == "other":
        context.user_data[AWAITING_EXCHANGE_CUSTOM] = "buy"
        await query.edit_message_text("لطفاً نام صرافی یا نوع کیف پول خود را بنویسید:")
        return

    context.user_data[EXCHANGE] = exch
    await query.edit_message_text(
        f"مقصد: *{exch}*\n\nحالا شبکهٔ مورد نظر برای دریافت تتر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=usdt_network_keyboard("buy"),
    )


# ---------------------------------------------------------------------------
# فروش — انتخاب صرافی
# ---------------------------------------------------------------------------
async def usdt_exch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, exch = query.data.split(":", 1)

    if exch == "other":
        context.user_data[AWAITING_EXCHANGE_CUSTOM] = "sell"
        await query.edit_message_text("لطفاً نام صرافی مورد نظر خود را بنویسید:")
        return

    context.user_data[EXCHANGE] = exch
    await query.edit_message_text(
        f"صرافی: *{exch}*\n\nحالا شبکهٔ مورد نظر برای ارسال تتر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=usdt_network_keyboard("sell"),
    )


async def handle_usdt_exchange_custom_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """مشترک بین خرید و فروش — تشخیص مسیر از روی مقدار ذخیره‌شده در AWAITING_EXCHANGE_CUSTOM."""
    action = context.user_data.get(AWAITING_EXCHANGE_CUSTOM)
    if not action:
        return False
    context.user_data[AWAITING_EXCHANGE_CUSTOM] = None
    exch = update.message.text.strip()
    context.user_data[EXCHANGE] = exch

    label = "دریافت تتر" if action == "buy" else "ارسال تتر"
    await update.message.reply_text(
        f"مقصد: *{exch}*\n\nحالا شبکهٔ مورد نظر برای {label} را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=usdt_network_keyboard(action),
    )
    return True


# ---------------------------------------------------------------------------
# انتخاب شبکه (مشترک بین خرید و فروش)
# ---------------------------------------------------------------------------
async def _after_network_selected(send_func, context: ContextTypes.DEFAULT_TYPE, action: str, network: str) -> None:
    context.user_data[NETWORK] = network

    if action == "buy":
        context.user_data[AWAITING_WALLET] = True
        await send_func(
            f"شبکهٔ انتخابی: *{network}*\n\n"
            "لطفاً آدرس ولت (کیف پول) خودتان برای دریافت تتر در همین شبکه را ارسال کنید.",
            parse_mode="Markdown",
        )
        return

    # action == "sell"
    wallet = USDT_DEPOSIT_WALLETS.get(network.upper())
    if not wallet:
        supported = "، ".join(USDT_DEPOSIT_WALLETS.keys())
        await send_func(
            f"⚠️ در حال حاضر فقط شبکهٔ {supported} برای دریافت تتر پشتیبانی می‌شود.\n\n"
            "لطفاً یکی از شبکه‌های زیر را انتخاب کنید:",
            reply_markup=usdt_network_keyboard("sell"),
        )
        return

    context.user_data[AWAITING_TX_PROOF] = True
    amount = context.user_data.get(AMOUNT, 0)
    await send_func(
        f"لطفاً مقدار *{amount:g} USDT* را به آدرس زیر در شبکهٔ *{network}* ارسال کنید:\n\n"
        f"`{wallet}`\n\n"
        "⚠️ لطفاً پیش از ارسال، آدرس و شبکه را با دقت بررسی کنید؛ ارسال در شبکهٔ اشتباه "
        "ممکن است باعث از دست رفتن دارایی شود.\n\n"
        "پس از انتقال، لطفاً *کد تراکنش (TxID)* یا *عکس رسید تراکنش* را ارسال کنید.",
        parse_mode="Markdown",
    )


async def usdt_network_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, action, network = query.data.split(":", 2)

    if network == "other":
        context.user_data[AWAITING_NETWORK_CUSTOM] = action
        await query.edit_message_text("لطفاً نام شبکهٔ مورد نظر خود را بنویسید (مثال: Polygon):")
        return

    await _after_network_selected(query.edit_message_text, context, action, network)


async def handle_usdt_network_custom_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    action = context.user_data.get(AWAITING_NETWORK_CUSTOM)
    if not action:
        return False
    context.user_data[AWAITING_NETWORK_CUSTOM] = None
    network = update.message.text.strip()
    await _after_network_selected(update.message.reply_text, context, action, network)
    return True


# ---------------------------------------------------------------------------
# خرید — دریافت آدرس ولت
# ---------------------------------------------------------------------------
async def handle_usdt_wallet_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_WALLET):
        return False
    context.user_data[AWAITING_WALLET] = False
    context.user_data[WALLET_ADDRESS] = update.message.text.strip()

    if _quote_expired(context):
        await update.message.reply_text(
            "⚠️ نرخ نمایش‌داده‌شده منقضی شده است. لطفاً دوباره از منوی «🪙 خرید و فروش تتر» شروع کنید."
        )
        _reset_state(context)
        return True

    await _request_phone(context, update.effective_chat.id, pending="buy")
    return True


async def _finalize_buy_order(send_func, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user) -> None:
    quote = context.user_data.get(QUOTE)
    result = await usdt_order_service.create_buy_order(
        chat_id=chat_id,
        username=user.username,
        full_name=user.full_name,
        phone=context.user_data.get(PHONE),
        amount=context.user_data.get(AMOUNT),
        quote=quote,
        payment_method=context.user_data.get(PAYMENT_METHOD),
        exchange_name=context.user_data.get(EXCHANGE),
        network=context.user_data.get(NETWORK),
        wallet_address=context.user_data.get(WALLET_ADDRESS),
        receipt_file_id=context.user_data.get(RECEIPT_FILE_ID),
        source="bot",
    )
    await send_func(result["message"], parse_mode="Markdown")
    _reset_state(context)


# ---------------------------------------------------------------------------
# فروش — دریافت اثبات تراکنش
# ---------------------------------------------------------------------------
async def _ask_sell_receive_method(send_func) -> None:
    await send_func(
        "✅ رسید تراکنش دریافت شد.\n\nمی‌خواهید مبلغ فروش را چگونه دریافت کنید؟",
        reply_markup=usdt_payment_method_keyboard("sell"),
    )


async def handle_usdt_tx_proof_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_TX_PROOF):
        return False
    context.user_data[AWAITING_TX_PROOF] = False
    context.user_data[TX_PROOF] = update.message.text.strip()
    await _ask_sell_receive_method(update.message.reply_text)
    return True


async def handle_usdt_tx_proof_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_TX_PROOF):
        return False
    context.user_data[AWAITING_TX_PROOF] = False
    context.user_data[TX_PROOF] = update.message.photo[-1].file_id
    await _ask_sell_receive_method(update.message.reply_text)
    return True


async def handle_usdt_bank_info_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_BANK_INFO):
        return False
    context.user_data[AWAITING_BANK_INFO] = False
    context.user_data[BANK_INFO] = update.message.text.strip()

    if _quote_expired(context):
        await update.message.reply_text(
            "⚠️ نرخ نمایش‌داده‌شده منقضی شده است. لطفاً دوباره از منوی «🪙 خرید و فروش تتر» شروع کنید."
        )
        _reset_state(context)
        return True

    await _request_phone(context, update.effective_chat.id, pending="sell", note="آنلاین (بانکی)")
    return True


async def _finalize_sell_order(send_func, context: ContextTypes.DEFAULT_TYPE, chat_id: int, user, payment_note: str) -> None:
    quote = context.user_data.get(QUOTE)
    result = await usdt_order_service.create_sell_order(
        chat_id=chat_id,
        username=user.username,
        full_name=user.full_name,
        phone=context.user_data.get(PHONE),
        amount=context.user_data.get(AMOUNT),
        quote=quote,
        exchange_name=context.user_data.get(EXCHANGE),
        network=context.user_data.get(NETWORK),
        tx_proof=context.user_data.get(TX_PROOF),
        receive_method=context.user_data.get(PAYMENT_METHOD),
        bank_info=context.user_data.get(BANK_INFO),
        source="bot",
    )
    await send_func(result["message"], parse_mode="Markdown")
    _reset_state(context)


# ---------------------------------------------------------------------------
# دریافت شمارهٔ تماس (مرحلهٔ مشترک، درست پیش از ثبت نهایی هر سفارش)
# ---------------------------------------------------------------------------
async def _request_phone(context: ContextTypes.DEFAULT_TYPE, chat_id: int, pending: str, note: str | None = None) -> None:
    context.user_data[AWAITING_PHONE] = True
    context.user_data[PENDING_FINALIZE] = pending
    context.user_data[PENDING_FINALIZE_NOTE] = note
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "📞 برای تکمیل و اعتبارسنجی سفارش، لطفاً شمارهٔ تماس خود را با دکمهٔ زیر به اشتراک "
            "بگذارید یا آن را تایپ کنید (تیم ما در صورت نیاز برای هماهنگی بیشتر با شما تماس می‌گیرد):"
        ),
        reply_markup=usdt_phone_keyboard(),
    )


async def handle_usdt_phone_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_PHONE):
        return False
    contact = update.message.contact
    if not contact:
        return False
    context.user_data[AWAITING_PHONE] = False
    context.user_data[PHONE] = contact.phone_number
    await _complete_pending_finalize(update, context)
    return True


async def handle_usdt_phone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_PHONE):
        return False
    text = update.message.text.strip()
    digits = "".join(ch for ch in text if ch.isdigit() or ch == "+")
    if len(digits) < 7:
        await update.message.reply_text(
            "⚠️ لطفاً یک شمارهٔ تماس معتبر ارسال کنید یا از دکمهٔ اشتراک‌گذاری استفاده کنید."
        )
        return True
    context.user_data[AWAITING_PHONE] = False
    context.user_data[PHONE] = digits
    await _complete_pending_finalize(update, context)
    return True


async def _complete_pending_finalize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pending = context.user_data.get(PENDING_FINALIZE)
    note = context.user_data.get(PENDING_FINALIZE_NOTE)

    if _quote_expired(context):
        await update.message.reply_text(
            "⚠️ نرخ نمایش‌داده‌شده منقضی شده است. لطفاً دوباره از منوی «🪙 خرید و فروش تتر» شروع کنید.",
            reply_markup=ReplyKeyboardRemove(),
        )
        _reset_state(context)
        return

    await update.message.reply_text("✅ شمارهٔ تماس شما ثبت شد.", reply_markup=ReplyKeyboardRemove())

    if pending == "buy":
        await _finalize_buy_order(update.message.reply_text, context, update.effective_chat.id, update.effective_user)
    elif pending == "sell":
        await _finalize_sell_order(
            update.message.reply_text, context, update.effective_chat.id, update.effective_user, note or "-"
        )
    else:
        logger.warning("مرحلهٔ نهایی‌سازی ناشناخته: %s", pending)
        _reset_state(context)


# ---------------------------------------------------------------------------
# امتیازدهی مشتری — بعد از تکمیل سفارش، ربات مدیریت این دکمه‌ها را برای مشتری
# می‌فرستد؛ اما چون از طریق همان BOT_TOKEN ارسال شده، کال‌بک آن به ربات اصلی
# (همین‌جا) می‌رسد.
# ---------------------------------------------------------------------------
async def usdt_rate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, order_id_str, stars_str = query.data.split(":", 2)
    try:
        order_id = int(order_id_str)
        stars = int(stars_str)
    except ValueError:
        await query.answer("درخواست نامعتبر.", show_alert=True)
        return

    chat_id = update.effective_chat.id
    ok = db.set_usdt_order_rating(order_id, chat_id, stars)
    if not ok:
        await query.answer("ثبت امتیاز ناموفق بود یا قبلاً امتیاز داده شده.", show_alert=True)
        return

    await query.answer("متشکریم از بازخورد شما! 🙏")
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"{'⭐' * stars}\n\nممنون از وقتی که گذاشتید. نظر شما برای ما مهم است.")
