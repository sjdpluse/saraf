"""
سرویس مشترک ثبت سفارش‌های تتر (USDT) — منبع واحد (single source of truth) که هم
جریان گفتگویی ربات (handlers/usdt.py) و هم API مینی‌اپ (api.py) از آن استفاده
می‌کنند. این‌طور منطق ثبت سفارش، متن پیام تایید، و اطلاع‌رسانی به ادمین هرگز بین
دو مسیر (چت / مینی‌اپ) واگرا نمی‌شود و احتمال باگ یا ناسازگاری به حداقل می‌رسد.

اطلاع‌رسانی به ادمین از طریق یک ربات تلگرامی کاملاً جداگانه (ADMIN_BOT_TOKEN)
انجام می‌شود تا اعلان‌های حساس مالی با پیام‌های عمومی مشتریان قاطی نشوند.
"""
import logging
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

from config import (
    ADMIN_CHAT_IDS,
    ADMIN_BOT_TOKEN,
    SUPPORT_TELEGRAM_USERNAME,
    IN_PERSON_ADDRESS,
    IN_PERSON_PHONE,
)
from services import supabase_service as db

logger = logging.getLogger(__name__)

_admin_bot_instance: Optional[Bot] = None


def get_admin_bot() -> Bot:
    global _admin_bot_instance
    if _admin_bot_instance is None:
        if not ADMIN_BOT_TOKEN:
            raise RuntimeError("ADMIN_BOT_TOKEN تنظیم نشده است؛ آن را در .env قرار دهید.")
        _admin_bot_instance = Bot(token=ADMIN_BOT_TOKEN)
    return _admin_bot_instance


async def notify_admins(text: str, order_id: Optional[int] = None) -> None:
    # ایمپورت داخل تابع برای جلوگیری از وابستگی حلقوی (keyboards <-> services)
    from keyboards import admin_order_review_keyboard

    try:
        bot = get_admin_bot()
    except RuntimeError:
        logger.exception("ربات مدیریت پیکربندی نشده؛ اعلان سفارش ارسال نشد.")
        return

    markup = admin_order_review_keyboard(order_id) if order_id else None
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup
            )
        except Exception:
            logger.exception("خطا در اطلاع‌رسانی به ادمین %s", admin_id)


def build_order_code(order_id: Optional[int]) -> str:
    return f"USDT-{order_id:05d}" if order_id else "USDT-?????"


async def create_buy_order(
    *,
    chat_id: int,
    username: Optional[str],
    full_name: Optional[str],
    phone: str,
    amount: float,
    quote: dict,
    payment_method: str,
    exchange_name: Optional[str],
    network: str,
    wallet_address: str,
    receipt_file_id: Optional[str] = None,
    source: str = "bot",
) -> dict:
    """
    سفارش خرید تتر را در پایگاه داده ثبت می‌کند، به ادمین اطلاع می‌دهد و دیکشنری
    شامل کد سفارش و متن پیام آمادهٔ نمایش به کاربر را برمی‌گرداند.

    source: "bot" یا "miniapp" — فقط برای تفکیک گزارشی، تاثیری در منطق ندارد.
    """
    order = {
        "chat_id": chat_id,
        "username": username,
        "full_name": full_name,
        "phone": phone,
        "order_type": "buy",
        "usdt_amount": amount,
        "usd_rate": quote["usd_rate"],
        "fee_percent": quote["fee_percent"],
        "total_afn": quote["total_afn"],
        "total_usd": quote["total_usd"],
        "payment_method": payment_method,
        "exchange_name": exchange_name,
        "network": network,
        "wallet_address": wallet_address,
        "receipt_file_id": receipt_file_id,
        "status": "pending",
        "source": source,
    }
    row = db.insert_usdt_order(order)
    order_id = row["id"] if row else None
    order_code = build_order_code(order_id)

    user_message = (
        f"✅ *سفارش شما ثبت شد*\n\n"
        f"کد سفارش: `{order_code}`\n"
        f"مقدار: {amount:g} USDT\n"
        f"شبکه: {network}\n"
        f"آدرس دریافت: `{wallet_address}`\n\n"
        "تتر شما پس از تأیید پرداخت، ظرف کمتر از *۱ ساعت* به آدرس فوق واریز خواهد شد.\n\n"
        f"🆘 پشتیبانی: {SUPPORT_TELEGRAM_USERNAME}"
    )

    await notify_admins(
        "🆕 *سفارش خرید تتر*\n\n"
        f"کد: `{order_code}`\n"
        f"کاربر: @{username or '-'} ({chat_id})\n"
        f"📞 تماس: {phone or '-'}\n"
        f"مقدار: {amount:g} USDT\n"
        f"مبلغ: {quote['total_afn']:,.0f} افغانی (کارمزد {quote['fee_percent']}٪)\n"
        f"روش پرداخت: {payment_method}\n"
        f"مقصد: {exchange_name or '-'}\n"
        f"شبکه: {network}\n"
        f"آدرس ولت: `{wallet_address}`\n"
        f"منبع سفارش: {source}",
        order_id=order_id,
    )

    return {"order_id": order_id, "order_code": order_code, "message": user_message}


async def create_sell_order(
    *,
    chat_id: int,
    username: Optional[str],
    full_name: Optional[str],
    phone: str,
    amount: float,
    quote: dict,
    exchange_name: str,
    network: str,
    tx_proof: Optional[str],
    receive_method: str,
    bank_info: Optional[str] = None,
    source: str = "bot",
) -> dict:
    order = {
        "chat_id": chat_id,
        "username": username,
        "full_name": full_name,
        "phone": phone,
        "order_type": "sell",
        "usdt_amount": amount,
        "usd_rate": quote["usd_rate"],
        "total_afn": quote["total_afn"],
        "total_usd": quote["total_usd"],
        "exchange_name": exchange_name,
        "network": network,
        "tx_proof": tx_proof,
        "receive_method": receive_method,
        "bank_info": bank_info,
        "status": "pending",
        "source": source,
    }
    row = db.insert_usdt_order(order)
    order_id = row["id"] if row else None
    order_code = build_order_code(order_id)

    if receive_method == "in_person":
        receive_text = (
            "برای دریافت مبلغ، به آدرس زیر مراجعه کنید:\n\n"
            f"📍 {IN_PERSON_ADDRESS}\n"
            f"📞 {IN_PERSON_PHONE}"
        )
    else:
        receive_text = "مبلغ به حساب بانکی اعلام‌شدهٔ شما واریز خواهد شد."

    user_message = (
        f"✅ *سفارش فروش شما ثبت شد*\n\n"
        f"کد سفارش: `{order_code}`\n"
        f"مقدار: {amount:g} USDT\n"
        f"مبلغ قابل دریافت: *{quote['total_afn']:,.0f} افغانی*\n\n"
        f"{receive_text}\n\n"
        "پس از تأیید تراکنش توسط تیم ما، مبلغ ظرف کمتر از *۱ ساعت* پرداخت خواهد شد.\n\n"
        f"🆘 پشتیبانی: {SUPPORT_TELEGRAM_USERNAME}"
    )

    receive_label = "حضوری" if receive_method == "in_person" else "آنلاین (بانکی)"
    await notify_admins(
        "🆕 *سفارش فروش تتر*\n\n"
        f"کد: `{order_code}`\n"
        f"کاربر: @{username or '-'} ({chat_id})\n"
        f"📞 تماس: {phone or '-'}\n"
        f"مقدار: {amount:g} USDT\n"
        f"مبلغ: {quote['total_afn']:,.0f} افغانی\n"
        f"صرافی: {exchange_name}\n"
        f"شبکه: {network}\n"
        f"روش دریافت: {receive_label}\n"
        f"اثبات تراکنش: {tx_proof or '-'}\n"
        f"اطلاعات بانکی کاربر: {bank_info or '-'}\n"
        f"منبع سفارش: {source}",
        order_id=order_id,
    )

    return {"order_id": order_id, "order_code": order_code, "message": user_message}
