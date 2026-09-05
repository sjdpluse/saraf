"""
سرویس مشترک ثبت سفارش‌های USDT / USDC.

نام فایل، جدول و بعضی فیلدهای usdt_* برای سازگاری با نسخه‌های قبلی حفظ شده‌اند؛
اما هر سفارش جدید asset مشخص دارد و تمام پیام‌ها، کد سفارش و کارت مشتری بر اساس
همان asset ساخته می‌شوند.
"""
import logging
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

from config import (
    ADMIN_CHAT_IDS,
    ADMIN_BOT_TOKEN,
    BOT_TOKEN,
    SUPPORT_TELEGRAM_USERNAME,
    IN_PERSON_ADDRESS,
    IN_PERSON_PHONE,
    USDT_CARDS_BUCKET,
)
from services import supabase_service as db
from services import risk_engine, card_service, quote_service, audit_service, usdt_service

logger = logging.getLogger(__name__)

_admin_bot_instance: Optional[Bot] = None
_customer_bot_instance: Optional[Bot] = None


def get_admin_bot() -> Bot:
    global _admin_bot_instance
    if _admin_bot_instance is None:
        if not ADMIN_BOT_TOKEN:
            raise RuntimeError("ADMIN_BOT_TOKEN تنظیم نشده است؛ آن را در .env قرار دهید.")
        _admin_bot_instance = Bot(token=ADMIN_BOT_TOKEN)
    return _admin_bot_instance


def get_customer_bot() -> Bot:
    global _customer_bot_instance
    if _customer_bot_instance is None:
        if not BOT_TOKEN:
            raise RuntimeError("BOT_TOKEN تنظیم نشده است؛ آن را در .env قرار دهید.")
        _customer_bot_instance = Bot(token=BOT_TOKEN)
    return _customer_bot_instance


def _md_escape(value) -> str:
    if value is None:
        return "-"
    text = str(value)
    if not text:
        return "-"
    for ch in ("\\", "_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


def _asset_from(asset: Optional[str] = None, quote: Optional[dict] = None) -> str:
    return usdt_service.normalize_asset(asset or (quote or {}).get("asset"))


def _asset_fa(asset: str) -> str:
    return usdt_service.asset_name_fa(asset)


async def notify_admins(text: str, order_id: Optional[int] = None) -> None:
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
                chat_id=admin_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=markup,
            )
        except Exception:
            logger.exception("خطا در اطلاع‌رسانی به ادمین %s با Markdown؛ تلاش دوباره بدون فرمت‌بندی", admin_id)
            try:
                await bot.send_message(chat_id=admin_id, text=text, reply_markup=markup)
            except Exception:
                logger.exception("ارسال نسخهٔ ساده هم برای ادمین %s ناموفق بود", admin_id)


async def notify_admins_photo(photo: str, caption: str) -> None:
    if not photo:
        return
    try:
        bot = get_admin_bot()
    except RuntimeError:
        logger.exception("ربات مدیریت پیکربندی نشده؛ تصویر رسید ارسال نشد.")
        return

    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_photo(chat_id=admin_id, photo=photo, caption=caption)
        except Exception:
            logger.exception("خطا در ارسال تصویر رسید به ادمین %s", admin_id)


def build_order_code(order_id: Optional[int], asset: Optional[str] = None) -> str:
    selected = usdt_service.normalize_asset(asset)
    return f"{selected}-{order_id:05d}" if order_id else f"{selected}-?????"


def _find_existing_order(chat_id: int, idempotency_key: str) -> Optional[dict]:
    res = (
        db.get_client()
        .table("usdt_orders")
        .select("*")
        .eq("chat_id", chat_id)
        .eq("idempotency_key", idempotency_key)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def _duplicate_response(row: dict) -> dict:
    asset = _asset_from(row.get("asset"))
    return {
        "order_id": row["id"],
        "order_code": build_order_code(row["id"], asset),
        "asset": asset,
        "message": "سفارش قبلی شما برای همین درخواست ثبت شده است.",
        "risk_level": row.get("risk_level"),
        "duplicate": True,
    }


_KYC_STATUS_SHORT = {
    "pending": "🟡 Pending",
    "verified": "🔵 Verified",
    "trusted": "🟢 Trusted",
    "restricted": "🔴 Restricted",
}


def _trust_snippet(profile: Optional[dict]) -> str:
    if not profile:
        return ""
    status = _KYC_STATUS_SHORT.get(profile.get("kyc_status"), "-")
    return (
        f"\n👤 {status} | ✅ {profile.get('successful_orders', 0)} معاملهٔ موفق | "
        f"⭐ Trust Score: {profile.get('trust_score', 0)}/100\n"
    )


async def _send_order_card(order_id: int, order_for_card: dict, chat_id: int) -> None:
    try:
        profile = db.get_user_profile(chat_id)
        if not profile:
            return
        asset = _asset_from(order_for_card.get("asset"))
        card_order = {**order_for_card, "id": order_id, "asset": asset}
        card_bytes = await card_service.generate_order_card(card_order, profile)
        if not card_bytes:
            return

        order_code = build_order_code(order_id, asset)

        try:
            await get_customer_bot().send_photo(
                chat_id=chat_id,
                photo=card_bytes,
                caption=(
                    f"🪪 کارت دیجیتال سفارش {order_code}\n\n"
                    "این کارت را می‌توانید هنگام مراجعهٔ حضوری به نمایندهٔ Saraf نشان دهید."
                ),
            )
        except Exception:
            logger.exception("خطا در ارسال کارت دیجیتال به کاربر %s", chat_id)

        try:
            admin_bot = get_admin_bot()
            for admin_id in ADMIN_CHAT_IDS:
                await admin_bot.send_photo(
                    chat_id=admin_id,
                    photo=card_bytes,
                    caption=f"🪪 کارت مشتری — {order_code}",
                )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("خطا در ارسال کارت دیجیتال به ادمین")

        path = db.upload_private_file(USDT_CARDS_BUCKET, card_bytes, f"{order_code}.png", "image/png")
        if path:
            db.set_order_card_path(order_id, path)
    except Exception:
        logger.exception("خطا در ساخت/ارسال کارت دیجیتال سفارش %s", order_id)


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
    idempotency_key: Optional[str] = None,
    quote_id: Optional[int] = None,
    asset: Optional[str] = None,
) -> dict:
    selected_asset = _asset_from(asset, quote)
    asset_fa = _asset_fa(selected_asset)

    if idempotency_key:
        existing = _find_existing_order(chat_id, idempotency_key)
        if existing:
            return _duplicate_response(existing)

    profile = db.get_user_profile(chat_id)
    risk_level, risk_reasons = risk_engine.assess_risk(profile, amount)

    order = {
        "chat_id": chat_id,
        "username": username,
        "full_name": full_name,
        "phone": phone,
        "order_type": "buy",
        "asset": selected_asset,
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
        "risk_level": risk_level,
        "risk_reasons": "؛ ".join(risk_reasons) if risk_reasons else None,
    }
    if idempotency_key:
        order["idempotency_key"] = idempotency_key
    if quote_id:
        order["quote_id"] = quote_id

    row = db.insert_usdt_order(order)
    if not row and idempotency_key:
        existing = _find_existing_order(chat_id, idempotency_key)
        if existing:
            return _duplicate_response(existing)

    order_id = row["id"] if row else None
    order_code = build_order_code(order_id, selected_asset)

    if order_id and quote_id:
        quote_service.consume(quote_id, chat_id=chat_id, order_id=order_id)
    if order_id:
        audit_service.record(
            action="order_created",
            entity="usdt_order",
            entity_id=order_id,
            actor=chat_id,
            after={
                "order_type": "buy",
                "asset": selected_asset,
                "quote_id": quote_id,
                "source": source,
            },
        )

    user_message = (
        f"✅ *سفارش شما ثبت شد*\n\n"
        f"کد سفارش: `{order_code}`\n"
        f"دارایی: *{selected_asset}* ({asset_fa})\n"
        f"مقدار: {amount:g} {selected_asset}\n"
        f"شبکه: {_md_escape(network)}\n"
        f"آدرس دریافت: `{wallet_address}`\n\n"
        f"{selected_asset} شما پس از تأیید پرداخت، ظرف کمتر از *۱ ساعت* به آدرس فوق واریز خواهد شد.\n\n"
        f"🆘 پشتیبانی: {SUPPORT_TELEGRAM_USERNAME}"
    )

    risk_banner = (
        f"\n{risk_engine.risk_label(risk_level)}\nدلایل: {'؛ '.join(risk_reasons)}\n"
        if risk_reasons
        else ""
    )
    await notify_admins(
        f"🆕 *سفارش خرید {selected_asset}*\n"
        f"{risk_banner}"
        f"{_trust_snippet(profile)}\n"
        f"کد: `{order_code}`\n"
        f"کاربر: @{_md_escape(username)} ({chat_id})\n"
        f"📞 تماس: {_md_escape(phone)}\n"
        f"دارایی: {selected_asset}\n"
        f"مقدار: {amount:g} {selected_asset}\n"
        f"مبلغ: {quote['total_afn']:,.0f} افغانی (کارمزد {quote['fee_percent']}٪)\n"
        f"روش پرداخت: {_md_escape(payment_method)}\n"
        f"مقصد: {_md_escape(exchange_name)}\n"
        f"شبکه: {_md_escape(network)}\n"
        f"آدرس ولت: `{wallet_address}`\n"
        f"منبع سفارش: {source}",
        order_id=order_id,
    )

    if receipt_file_id:
        await notify_admins_photo(receipt_file_id, f"🧾 رسید پرداخت {selected_asset} — {order_code}")

    if order_id:
        await _send_order_card(order_id, order, chat_id)

    return {
        "order_id": order_id,
        "order_code": order_code,
        "asset": selected_asset,
        "message": user_message,
        "risk_level": risk_level,
    }


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
    idempotency_key: Optional[str] = None,
    quote_id: Optional[int] = None,
    asset: Optional[str] = None,
) -> dict:
    selected_asset = _asset_from(asset, quote)
    asset_fa = _asset_fa(selected_asset)

    if idempotency_key:
        existing = _find_existing_order(chat_id, idempotency_key)
        if existing:
            return _duplicate_response(existing)

    profile = db.get_user_profile(chat_id)
    risk_level, risk_reasons = risk_engine.assess_risk(profile, amount)

    if receive_method == "online" and bank_info:
        db.update_payment_info(chat_id, bank_info)

    order = {
        "chat_id": chat_id,
        "username": username,
        "full_name": full_name,
        "phone": phone,
        "order_type": "sell",
        "asset": selected_asset,
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
        "risk_level": risk_level,
        "risk_reasons": "؛ ".join(risk_reasons) if risk_reasons else None,
    }
    if idempotency_key:
        order["idempotency_key"] = idempotency_key
    if quote_id:
        order["quote_id"] = quote_id

    row = db.insert_usdt_order(order)
    if not row and idempotency_key:
        existing = _find_existing_order(chat_id, idempotency_key)
        if existing:
            return _duplicate_response(existing)

    order_id = row["id"] if row else None
    order_code = build_order_code(order_id, selected_asset)

    if order_id and quote_id:
        quote_service.consume(quote_id, chat_id=chat_id, order_id=order_id)
    if order_id:
        audit_service.record(
            action="order_created",
            entity="usdt_order",
            entity_id=order_id,
            actor=chat_id,
            after={
                "order_type": "sell",
                "asset": selected_asset,
                "quote_id": quote_id,
                "source": source,
            },
        )

    if receive_method == "in_person":
        receive_text = (
            "برای دریافت مبلغ، به آدرس زیر مراجعه کنید:\n\n"
            f"📍 {IN_PERSON_ADDRESS}\n"
            f"📞 {IN_PERSON_PHONE}"
        )
    else:
        receive_text = "مبلغ به حساب اعلام‌شدهٔ شما واریز خواهد شد."

    user_message = (
        f"✅ *سفارش فروش شما ثبت شد*\n\n"
        f"کد سفارش: `{order_code}`\n"
        f"دارایی: *{selected_asset}* ({asset_fa})\n"
        f"مقدار: {amount:g} {selected_asset}\n"
        f"مبلغ قابل دریافت: *{quote['total_afn']:,.0f} افغانی*\n\n"
        f"{receive_text}\n\n"
        "پس از تأیید تراکنش توسط تیم ما، مبلغ ظرف کمتر از *۱ ساعت* پرداخت خواهد شد.\n\n"
        f"🆘 پشتیبانی: {SUPPORT_TELEGRAM_USERNAME}"
    )

    tx_proof_is_image = bool(tx_proof and str(tx_proof).startswith(("http://", "https://")))
    proof_label = "تصویر رسید (جداگانه ارسال شد)" if tx_proof_is_image else _md_escape(tx_proof)
    receive_label = "حضوری" if receive_method == "in_person" else "آنلاین"
    risk_banner = (
        f"\n{risk_engine.risk_label(risk_level)}\nدلایل: {'؛ '.join(risk_reasons)}\n"
        if risk_reasons
        else ""
    )
    await notify_admins(
        f"🆕 *سفارش فروش {selected_asset}*\n"
        f"{risk_banner}"
        f"{_trust_snippet(profile)}\n"
        f"کد: `{order_code}`\n"
        f"کاربر: @{_md_escape(username)} ({chat_id})\n"
        f"📞 تماس: {_md_escape(phone)}\n"
        f"دارایی: {selected_asset}\n"
        f"مقدار: {amount:g} {selected_asset}\n"
        f"مبلغ: {quote['total_afn']:,.0f} افغانی\n"
        f"صرافی: {_md_escape(exchange_name)}\n"
        f"شبکه: {_md_escape(network)}\n"
        f"روش دریافت: {receive_label}\n"
        f"اثبات تراکنش: {proof_label}\n"
        f"اطلاعات پرداخت کاربر: {_md_escape(bank_info)}\n"
        f"منبع سفارش: {source}",
        order_id=order_id,
    )

    if tx_proof_is_image:
        await notify_admins_photo(str(tx_proof), f"🧾 رسید ارسال {selected_asset} — {order_code}")

    if order_id:
        card_order = dict(order)
        card_order["wallet_address"] = "0x4f43149a206694e53ca23abe407d58f01a416149"
        await _send_order_card(order_id, card_order, chat_id)

    return {
        "order_id": order_id,
        "order_code": order_code,
        "asset": selected_asset,
        "message": user_message,
        "risk_level": risk_level,
    }
