"""
جریان احراز هویت (KYC) — فقط یک‌بار برای هر کاربر اجرا می‌شود، پیش از اولین سفارش.

مراحل: نام → نام خانوادگی → شمارهٔ تماس → اطلاعات پرداخت → عکس مدرک هویتی → سلفی
پس از تکمیل، پروفایل ثبت می‌شود، درخواست بررسی برای ادمین ارسال می‌شود، و کاربر
دقیقاً به همان نقطه‌یی که قبل از KYC بود (خرید یا فروش) بازمی‌گردد — چیزی از
دست نمی‌رود.
"""
import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

from keyboards import kyc_phone_keyboard
from services import kyc_service

logger = logging.getLogger(__name__)

# --- کلیدهای user_data ---
KYC_FIRST_NAME = "kyc_first_name"
KYC_LAST_NAME = "kyc_last_name"
KYC_PHONE = "kyc_phone"
KYC_PAYMENT_INFO = "kyc_payment_info"
KYC_ID_DOC_BYTES = "kyc_id_doc_bytes"
KYC_ID_DOC_EXT = "kyc_id_doc_ext"
KYC_RESUME_ACTION = "kyc_resume_action"  # "buy" یا "sell" — برای بازگشت بعد از تکمیل

AWAITING_FIRST_NAME = "kyc_awaiting_first_name"
AWAITING_LAST_NAME = "kyc_awaiting_last_name"
AWAITING_PHONE = "kyc_awaiting_phone"
AWAITING_PAYMENT_INFO = "kyc_awaiting_payment_info"
AWAITING_ID_DOC = "kyc_awaiting_id_doc"
AWAITING_SELFIE = "kyc_awaiting_selfie"

_ALL_KEYS = (
    KYC_FIRST_NAME, KYC_LAST_NAME, KYC_PHONE, KYC_PAYMENT_INFO,
    KYC_ID_DOC_BYTES, KYC_ID_DOC_EXT, KYC_RESUME_ACTION,
    AWAITING_FIRST_NAME, AWAITING_LAST_NAME, AWAITING_PHONE,
    AWAITING_PAYMENT_INFO, AWAITING_ID_DOC, AWAITING_SELFIE,
)


def _reset_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in _ALL_KEYS:
        context.user_data.pop(key, None)


async def _download_photo_bytes(context: ContextTypes.DEFAULT_TYPE, file_id: str) -> bytes:
    tg_file = await context.bot.get_file(file_id)
    return bytes(await tg_file.download_as_bytearray())


# ---------------------------------------------------------------------------
# شروع جریان — از handlers/usdt.py صدا زده می‌شود وقتی پروفایل کاربر ناقص است
# ---------------------------------------------------------------------------
async def start_kyc(update: Update, context: ContextTypes.DEFAULT_TYPE, resume_action: str) -> None:
    context.user_data[KYC_RESUME_ACTION] = resume_action
    context.user_data[AWAITING_FIRST_NAME] = True

    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🪪 *تکمیل پروفایل و احراز هویت*\n\n"
            "برای اولین سفارش، لازم است یک‌بار پروفایل خود را تکمیل کنید. این کار فقط "
            "همین یک‌بار انجام می‌شود و در سفارش‌های بعدی دیگر لازم نیست تکرار شود.\n\n"
            "لطفاً *نام* خود را بنویسید:"
        ),
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# نام و نام خانوادگی
# ---------------------------------------------------------------------------
async def handle_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_FIRST_NAME):
        return False
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("⚠️ لطفاً یک نام معتبر بنویسید.")
        return True
    context.user_data[AWAITING_FIRST_NAME] = False
    context.user_data[KYC_FIRST_NAME] = name
    context.user_data[AWAITING_LAST_NAME] = True
    await update.message.reply_text("لطفاً *نام خانوادگی* خود را بنویسید:", parse_mode="Markdown")
    return True


async def handle_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_LAST_NAME):
        return False
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("⚠️ لطفاً یک نام خانوادگی معتبر بنویسید.")
        return True
    context.user_data[AWAITING_LAST_NAME] = False
    context.user_data[KYC_LAST_NAME] = name
    context.user_data[AWAITING_PHONE] = True
    await update.message.reply_text(
        "لطفاً *شمارهٔ تماس* خود را با دکمهٔ زیر ارسال کنید یا تایپ کنید:",
        parse_mode="Markdown",
        reply_markup=kyc_phone_keyboard(),
    )
    return True


# ---------------------------------------------------------------------------
# شمارهٔ تماس
# ---------------------------------------------------------------------------
async def handle_phone_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_PHONE):
        return False
    contact = update.message.contact
    if not contact:
        return False
    context.user_data[AWAITING_PHONE] = False
    context.user_data[KYC_PHONE] = contact.phone_number
    await _ask_payment_info(update, context)
    return True


async def handle_phone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_PHONE):
        return False
    text = update.message.text.strip()
    digits = "".join(ch for ch in text if ch.isdigit() or ch == "+")
    if len(digits) < 7:
        await update.message.reply_text("⚠️ لطفاً یک شمارهٔ تماس معتبر ارسال کنید.")
        return True
    context.user_data[AWAITING_PHONE] = False
    context.user_data[KYC_PHONE] = digits
    await _ask_payment_info(update, context)
    return True


async def _ask_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[AWAITING_PAYMENT_INFO] = True
    await update.message.reply_text(
        "✅ شمارهٔ تماس ثبت شد.\n\n"
        "لطفاً *اطلاعات پرداخت* خود را بنویسید (شمارهٔ حساب بانکی یا شمارهٔ حواله‌جاتی که "
        "معمولاً استفاده می‌کنید):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


# ---------------------------------------------------------------------------
# اطلاعات پرداخت
# ---------------------------------------------------------------------------
async def handle_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_PAYMENT_INFO):
        return False
    text = update.message.text.strip()
    if len(text) < 4:
        await update.message.reply_text("⚠️ لطفاً اطلاعات پرداخت معتبر بنویسید.")
        return True
    context.user_data[AWAITING_PAYMENT_INFO] = False
    context.user_data[KYC_PAYMENT_INFO] = text
    context.user_data[AWAITING_ID_DOC] = True
    await update.message.reply_text(
        "🪪 حالا لطفاً *عکس تذکره یا مدرک هویتی* خود را ارسال کنید (واضح و خوانا):",
        parse_mode="Markdown",
    )
    return True


# ---------------------------------------------------------------------------
# مدرک هویتی
# ---------------------------------------------------------------------------
async def handle_id_document_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_ID_DOC):
        return False
    if not update.message.photo:
        await update.message.reply_text("⚠️ لطفاً یک عکس ارسال کنید.")
        return True

    file_id = update.message.photo[-1].file_id
    try:
        doc_bytes = await _download_photo_bytes(context, file_id)
    except Exception:
        logger.exception("خطا در دانلود عکس مدرک هویتی")
        await update.message.reply_text("⚠️ خطا در دریافت عکس؛ لطفاً دوباره ارسال کنید.")
        return True

    context.user_data[AWAITING_ID_DOC] = False
    context.user_data[KYC_ID_DOC_BYTES] = doc_bytes
    context.user_data[KYC_ID_DOC_EXT] = "jpg"
    context.user_data[AWAITING_SELFIE] = True
    await update.message.reply_text(
        "✅ مدرک هویتی دریافت شد.\n\n"
        "🤳 در آخرین مرحله، لطفاً یک *سلفی واضح از چهرهٔ خودتان* ارسال کنید:",
        parse_mode="Markdown",
    )
    return True


# ---------------------------------------------------------------------------
# سلفی — مرحلهٔ پایانی، ثبت پروفایل و بازگشت به جریان سفارش
# ---------------------------------------------------------------------------
async def handle_selfie_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get(AWAITING_SELFIE):
        return False
    if not update.message.photo:
        await update.message.reply_text("⚠️ لطفاً یک عکس سلفی ارسال کنید.")
        return True

    file_id = update.message.photo[-1].file_id
    try:
        selfie_bytes = await _download_photo_bytes(context, file_id)
    except Exception:
        logger.exception("خطا در دانلود عکس سلفی")
        await update.message.reply_text("⚠️ خطا در دریافت عکس؛ لطفاً دوباره ارسال کنید.")
        return True

    context.user_data[AWAITING_SELFIE] = False
    chat_id = update.effective_chat.id
    thinking = await update.message.reply_text("در حال ثبت پروفایل... ⏳")

    ok = await kyc_service.complete_kyc(
        chat_id=chat_id,
        first_name=context.user_data.get(KYC_FIRST_NAME, ""),
        last_name=context.user_data.get(KYC_LAST_NAME, ""),
        phone=context.user_data.get(KYC_PHONE, ""),
        payment_info=context.user_data.get(KYC_PAYMENT_INFO, ""),
        id_doc_bytes=context.user_data.get(KYC_ID_DOC_BYTES),
        id_doc_ext=context.user_data.get(KYC_ID_DOC_EXT, "jpg"),
        id_doc_content_type="image/jpeg",
        selfie_bytes=selfie_bytes,
        selfie_ext="jpg",
        selfie_content_type="image/jpeg",
    )

    resume_action = context.user_data.get(KYC_RESUME_ACTION)
    _reset_state(context)

    if not ok:
        await thinking.edit_text(
            "⚠️ ثبت پروفایل ناموفق بود. لطفاً کمی بعد دوباره از منوی «🪙 خرید و فروش تتر» شروع کنید."
        )
        return True

    await thinking.edit_text(
        "✅ پروفایل شما ثبت شد و برای بررسی نزد تیم ما ارسال شد.\n"
        "می‌توانید همین الان سفارش خود را ادامه دهید — بعد از تایید هویت، این مرحله "
        "دیگر برای سفارش‌های بعدی تکرار نمی‌شود."
    )

    # بازگشت دقیق به همان جایی که قبل از KYC بود (خرید یا فروش)
    from handlers import usdt as usdt_handlers

    if resume_action in ("buy", "sell"):
        await usdt_handlers.resume_after_kyc(update, context, resume_action)
    return True
