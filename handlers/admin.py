import asyncio
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_CHAT_IDS, TRACKED_CURRENCIES
from services import supabase_service as db, spread_service, order_transition_service
from services import facebook_service, instagram_service
from services.order_state_machine import InvalidStateTransition

logger = logging.getLogger(__name__)


def _is_admin(update: Update) -> bool:
    return update.effective_user.id in ADMIN_CHAT_IDS


async def manual_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دکمهٔ «📢 نشر پست (فیسبوک/اینستاگرام)» در منوی اصلی — فقط برای ادمین قابل‌مشاهده
    است (keyboards.main_menu فقط برای chat_id های داخل ADMIN_CHAT_IDS این دکمه را
    اضافه می‌کند)، ولی برای دفاع در عمق، این تابع هم مستقل بررسی می‌کند.

    برخلاف پست خودکار زمان‌بندی‌شده (jobs.py)، این‌جا force=True پاس داده
    می‌شود — یعنی صرف‌نظر از این‌که نرخ تغییر محسوس کرده باشد یا نه، همیشه
    پست منتشر می‌شود؛ دقیقاً همان چیزی که برای تست دستی یا نشر فوری لازم است.
    """
    if not _is_admin(update):
        return

    status_msg = await update.message.reply_text("⏳ در حال آماده‌سازی تصویر و نشر پست در فیسبوک و اینستاگرام...")

    # وارد کردن دیرهنگام (lazy import) برای جلوگیری از حلقهٔ ایمپورت
    # (jobs.py خودش handlers را ایمپورت نمی‌کند، ولی این الگو امن‌تر و
    # مستقل از ترتیب بارگذاری ماژول‌هاست).
    from jobs import get_current_quotes_and_metals

    try:
        quotes, gold_breakdown, silver_breakdown = await get_current_quotes_and_metals()
    except Exception:
        logger.exception("خطا در دریافت نرخ‌های لحظه‌یی برای نشر دستی پست")
        await status_msg.edit_text("❌ دریافت نرخ‌های لحظه‌یی ناموفق بود؛ پستی نشر نشد.")
        return

    if not quotes:
        await status_msg.edit_text("❌ نرخی برای ساخت پست در دسترس نیست؛ پستی نشر نشد.")
        return

    fb_result, ig_result = await asyncio.gather(
        facebook_service.check_and_maybe_post(quotes, gold_breakdown, silver_breakdown, force=True),
        instagram_service.check_and_maybe_post(quotes, gold_breakdown, silver_breakdown, force=True),
        return_exceptions=True,
    )

    def _line(platform: str, result) -> str:
        if isinstance(result, Exception):
            logger.exception("خطای غیرمنتظره در نشر دستی پست %s", platform, exc_info=result)
            return f"❌ {platform}: خطای غیرمنتظره (جزئیات در لاگ سرور)"
        return f"✅ {platform}: با موفقیت منتشر شد" if result else f"❌ {platform}: نشر ناموفق (لاگ سرور را ببینید)"

    summary = "\n".join([
        "📢 نتیجهٔ نشر دستی پست:",
        _line("فیسبوک", fb_result),
        _line("اینستاگرام", ig_result),
    ])
    await status_msg.edit_text(summary)


async def usdt_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    orders = db.get_pending_usdt_orders()
    if not orders:
        await update.message.reply_text("سفارش در انتظاری برای تتر وجود ندارد.")
        return
    lines = ["📋 *سفارش‌های تتر در انتظار*\n"]
    for o in orders:
        code = f"USDT-{o['id']:05d}"
        kind = "خرید" if o["order_type"] == "buy" else "فروش"
        lines.append(f"`{code}` | {kind} | {o['usdt_amount']:g} USDT | {o['total_afn']:,.0f} افغانی")
    lines.append("\nبرای تأیید سفارش: /usdtconfirm شمارهٔ_سفارش")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def usdt_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /usdtconfirm 12  (فقط شمارهٔ سفارش)")
        return
    try:
        order_id = int(context.args[0].replace("USDT-", "").lstrip("0") or "0")
    except ValueError:
        await update.message.reply_text("⚠️ شمارهٔ سفارش نامعتبر است.")
        return
    order = db.get_usdt_order_by_id(order_id)
    if not order:
        await update.message.reply_text("⚠️ سفارشی با این کد یافت نشد.")
        return
    # این دستور قبلاً مستقیماً db.update_usdt_order_status را صدا می‌زد — بدون
    # بررسی وضعیت فعلی سفارش، بدون actor/reason، و بدون Audit Log؛ یعنی یک مسیر
    # دوم و ناهماهنگ برای همان business rule که در admin_bot.py با
    # order_transition_service پیاده‌سازی شده بود (§9، §26: یکپارچه‌سازی duplicate
    # logic). حالا از همان منبع واحد استفاده می‌کند.
    try:
        order_transition_service.transition_order_status(
            order_id, "confirmed", changed_by=update.effective_user.id, reason="تایید از طریق دستور /usdtconfirm"
        )
    except order_transition_service.OrderNotFoundError:
        await update.message.reply_text("⚠️ سفارشی با این کد یافت نشد.")
        return
    except InvalidStateTransition:
        await update.message.reply_text(
            f"⚠️ سفارش USDT-{order_id:05d} در وضعیت «{order['status']}» است و قابل تایید نیست."
        )
        return
    await update.message.reply_text(f"✅ سفارش USDT-{order_id:05d} تأیید شد.")
    try:
        await context.bot.send_message(
            chat_id=order["chat_id"],
            text=f"✅ سفارش شما (USDT-{order_id:05d}) تأیید و در حال پردازش نهایی است.",
        )
    except Exception:
        logger.exception("خطا در اطلاع‌رسانی تأیید سفارش به کاربر")


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
            "استفاده: /setspread usd 0.8\n(کد ارز و درصد اسپرد را وارد کنید)"
        )
        return

    code, pct_str = args
    code = code.lower()
    if code not in TRACKED_CURRENCIES:
        await update.message.reply_text(
            f"⚠️ ارز «{code}» در لیست ارزهای پیگیری‌شده نیست."
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

    name = TRACKED_CURRENCIES[code]
    await update.message.reply_text(f"✅ اسپرد {name} به {pct}٪ تنظیم شد.")


async def list_spreads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/spreads — نمایش اسپرد فعلی همهٔ ارزها."""
    if not _is_admin(update):
        return

    lines = ["📐 *اسپرد فعلی ارزها*\n"]
    for code, name in TRACKED_CURRENCIES.items():
        pct = spread_service.get_spread_percent(code)
        lines.append(f"▫️ {name} ({code.upper()}): {pct}٪")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
