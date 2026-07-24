import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards import main_menu, BTN_ABOUT
from services import supabase_service as db

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "سلام {name} 👋\n\n"
    "به ربات رسمی *Saraf* خوش آمدید.\n\n"
    "از منوی زیر، گزینه مورد نظر خود را انتخاب کنید. 👇"
)

ABOUT_TEXT = (
    "🏦 *Saraf*\n\n"
    "مرجع هوشمند اطلاع‌رسانی نرخ ارز و قیمت طلا در افغانستان.\n\n"
    "Saraf با هدف فراهم‌سازی دسترسی سریع، دقیق و رایگان به اطلاعات بازار مالی افغانستان توسعه یافته است تا کاربران، تاجران، صرافان، سرمایه‌گذاران و عموم مردم بتوانند در هر زمان به جدیدترین نرخ‌های ارز و طلا دسترسی داشته باشند.\n\n"
    "✨ امکانات:\n"
    "• نمایش نرخ لحظه‌ای ارزهای معتبر در برابر افغانی\n"
    "• نمایش قیمت طلا در عیارهای ۲۴، ۲۲، ۲۱ و ۱۸\n"
    "• مشاهده تغییرات قیمت در بازه‌های زمانی مختلف\n"
    "• استفاده از چندین منبع معتبر داده با سیستم پشتیبان خودکار\n"
    "• بروزرسانی مداوم اطلاعات در طول شبانه‌روز\n"
    "• تحلیل هوشمند مبتنی بر داده‌های بازار و اصول مدیریت ریسک\n\n"
    "🎯 مأموریت ما ایجاد یک مرجع قابل اعتماد، شفاف و در دسترس برای اطلاعات بازار ارز و طلا در افغانستان و کمک به تصمیم‌گیری آگاهانه کاربران است.\n\n"
    "👨‍💻 توسعه و طراحی:\n"
    "*Sajad Mohammadi*\n"
    "Telegram: @SJDPLUS\n\n"
    "از پیشنهادها، انتقادها و گزارش خطاهای شما برای بهبود مستمر Saraf استقبال می‌کنیم.\n\n"
    "⚠️ اطلاعات این ربات صرفاً جهت اطلاع‌رسانی و اهداف آموزشی ارائه می‌شود و نباید به‌عنوان توصیه قطعی برای سرمایه‌گذاری یا خرید و فروش تلقی گردد. مسئولیت هرگونه تصمیم مالی بر عهده کاربر است.\n\n"
    "© 2026 Saraf — Smart Exchange Rates & Gold Price bot"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
        WELCOME_TEXT.format(name=user.first_name or "دوست عزیز"),
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(ABOUT_TEXT, parse_mode="Markdown")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.deactivate_user(update.effective_user.id)
    await update.message.reply_text(
        "شما از دریافت پیام‌های همگانی ربات خارج شدید. هر وقت خواستید با /start "
        "دوباره فعال شوید."
    )
