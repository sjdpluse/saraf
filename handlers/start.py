import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards import about_keyboard, usdt_menu_keyboard
from services import supabase_service as db

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "سلام {name} 👋\n\n"
    "به ربات رسمی *Saraf* خوش آمدید.\n\n"
    "از منوی زیر، گزینه مورد نظر خود را انتخاب کنید. 👇"
)

ABOUT_HOME_TEXT = (
    "🏦 *SARAF*\n\n"
    "*دستیار هوشمند بازار ارز، طلا و تتر افغانستان*\n\n"
    "Saraf یک پلتفرم هوشمند برای دسترسی سریع به اطلاعات بازار و انجام خدمات ارزی است؛ "
    "ساخته شده تا نرخ‌ها، محاسبات و خدمات مرتبط با ارز، طلا و USDT را در یک تجربه ساده، "
    "شفاف و کاربردی در اختیار شما قرار دهد.\n\n"
    "*ببین. محاسبه کن. معامله کن.*\n\n"
    "از منوی زیر درباره بخش‌های مختلف Saraf بیشتر بدانید. 👇"
)

ABOUT_FEATURES_TEXT = (
    "📊 *امکانات Saraf*\n\n"
    "💵 *بازار ارز*\n"
    "• نمایش نرخ ارزهای مهم در برابر افغانی\n"
    "• مشاهده نرخ‌ها و اطلاعات به‌روز بازار\n\n"
    "🥇 *بازار طلا*\n"
    "• نرخ طلا در عیارهای ۲۴، ۲۲، ۲۱ و ۱۸\n"
    "• ماشین‌حساب خرید و فروش طلا\n\n"
    "📈 *تحلیل تغییرات*\n"
    "• مقایسه نرخ با ۲۴ ساعت، ۷، ۳۰ و ۹۰ روز گذشته\n\n"
    "🔄 *ابزارهای مالی*\n"
    "• مبدل ارز\n"
    "• محاسبه سریع ارزش معاملات\n\n"
    "🪙 *خدمات تتر*\n"
    "• خرید و فروش USDT\n"
    "• محاسبه نرخ و مبلغ معامله\n"
    "• ثبت و مدیریت درخواست سفارش"
)

ABOUT_USDT_TEXT = (
    "🪙 *خدمات خرید و فروش USDT*\n\n"
    "Saraf فقط نمایش‌دهنده نرخ تتر نیست؛ مسیر ثبت و مدیریت درخواست معامله را نیز فراهم می‌کند.\n\n"
    "🟢 خرید USDT\n"
    "🔴 فروش USDT\n"
    "⚡ دریافت نرخ و محاسبه مبلغ معامله\n"
    "🏦 پرداخت بانکی یا 🏢 پرداخت حضوری\n"
    "👛 انتخاب صرافی یا کیف پول مقصد\n"
    "🌐 انتخاب شبکه انتقال\n"
    "📋 ثبت و بررسی سفارش\n"
    "⭐ امتیازدهی پس از تکمیل سفارش\n\n"
    "برای معاملات، تکمیل پروفایل و فرآیند احراز هویت در نظر گرفته شده است تا امنیت و اعتبار معاملات افزایش یابد."
)

ABOUT_SECURITY_TEXT = (
    "🛡 *امنیت و شفافیت*\n\n"
    "Saraf برای خدمات معاملاتی خود از فرآیند احراز هویت استفاده می‌کند و اطلاعات سفارش‌ها را برای بررسی و پردازش در اختیار سیستم مدیریت قرار می‌دهد.\n\n"
    "همچنین نرخ‌های بازار از چند منبع داده دریافت می‌شوند و سیستم به‌روزرسانی و پشتیبان برای افزایش پایداری سرویس در نظر گرفته شده است.\n\n"
    "هدف ما ایجاد تجربه‌ای شفاف، قابل پیگیری و ساده برای کاربر است."
)

ABOUT_DATA_TEXT = (
    "📡 *داده‌های بازار*\n\n"
    "Saraf با تکیه بر چند منبع داده و سازوکارهای پشتیبان، نرخ‌های ارز و طلا را جمع‌آوری و به‌روزرسانی می‌کند.\n\n"
    "امکان مشاهده تغییرات تاریخی نیز به کاربر کمک می‌کند نرخ فعلی را در کنار سابقه بازار بررسی کند.\n\n"
    "این اطلاعات برای اطلاع‌رسانی و تحلیل شخصی کاربر ارائه می‌شوند و تضمین‌کننده قیمت معامله در بازار خارج از Saraf نیستند."
)

ABOUT_DEVELOPER_TEXT = (
    "👨‍💻 *توسعه و طراحی Saraf*\n\n"
    "*Sajad Mohammadi*\n"
    "Telegram: @SJDPLUS\n\n"
    "Saraf به‌صورت مستمر بر اساس بازخورد کاربران، نیازهای بازار و تجربه استفاده از محصول توسعه داده می‌شود.\n\n"
    "پیشنهادها، انتقادها و گزارش خطاهای شما به بهبود Saraf کمک می‌کند."
)

DISCLAIMER_TEXT = (
    "⚠️ *سلب مسئولیت*\n\n"
    "اطلاعات و ابزارهای ارائه‌شده در Saraf با هدف اطلاع‌رسانی و استفاده آموزشی ارائه می‌شوند "
    "و به‌منزله توصیه قطعی برای سرمایه‌گذاری، خرید یا فروش نیستند.\n\n"
    "تصمیم‌گیری مالی و مسئولیت نتایج هر معامله بر عهده کاربر است.\n\n"
    "© 2026 SARAF — *Smart Market Intelligence & Exchange*"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
        WELCOME_TEXT.format(name=user.first_name or "دوست عزیز"),
        parse_mode="Markdown",
        reply_markup=__import__("keyboards").main_menu(),
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
            ABOUT_HOME_TEXT, parse_mode="Markdown", reply_markup=about_keyboard()
        )
        return

    pages = {
        "features": ABOUT_FEATURES_TEXT,
        "usdt": ABOUT_USDT_TEXT,
        "security": ABOUT_SECURITY_TEXT,
        "data": ABOUT_DATA_TEXT,
        "developer": ABOUT_DEVELOPER_TEXT,
        "disclaimer": DISCLAIMER_TEXT,
    }

    text = pages.get(action)
    if not text:
        return

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=about_keyboard(page=action),
    )


async def about_usdt_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🪙 *خرید و فروش USDT*\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=usdt_menu_keyboard(),
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.deactivate_user(update.effective_user.id)
    await update.message.reply_text(
        "شما از دریافت پیام‌های همگانی ربات خارج شدید. هر وقت خواستید با /start "
        "دوباره فعال شوید."
    )
