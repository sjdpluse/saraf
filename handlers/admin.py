import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_CHAT_IDS, TRACKED_CURRENCIES, GOLD_KARATS
from services import supabase_service as db, spread_service

GOLD_SPREAD_KEYS = {f"gold{k}": f"طلای عیار {k}" for k in GOLD_KARATS}

logger = logging.getLogger(__name__)


def _is_admin(update: Update) -> bool:
    return update.effective_user.id in ADMIN_CHAT_IDS


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/broadcast <پیام> — فقط برای مدیران. پیام به همهٔ کاربران فعال ارسال می‌شود."""
    if not _is_admin(update):
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
    if not _is_admin(update):
        return
    count = db.count_active_users()
    await update.message.reply_text(f"📈 تعداد کاربران فعال ربات: {count}")


async def set_spread(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/setspread <کد_ارز> <درصد> — تنظیم حاشیهٔ سود صراف برای یک ارز خاص."""
    if not _is_admin(update):
        await update.message.reply_text("این دستور فقط برای مدیران ربات است.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "استفاده: /setspread usd 0.8  یا  /setspread gold18 1.2\n"
            "(کد ارز یا کلید طلا — gold24/gold22/gold21/gold18/gold14 — و درصد اسپرد)"
        )
        return

    code, pct_str = args
    code = code.lower()
    if code in TRACKED_CURRENCIES:
        name = TRACKED_CURRENCIES[code]
    elif code in GOLD_SPREAD_KEYS:
        name = GOLD_SPREAD_KEYS[code]
    else:
        await update.message.reply_text(
            f"⚠️ «{code}» نه یک ارز پیگیری‌شده و نه یک کلید طلای معتبر است."
        )
        return

    try:
        pct = float(pct_str)
        spread_service.set_spread_percent(code, pct)
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
        return
    except Exception:
        logger.exception("خطا در تنظیم اسپرد")
        await update.message.reply_text("⚠️ خطا در ذخیرهٔ تنظیم اسپرد.")
        return

    await update.message.reply_text(f"✅ اسپرد {name} به {pct}٪ تنظیم شد.")


async def list_spreads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/spreads — نمایش اسپرد فعلی همهٔ ارزها."""
    if not _is_admin(update):
        return

    lines = ["📐 *اسپرد فعلی ارزها*\n"]
    for code, name in TRACKED_CURRENCIES.items():
        pct = spread_service.get_spread_percent(code)
        lines.append(f"▫️ {name} ({code.upper()}): {pct}٪")

    lines.append("\n📐 *اسپرد فعلی طلا (فقط برای نرخ رسمی تک‌عددی کابل)*\n")
    for code, name in GOLD_SPREAD_KEYS.items():
        pct = spread_service.get_spread_percent(code)
        lines.append(f"▫️ {name}: {pct}٪")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
