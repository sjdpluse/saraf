import logging
import secrets

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from config import ADMIN_CHAT_IDS
from services import remittance_service

logger = logging.getLogger(__name__)


def remittance_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup | None:
    if status == "transfer_submitted":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ کریپتو دریافت شد — آماده پرداخت", callback_data=f"remit_ready:{order_id}")],
            [InlineKeyboardButton("⏸ توقف برای بررسی", callback_data=f"remit_hold:{order_id}"),
             InlineKeyboardButton("❌ لغو", callback_data=f"remit_cancel:{order_id}")],
        ])
    if status == "on_hold":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تایید و آماده پرداخت", callback_data=f"remit_ready:{order_id}")],
            [InlineKeyboardButton("❌ لغو", callback_data=f"remit_cancel:{order_id}")],
        ])
    if status == "payout_ready":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸ توقف پرداخت", callback_data=f"remit_hold:{order_id}")],
        ])
    return None


async def remittance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not update.effective_user or update.effective_user.id not in ADMIN_CHAT_IDS:
        if query:
            await query.answer("دسترسی ندارید.", show_alert=True)
        return

    action, raw_id = query.data.split(":", 1)
    try:
        order_id = int(raw_id)
    except ValueError:
        await query.answer("شناسه نامعتبر است.", show_alert=True)
        return

    target = {
        "remit_ready": "payout_ready",
        "remit_hold": "on_hold",
        "remit_cancel": "cancelled",
    }.get(action)
    if not target:
        return

    try:
        updated = await remittance_service.transition(
            order_id,
            target,
            admin_id=update.effective_user.id,
            note=f"Admin action: {action}",
        )
    except (LookupError, ValueError) as exc:
        await query.answer(str(exc), show_alert=True)
        return
    except Exception:
        logger.exception("Remittance admin transition failed: %s", order_id)
        await query.answer("تغییر وضعیت ناموفق بود.", show_alert=True)
        return

    labels = {
        "payout_ready": "✅ آماده پرداخت نقدی",
        "on_hold": "⏸ متوقف برای بررسی",
        "cancelled": "❌ لغو شد",
    }
    await query.answer(labels[target])
    try:
        await query.edit_message_reply_markup(reply_markup=remittance_keyboard(order_id, updated["status"]))
    except Exception:
        pass

    extra = ""
    if target == "payout_ready":
        extra = (
            "\n\nبرای تکمیل پرداخت، پس از تطبیق مدرک هویت گیرنده، کد ۶ رقمی دریافت را از او بگیرید و ارسال کنید:\n"
            f"/remitpay {order_id} CODE"
        )
    await query.message.reply_text(f"{labels[target]} — {updated['order_code']}{extra}")


async def remitpay_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or update.effective_user.id not in ADMIN_CHAT_IDS or not update.message:
        return
    if len(context.args) != 2:
        await update.message.reply_text("استفاده: /remitpay <order_id> <pickup_code>")
        return
    try:
        order_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شناسه حواله نامعتبر است.")
        return
    supplied = str(context.args[1]).strip()
    order = remittance_service.get_order(order_id)
    if not order:
        await update.message.reply_text("حواله یافت نشد.")
        return
    if order.get("status") != "payout_ready":
        await update.message.reply_text("این حواله در وضعیت آمادهٔ پرداخت نیست.")
        return
    expected = str(order.get("pickup_code") or "")
    if not expected or not secrets.compare_digest(expected, supplied):
        await update.message.reply_text("❌ کد دریافت اشتباه است؛ پرداخت را انجام ندهید.")
        return

    try:
        updated = await remittance_service.transition(
            order_id,
            "completed",
            admin_id=update.effective_user.id,
            note="Pickup code verified; beneficiary identity checked by payout operator",
        )
    except Exception:
        logger.exception("Completing remittance after pickup verification failed: %s", order_id)
        await update.message.reply_text("تکمیل حواله ناموفق بود؛ وضعیت را دوباره بررسی کنید.")
        return
    await update.message.reply_text(f"💵 پرداخت تایید و حواله {updated['order_code']} تکمیل شد.")


def register(app) -> None:
    app.add_handler(CommandHandler("remitpay", remitpay_command))
    app.add_handler(CallbackQueryHandler(remittance_callback, pattern=r"^remit_(ready|hold|cancel):\d+$"))
