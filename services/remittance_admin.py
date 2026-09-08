import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

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
            [InlineKeyboardButton("💵 پول به گیرنده پرداخت شد", callback_data=f"remit_complete:{order_id}")],
            [InlineKeyboardButton("⏸ توقف", callback_data=f"remit_hold:{order_id}")],
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
        "remit_complete": "completed",
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
        "completed": "💵 پرداخت و تکمیل شد",
    }
    await query.answer(labels[target])
    try:
        await query.edit_message_reply_markup(reply_markup=remittance_keyboard(order_id, updated["status"]))
    except Exception:
        pass
    await query.message.reply_text(f"{labels[target]} — {updated['order_code']}")


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(remittance_callback, pattern=r"^remit_(ready|hold|cancel|complete):\d+$"))
