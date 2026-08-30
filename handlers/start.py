import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import (
    SUPPORT_TELEGRAM_USERNAME,
    USDT_IDENTITY_VERIFICATION_THRESHOLD_USD,
    USDT_MAX_AMOUNT,
    USDT_MIN_AMOUNT,
    ADMIN_CHAT_IDS,
)
from keyboards import main_menu, usdt_menu_keyboard
from services import supabase_service as db

logger = logging.getLogger(__name__)


def _escape_markdown_legacy(value: str) -> str:
    """Escape user-controlled text for Telegram's legacy Markdown parser."""
    text = str(value or "")
    for char in ("\\", "_", "*", "`", "["):
        text = text.replace(char, f"\\{char}")
    return text


WELCOME_TEXT = (
    "سلام {name} 👋\n\n"
    "به *صراف* خوش آمدید.\n"
    "پلتفرم هوشمند بازار و خدمات مالی افغانستان.\n\n"
    "💵 نرخ ارزها  |  🥇 طلا  |  🥈 نقره  |  🪙 رمزارزها\n"
    "📊 مقایسه با گذشته  |  🔄 مبدل ارز  |  🪙 خرید و فروش USDT\n\n"
    "از منوی زیر گزینهٔ مورد نظر خود را انتخاب کنید. 👇"
)

ABOUT_HOME_TEXT = (
    "🏦 *صراف*\n\n"
    "*یک تجربهٔ مالی هوشمند، ساده و ساخته‌شده برای افغانستان*\n\n"
    "صراف برای این ساخته شده است که دسترسی به معلومات بازار، ابزارهای محاسبه و خدمات "
    "خرید و فروش تتر را برای کاربران افغانستان ساده‌تر، شفاف‌تر و قابل پیگیری‌تر کند.\n\n"
    "تمرکز صراف روی تجربهٔ سریع، معلومات روشن و روند قابل اعتماد است؛ از بررسی نرخ و "
    "محاسبه گرفته تا ثبت و پیگیری سفارش.\n\n"
    "*نرخ را ببین. محاسبه کن. با آگاهی تصمیم بگیر.*\n\n"
    "برای آشنایی بیشتر، یکی از گزینه‌های زیر را انتخاب کنید. 👇"
)

ABOUT_MARKETS_TEXT = (
    "📊 *بازارها و نرخ‌ها*\n\n"
    "صراف معلومات مورد نیاز بازار را در یک محیط ساده و یک‌دست در اختیار کاربر قرار می‌دهد.\n\n"
    "💵 *ارزهای خارجی*\n"
    "• نمایش نرخ خرید و فروش ارزهای پرکاربرد در برابر افغانی\n\n"
    "🥇 *طلا*\n"
    "• نمایش نرخ عیارهای پرکاربرد طلا به گرم و مثقال\n\n"
    "🥈 *نقره*\n"
    "• نمایش نرخ نقره به واحدهای کاربردی بازار\n\n"
    "🪙 *رمزارزها*\n"
    "• نمایش قیمت رمزارزهای پرکاربرد به دالر و معادل افغانی"
)

ABOUT_TOOLS_TEXT = (
    "🧮 *ابزارهای مالی صراف*\n\n"
    "📊 *مقایسه با گذشته*\n"
    "• مقایسهٔ تغییرات نرخ در بازه‌های زمانی مختلف\n\n"
    "🔄 *مبدل ارز*\n"
    "• تبدیل مستقیم میان ارزهای پشتیبانی‌شده\n\n"
    "💵 *ماشین‌حساب ارز*\n"
    "• محاسبهٔ مبلغ بر اساس نرخ خرید و فروش\n\n"
    "🥇 *ماشین‌حساب طلا*\n"
    "• محاسبهٔ خرید و فروش بر اساس عیار و وزن\n\n"
    "🥈 *ماشین‌حساب نقره*\n"
    "• محاسبهٔ مبلغ نقره بر اساس وزن و نوع معامله"
)

ABOUT_USDT_TEXT = (
    "🪙 *خرید و فروش USDT*\n\n"
    "صراف روند خرید و فروش تتر را از دریافت نرخ تا ثبت و پیگیری سفارش در یک مسیر روشن "
    "و قابل فهم برای کاربر فراهم می‌کند.\n\n"
    f"• محدودهٔ سفارش: *{USDT_MIN_AMOUNT:g} تا {USDT_MAX_AMOUNT:g} USDT*\n"
    "• دریافت نرخ و محاسبهٔ مبلغ معامله\n"
    "• کارمزد پلکانی و شفاف برای خرید\n"
    "• انتخاب روش پرداخت یا دریافت\n"
    "• انتخاب صرافی یا کیف پول و شبکهٔ انتقال\n"
    "• ثبت رسید یا مدرک انتقال\n"
    "• کد اختصاصی برای هر سفارش\n"
    "• پیگیری وضعیت سفارش تا تکمیل\n"
    "• مشاهدهٔ سفارش‌های قبلی و ثبت امتیاز پس از معامله\n\n"
    "🚀 خدمات USDT از طریق مینی‌اپ تلگرام صراف در دسترس است."
)

ABOUT_SECURITY_TEXT = (
    "🛡 *امنیت و تایید هویت*\n\n"
    "صراف برای کاهش خطا و افزایش اطمینان در معاملات، سفارش‌ها را پیش از تکمیل بررسی می‌کند.\n\n"
    "• تکمیل معلومات پایه برای ثبت سفارش\n"
    f"• تایید هویت تکمیلی برای سفارش‌های بالاتر از *{USDT_IDENTITY_VERIFICATION_THRESHOLD_USD:g} USDT*\n"
    "• بررسی دستی سفارش‌های مالی پیش از تکمیل\n"
    "• کنترل معلومات پرداخت، شبکه و آدرس مقصد\n"
    "• پیگیری وضعیت هر سفارش تا پایان روند\n\n"
    "جزییات فنی و ساختار داخلی سیستم به‌دلایل امنیتی به‌صورت عمومی نشر نمی‌شود."
)

ABOUT_DEVELOPER_TEXT = (
    "👨‍💻 *توسعه و برند*\n\n"
    "*سجاد محمدی — بنیان‌گذار و سازندهٔ صراف*\n\n"
    "در مرز فناوری و بازارهای مالی کار می‌کند؛ جایی که داده، طراحی و تصمیم‌گیری به یک محصول واقعی تبدیل می‌شوند.\n\n"
    "*صراف امضای همین نگاه است: ساده، دقیق، سریع و ساخته‌شده برای افغانستان.*\n\n"
    f"ارتباط مستقیم: {SUPPORT_TELEGRAM_USERNAME}"
)

DISCLAIMER_TEXT = (
    "⚠️ *شرایط استفاده و سلب مسئولیت*\n\n"
    "• نرخ‌های عمومی صراف برای اطلاع‌رسانی و محاسبه ارائه می‌شوند و لزوماً قیمت قطعی "
    "معامله در بازار خارج از صراف نیستند.\n"
    "• معلومات بازار به‌معنای توصیهٔ سرمایه‌گذاری یا تضمین سود نیست.\n"
    "• پیش از تایید هر معاملهٔ USDT، مبلغ، نرخ، کارمزد، شبکه و آدرس مقصد را بررسی کنید.\n"
    "• مسئولیت صحت آدرس کیف پول و معلوماتی که کاربر وارد می‌کند بر عهدهٔ خود کاربر است.\n"
    "• تصمیم‌گیری مالی و نتایج ناشی از خرید، فروش یا انتقال دارایی بر عهدهٔ کاربر است.\n\n"
    "© 2026 صراف"
)


def about_keyboard(page: str = "home") -> InlineKeyboardMarkup:
    if page == "home":
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📊 بازارها و نرخ‌ها", callback_data="about:markets"),
                    InlineKeyboardButton("🧮 ابزارهای مالی", callback_data="about:tools"),
                ],
                [
                    InlineKeyboardButton("🪙 خدمات USDT", callback_data="about:usdt"),
                    InlineKeyboardButton("🛡 امنیت و تایید هویت", callback_data="about:security"),
                ],
                [
                    InlineKeyboardButton("👨‍💻 توسعه و برند", callback_data="about:developer"),
                    InlineKeyboardButton("⚠️ شرایط استفاده", callback_data="about:disclaimer"),
                ],
            ]
        )

    rows = []

    if page == "usdt":
        rows.append(
            [InlineKeyboardButton("🚀 ورود به خدمات USDT", callback_data="about:open_usdt")]
        )

    rows.append(
        [InlineKeyboardButton("🔙 بازگشت به درباره صراف", callback_data="about:home")]
    )
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)
    safe_name = _escape_markdown_legacy(user.first_name or "دوست عزیز")
    await update.message.reply_text(
        WELCOME_TEXT.format(name=safe_name),
        parse_mode="Markdown",
        reply_markup=main_menu(is_admin=user.id in ADMIN_CHAT_IDS),
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        ABOUT_HOME_TEXT,
        parse_mode="Markdown",
        reply_markup=about_keyboard(),
    )


async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]

    if action == "home":
        await query.edit_message_text(
            ABOUT_HOME_TEXT,
            parse_mode="Markdown",
            reply_markup=about_keyboard(),
        )
        return

    if action == "open_usdt":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🪙 *خرید و فروش USDT*\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
            parse_mode="Markdown",
            reply_markup=usdt_menu_keyboard(),
        )
        return

    pages = {
        "markets": ABOUT_MARKETS_TEXT,
        "tools": ABOUT_TOOLS_TEXT,
        "usdt": ABOUT_USDT_TEXT,
        "security": ABOUT_SECURITY_TEXT,
        "developer": ABOUT_DEVELOPER_TEXT,
        "disclaimer": DISCLAIMER_TEXT,
    }

    text = pages.get(action)
    if not text:
        logger.warning("Unknown about action: %s", action)
        return

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=about_keyboard(page=action),
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.deactivate_user(update.effective_user.id)
    await update.message.reply_text(
        "شما از دریافت پیام‌های همگانی ربات خارج شدید. هر وقت خواستید با /start دوباره فعال شوید."
    )
