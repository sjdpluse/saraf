import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_CHAT_IDS
from services import supabase_service as db

logger = logging.getLogger(__name__)


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/broadcast <پیام> — فقط برای مدیران. پیام به همهٔ کاربران فعال ارسال می‌شود."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_CHAT_IDS:
        await update.message.reply_text("این دستور فقط برای مدیران ربات است.")
        return

    text = update.message.text.partition(" ")[2].strip()
    if not text:
        await update.message.reply_text("استفاده: /broadcast متن پیام شما")
        return

    chat_ids = db.get_all_active_chat_ids()
    sent, failed = 0, 0
    status_msg = await update.message.reply_text(
        f"در حال ارسال به {len(chat_ids)} کاربر..."
    )

    for chat_id in chat_ids:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # جلوگیری از محدودیت نرخ تلگرام

    await status_msg.edit_text(f"✅ ارسال شد: {sent} | ناموفق: {failed}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_CHAT_IDS:
        return
    count = db.count_active_users()
    await update.message.reply_text(f"📈 تعداد کاربران فعال ربات: {count}")
