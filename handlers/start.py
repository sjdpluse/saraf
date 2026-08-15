import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import (
    SUPPORT_TELEGRAM_USERNAME,
    TRACKED_CURRENCIES,
    USDT_IDENTITY_VERIFICATION_THRESHOLD_USD,
    USDT_MAX_AMOUNT,
    USDT_MIN_AMOUNT,
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
    "به *Saraf | صراف* خوش آمدید.\n"
    "پلتفرم نرخ بازار، ابزارهای مالی و خدمات ارزی افغانستان.\n\n"
    "💵 نرخ ارزها  |  🥇 طلا  |  🥈 نقره  |  🪙 رمزارزها\n"
    "📊 مقایسه تاریخی  |  🔄 مبدل ارز  |  🪙 خرید و فروش USDT\n\n"
    "از منوی زیر سرویس مورد نظر خود را انتخاب کنید. 👇"
)

ABOUT_HOME_TEXT = (
    "🏦 *SARAF | صراف*\n\n"
    "*پلتفرم هوشمند نرخ بازار و خدمات ارزی افغانستان*\n\n"
    "Saraf نرخ‌های بازار افغانستان و منابع بین‌المللی را با ابزارهای محاسبه، "
    "مقایسه تاریخی و خدمات خرید و فروش USDT در یک سیستم واحد ارائه می‌کند.\n\n"
    "هدف Saraf این است که کاربر بتواند نرخ را بررسی کند، ارزش معامله را محاسبه کند، "
    "تغییرات گذشته را ببیند و در بخش USDT درخواست معامله را به‌صورت قابل پیگیری ثبت کند.\n\n"
    "*نرخ را ببین. محاسبه کن. با اطمینان معامله کن.*\n\n"
    "برای مشاهده جزئیات هر بخش، یکی از گزینه‌های زیر را انتخاب کنید. 👇"
)

ABOUT_MARKETS_TEXT = (
    "📊 *بازارها و نرخ‌ها*\n\n"
    f"💵 *ارزهای خارجی — {len(TRACKED_CURRENCIES)} ارز*\n"
    "• دالر، یورو، پوند، کلدار پاکستانی، تومان، درهم، روپیه، ریال سعودی، لیره، "
    "یوان و سایر ارزهای پشتیبانی‌شده\n"
    "• نمایش نرخ خرید و فروش در برابر افغانی\n"
    "• استفاده از نرخ بازارهای محلی در صورت دسترس بودن\n"
    "• نمایش نرخ مرجع بازار جهانی در کنار نرخ محلی\n\n"
    "🥇 *طلا*\n"
    "• نرخ طلای ۲۴، ۲۲، ۲۱ و ۱۸ عیار\n"
    "• قیمت به گرم و مثقال، به افغانی و دالر\n"
    "• نمایش قیمت جهانی هر اونس تروی\n\n"
    "🥈 *نقره*\n"
    "• نرخ نقره خالص به گرم و مثقال\n"
    "• نمایش معادل افغانی و دالر\n\n"
    "🪙 *رمزارزها*\n"
    "• BTC، ETH، SOL، BNB، XRP و SHIB\n"
    "• قیمت به دالر و معادل افغانی"
)

ABOUT_TOOLS_TEXT = (
    "🧮 *ابزارهای مالی Saraf*\n\n"
    "📊 *مقایسه تاریخی*\n"
    "• مقایسه ارزها و طلای ۲۴ عیار با ۲۴ ساعت، ۷، ۳۰ و ۹۰ روز گذشته\n"
    "• نمایش درصد تغییر و جهت حرکت نرخ\n\n"
    "🔄 *مبدل ارز جهانی*\n"
    "• تبدیل مستقیم میان ارزهای پشتیبانی‌شده\n"
    "• محاسبه نرخ واحد و مبلغ نهایی\n\n"
    "💵 *ماشین‌حساب ارز به افغانی*\n"
    "• محاسبه مبلغ بر اساس نرخ خرید و فروش بازار\n\n"
    "🥇 *ماشین‌حساب طلا*\n"
    "• محاسبه خرید و فروش بر اساس عیار، وزن و هزینه/کسر معامله\n\n"
    "🥈 *ماشین‌حساب نقره*\n"
    "• محاسبه خرید و فروش نقره بر اساس وزن و تنظیمات معامله"
)

ABOUT_USDT_TEXT = (
    "🪙 *خرید و فروش USDT*\n\n"
    "Saraf برای تتر فقط نرخ نمایش نمی‌دهد؛ چرخه ثبت، بررسی و پیگیری سفارش را نیز "
    "مدیریت می‌کند.\n\n"
    f"• محدوده سفارش: *{USDT_MIN_AMOUNT:g} تا {USDT_MAX_AMOUNT:g} USDT*\n"
    "• دریافت نرخ خرید/فروش و محاسبه مبلغ معامله\n"
    "• کارمزد پلکانی شفاف برای خرید\n"
    "• پرداخت بانکی آنلاین یا مراجعه حضوری\n"
    "• انتخاب صرافی/کیف پول مقصد و شبکه انتقال\n"
    "• پشتیبانی از شبکه‌های تعریف‌شده مانند TRC20، ERC20 و BEP20\n"
    "• آپلود رسید پرداخت یا مدرک انتقال\n"
    "• کد اختصاصی برای هر سفارش\n"
    "• پیگیری سفارش از ثبت تا تایید و تکمیل\n"
    "• مشاهده سفارش‌های قبلی در Mini App\n"
    "• امتیازدهی ۱ تا ۵ ستاره پس از تکمیل معامله\n"
    "• نمایش آمار واقعی معاملات تکمیل‌شده و میانگین امتیاز در Mini App\n"
    "• تولید کارت دیجیتال سفارش برای استفاده مشتری و مدیریت\n\n"
    "🚀 خدمات USDT از طریق *Telegram Mini App* ارائه می‌شود و در صورت غیرفعال بودن "
    "Mini App، جریان گفتگویی داخل ربات به‌عنوان مسیر جایگزین در دسترس است."
)

ABOUT_SECURITY_TEXT = (
    "🛡 *امنیت، احراز هویت و کنترل ریسک*\n\n"
    "👤 *پروفایل و KYC*\n"
    "• تکمیل اطلاعات پایه برای ثبت سفارش‌های USDT\n"
    f"• احراز هویت تکمیلی با مدرک هویتی و سلفی برای سفارش‌های بالاتر از "
    f"*{USDT_IDENTITY_VERIFICATION_THRESHOLD_USD:g} USDT*\n"
    "• نگهداری مدارک هویتی در فضای ذخیره‌سازی خصوصی\n\n"
    "⭐ *Trust Profile و Risk Engine*\n"
    "• پروفایل اعتبار بر اساس وضعیت KYC و سابقه معاملات\n"
    "• ارزیابی ریسک سفارش پیش از بررسی مدیریت\n"
    "• ثبت تعداد معاملات موفق/لغوشده و امتیاز اعتماد\n\n"
    "🔐 *کنترل‌های فنی*\n"
    "• اعتبارسنجی Telegram Mini App initData برای APIهای حساس\n"
    "• اعتبارسنجی آدرس کیف پول بر اساس شبکه\n"
    "• Rate Limit برای درخواست‌ها و آپلودهای حساس\n"
    "• جلوگیری از ثبت تکراری سفارش در Retry/Double-click\n"
    "• ثبت Audit برای رویدادهای مهم\n"
    "• ربات مدیریت جداگانه برای پردازش اعلان‌ها و سفارش‌های مالی"
)

ABOUT_DATA_TEXT = (
    "📡 *داده‌ها و نرخ‌های بازار*\n\n"
    "Saraf از یک موتور نرخ مرکزی استفاده می‌کند تا داده‌های بازار محلی و نرخ‌های مرجع "
    "بین‌المللی را در یک ساختار واحد پردازش کند.\n\n"
    "• نرخ بازار محلی در اولویت قرار می‌گیرد؛ در صورت نبود داده کافی، نرخ مرجع "
    "به‌عنوان پشتیبان استفاده می‌شود\n"
    "• Snapshotهای نرخ به‌صورت دوره‌ای ذخیره می‌شوند تا مقایسه تاریخی ممکن باشد\n"
    "• نرخ‌های طلا و نقره از قیمت جهانی و نرخ دالر/افغانی محاسبه می‌شوند\n"
    "• نرخ رمزارزهای پشتیبانی‌شده از CoinGecko دریافت می‌شود\n"
    "• API و ربات از همان لایه سرویس استفاده می‌کنند تا اعداد بین کانال‌ها یکسان بماند\n\n"
    "نرخ‌های عمومی برای اطلاع‌رسانی هستند؛ قیمت نهایی یک معامله می‌تواند بر اساس نوع "
    "سفارش، کارمزد، شبکه و شرایط همان لحظه متفاوت باشد."
)

ABOUT_INFRASTRUCTURE_TEXT = (
    "⚙️ *سرویس‌ها و زیرساخت Saraf*\n\n"
    "🤖 *Telegram Bot*\n"
    "رابط اصلی کاربران برای نرخ‌ها، ابزارها و خدمات ارزی.\n\n"
    "📱 *Telegram Mini App*\n"
    "رابط کامل خرید/فروش USDT، KYC، سفارش‌ها، Timeline، رسید و امتیازدهی.\n\n"
    "🌐 *Saraf API*\n"
    "API مشترک برای نرخ ارز، طلا، مبدل، مقایسه تاریخی و عملیات Mini App.\n\n"
    "🗄 *Supabase*\n"
    "ذخیره تاریخچه نرخ‌ها، پروفایل‌ها، سفارش‌ها، امتیازها و فایل‌های مورد نیاز.\n\n"
    "🛡 *Admin & Risk Services*\n"
    "ربات مدیریت مستقل، موتور ریسک، Trust Profile، Audit و مدیریت وضعیت سفارش.\n\n"
    "📣 *Facebook Automation*\n"
    "بررسی دوره‌ای تغییر نرخ‌ها و امکان تولید/انتشار خودکار پست نرخ در صورت تغییر "
    "معنادار.\n\n"
    "❤️ *Health Monitoring*\n"
    "بررسی سلامت سرویس و دسترسی پایگاه داده برای تشخیص وضعیت عادی یا degraded."
)

ABOUT_DEVELOPER_TEXT = (
    "👨‍💻 *توسعه و طراحی Saraf*\n\n"
    "*Sajad Mohammadi*\n"
    f"پشتیبانی تلگرام: {SUPPORT_TELEGRAM_USERNAME}\n\n"
    "Saraf به‌صورت مستمر بر اساس داده‌های واقعی، نیاز بازار و بازخورد کاربران "
    "توسعه داده می‌شود.\n\n"
    "گزارش خطا، پیشنهاد قابلیت جدید و بازخورد تجربه کاربری مستقیماً به بهبود سرویس "
    "کمک می‌کند."
)

DISCLAIMER_TEXT = (
    "⚠️ *شرایط استفاده و سلب مسئولیت*\n\n"
    "• نرخ‌های عمومی Saraf برای اطلاع‌رسانی و محاسبه ارائه می‌شوند و لزوماً قیمت "
    "قطعی معامله در بازار خارج از Saraf نیستند.\n"
    "• اطلاعات بازار به‌منزله توصیه سرمایه‌گذاری یا تضمین سود نیست.\n"
    "• پیش از تایید هر معامله USDT، مبلغ، نرخ، کارمزد، شبکه و آدرس مقصد را بررسی کنید.\n"
    "• مسئولیت صحت آدرس کیف پول و اطلاعاتی که کاربر وارد می‌کند بر عهده خود کاربر است.\n"
    "• تصمیم‌گیری مالی و نتایج ناشی از خرید، فروش یا انتقال دارایی بر عهده کاربر است.\n\n"
    "© 2026 SARAF — *Smart Market Intelligence & Exchange*"
)


def about_keyboard(page: str = "home") -> InlineKeyboardMarkup:
    if page == "home":
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 بازارها و نرخ‌ها",
                        callback_data="about:markets",
                    ),
                    InlineKeyboardButton(
                        "🧮 ابزارهای مالی",
                        callback_data="about:tools",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "🪙 خدمات USDT",
                        callback_data="about:usdt",
                    ),
                    InlineKeyboardButton(
                        "🛡 امنیت و KYC",
                        callback_data="about:security",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "📡 داده‌ها و نرخ‌ها",
                        callback_data="about:data",
                    ),
                    InlineKeyboardButton(
                        "⚙️ سرویس‌ها و زیرساخت",
                        callback_data="about:infrastructure",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "👨‍💻 توسعه و برند",
                        callback_data="about:developer",
                    ),
                    InlineKeyboardButton(
                        "⚠️ شرایط استفاده",
                        callback_data="about:disclaimer",
                    ),
                ],
            ]
        )

    rows = []

    if page == "usdt":
        rows.append(
            [
                InlineKeyboardButton(
                    "🚀 ورود به خدمات USDT",
                    callback_data="about:open_usdt",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "🔙 بازگشت به درباره Saraf",
                callback_data="about:home",
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user

    db.upsert_user(
        user.id,
        user.username,
        user.full_name,
    )

    safe_name = _escape_markdown_legacy(
        user.first_name or "دوست عزیز"
    )

    await update.message.reply_text(
        WELCOME_TEXT.format(name=safe_name),
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


async def about(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await update.message.reply_text(
        ABOUT_HOME_TEXT,
        parse_mode="Markdown",
        reply_markup=about_keyboard(),
    )


async def about_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
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
            text=(
                "🪙 *خرید و فروش USDT*\n\n"
                "یکی از گزینه‌های زیر را انتخاب کنید:"
            ),
            parse_mode="Markdown",
            reply_markup=usdt_menu_keyboard(),
        )
        return

    pages = {
        "markets": ABOUT_MARKETS_TEXT,
        "tools": ABOUT_TOOLS_TEXT,
        "usdt": ABOUT_USDT_TEXT,
        "security": ABOUT_SECURITY_TEXT,
        "data": ABOUT_DATA_TEXT,
        "infrastructure": ABOUT_INFRASTRUCTURE_TEXT,
        "developer": ABOUT_DEVELOPER_TEXT,
        "disclaimer": DISCLAIMER_TEXT,
    }

    text = pages.get(action)

    if not text:
        logger.warning(
            "Unknown about action: %s",
            action,
        )
        return

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=about_keyboard(page=action),
    )


async def stop(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    db.deactivate_user(
        update.effective_user.id
    )

    await update.message.reply_text(
        "شما از دریافت پیام‌های همگانی ربات خارج شدید. "
        "هر وقت خواستید با /start دوباره فعال شوید."
    )