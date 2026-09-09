import logging
import secrets
from decimal import Decimal
from typing import Optional

from telegram import Bot

from config import (
    ADMIN_CHAT_IDS,
    ADMIN_BOT_TOKEN,
    BOT_TOKEN,
    SUPPORT_TELEGRAM_USERNAME,
    USDT_KYC_DOCS_BUCKET,
)
from services import audit_service, rate_engine, supabase_service as db, usdt_service
from services.money import D, quantize_afn, quantize_percent, quantize_rate, to_float

logger = logging.getLogger(__name__)

SUPPORTED_NETWORKS = {
    "USDT": ("TRC20", "BEP20", "ERC20"),
    "USDC": ("BEP20", "ERC20"),
}

_admin_bot: Optional[Bot] = None
_customer_bot: Optional[Bot] = None


def _admin() -> Bot:
    global _admin_bot
    if _admin_bot is None:
        if not ADMIN_BOT_TOKEN:
            raise RuntimeError("ADMIN_BOT_TOKEN تنظیم نشده است.")
        _admin_bot = Bot(token=ADMIN_BOT_TOKEN)
    return _admin_bot


def _customer() -> Bot:
    global _customer_bot
    if _customer_bot is None:
        if not BOT_TOKEN:
            raise RuntimeError("BOT_TOKEN تنظیم نشده است.")
        _customer_bot = Bot(token=BOT_TOKEN)
    return _customer_bot


def _deposit_wallet(asset: str, network: str) -> str:
    from config import USDT_DEPOSIT_WALLETS

    selected_asset = usdt_service.normalize_asset(asset)
    selected_network = str(network or "").upper()
    if selected_network not in SUPPORTED_NETWORKS[selected_asset]:
        raise ValueError("شبکهٔ انتخاب‌شده برای این دارایی پشتیبانی نمی‌شود.")
    wallet = (USDT_DEPOSIT_WALLETS or {}).get(selected_network)
    if not wallet:
        raise ValueError(f"آدرس دریافت {selected_asset} روی شبکهٔ {selected_network} هنوز تنظیم نشده است.")
    return wallet


def _pickup_code() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def remittance_code(order_id: int) -> str:
    return f"REM-{int(order_id):06d}"


def _validate_text(value: str, label: str, min_len: int = 2, max_len: int = 120) -> str:
    cleaned = str(value or "").strip()
    if len(cleaned) < min_len or len(cleaned) > max_len:
        raise ValueError(f"{label} معتبر نیست.")
    return cleaned


async def quote(*, amount: float, asset: str, network: str, fee_percent: float = 0.0) -> dict:
    selected_asset = usdt_service.normalize_asset(asset)
    usdt_service.validate_amount(amount, selected_asset)
    wallet = _deposit_wallet(selected_asset, network)

    local = await rate_engine.get_full_quote("usd")
    usd_buy_rate = D(local["saraf_quote"]["buy"])
    amount_d = D(amount)
    fee_pct = max(D(fee_percent), Decimal("0"))
    gross_afn = amount_d * usd_buy_rate
    fee_afn = gross_afn * fee_pct / D(100)
    payout_afn = max(gross_afn - fee_afn, Decimal("0"))

    return {
        "asset": selected_asset,
        "network": str(network).upper(),
        "crypto_amount": to_float(amount_d),
        "usd_rate": to_float(quantize_rate(usd_buy_rate)),
        "gross_afn": to_float(quantize_afn(gross_afn)),
        "fee_percent": to_float(quantize_percent(fee_pct)),
        "fee_afn": to_float(quantize_afn(fee_afn)),
        "payout_afn": to_float(quantize_afn(payout_afn)),
        "deposit_wallet": wallet,
        "basis": local["saraf_quote"]["basis"],
    }


def _existing(chat_id: int, idempotency_key: str) -> Optional[dict]:
    res = (
        db.get_client()
        .table("remittance_orders")
        .select("*")
        .eq("chat_id", chat_id)
        .eq("idempotency_key", idempotency_key)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


async def create_order(
    *,
    chat_id: int,
    sender_name: str,
    sender_phone: Optional[str],
    sender_country: str,
    beneficiary_full_name: str,
    beneficiary_phone: str,
    beneficiary_province: str,
    beneficiary_city: str,
    beneficiary_address: str,
    beneficiary_id_document_path: str,
    amount: float,
    asset: str,
    network: str,
    idempotency_key: str,
    fee_percent: float = 0.0,
) -> dict:
    if not idempotency_key or len(idempotency_key) > 120:
        raise ValueError("شناسهٔ درخواست معتبر نیست.")

    duplicate = _existing(chat_id, idempotency_key)
    if duplicate:
        return {"duplicate": True, **duplicate, "order_code": remittance_code(duplicate["id"])}

    q = await quote(amount=amount, asset=asset, network=network, fee_percent=fee_percent)
    row = {
        "chat_id": chat_id,
        "idempotency_key": idempotency_key,
        "sender_country": _validate_text(sender_country, "کشور فرستنده"),
        "sender_name": _validate_text(sender_name, "نام کامل فرستنده", 3, 160),
        "sender_phone": (sender_phone or "").strip() or None,
        "beneficiary_full_name": _validate_text(beneficiary_full_name, "نام کامل گیرنده", 3, 160),
        "beneficiary_phone": _validate_text(beneficiary_phone, "شماره تماس گیرنده", 7, 40),
        "beneficiary_province": _validate_text(beneficiary_province, "ولایت گیرنده"),
        "beneficiary_city": _validate_text(beneficiary_city, "شهر گیرنده"),
        "beneficiary_address": _validate_text(beneficiary_address, "آدرس گیرنده", 3, 300),
        "beneficiary_id_document_path": _validate_text(beneficiary_id_document_path, "تذکره گیرنده", 10, 500),
        "relationship": None,
        "purpose": None,
        "asset": q["asset"],
        "network": q["network"],
        "crypto_amount": q["crypto_amount"],
        "usd_rate": q["usd_rate"],
        "gross_afn": q["gross_afn"],
        "fee_percent": q["fee_percent"],
        "fee_afn": q["fee_afn"],
        "payout_afn": q["payout_afn"],
        "deposit_wallet": q["deposit_wallet"],
        "pickup_code": _pickup_code(),
        "status": "awaiting_transfer",
    }
    result = db.get_client().table("remittance_orders").insert(row).execute()
    if not result.data:
        raise RuntimeError("ثبت حواله ناموفق بود.")
    order = result.data[0]
    db.get_client().table("remittance_status_history").insert({
        "order_id": order["id"],
        "from_status": None,
        "to_status": "awaiting_transfer",
        "changed_by": chat_id,
        "note": "Order created; waiting for blockchain transfer",
    }).execute()
    audit_service.record(action="remittance_created", entity="remittance", entity_id=order["id"], actor=chat_id)
    # The admin is intentionally not notified here. The request becomes operational
    # only after the sender submits a transaction hash.
    return {**order, "order_code": remittance_code(order["id"]), "duplicate": False}


async def submit_tx_hash(*, chat_id: int, order_id: int, tx_hash: str) -> dict:
    cleaned = str(tx_hash or "").strip()
    if len(cleaned) < 12 or len(cleaned) > 200:
        raise ValueError("Tx Hash / Transaction ID معتبر نیست.")
    current = get_order(order_id)
    if not current or int(current["chat_id"]) != int(chat_id):
        raise LookupError("حواله یافت نشد.")
    if current["status"] not in ("awaiting_transfer", "transfer_submitted"):
        raise ValueError("این حواله دیگر در مرحلهٔ ثبت تراکنش نیست.")

    result = (
        db.get_client()
        .table("remittance_orders")
        .update({"tx_hash": cleaned, "status": "transfer_submitted", "verification_status": "pending"})
        .eq("id", order_id)
        .eq("chat_id", chat_id)
        .execute()
    )
    if not result.data:
        raise RuntimeError("ثبت Tx Hash ناموفق بود.")
    db.get_client().table("remittance_status_history").insert({
        "order_id": order_id,
        "from_status": current["status"],
        "to_status": "transfer_submitted",
        "changed_by": chat_id,
        "note": "Tx Hash submitted by sender; sent to admin and blockchain watcher",
    }).execute()
    audit_service.record(action="remittance_tx_submitted", entity="remittance", entity_id=order_id, actor=chat_id)
    await notify_admins(result.data[0], event="tx_submitted")
    return {**result.data[0], "order_code": remittance_code(order_id)}


def get_order(order_id: int) -> Optional[dict]:
    res = db.get_client().table("remittance_orders").select("*").eq("id", int(order_id)).limit(1).execute()
    return res.data[0] if res.data else None


def get_my_orders(chat_id: int) -> list[dict]:
    res = (
        db.get_client()
        .table("remittance_orders")
        .select("*")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return [{**row, "order_code": remittance_code(row["id"])} for row in (res.data or [])]


async def transition(order_id: int, to_status: str, *, admin_id: int, note: Optional[str] = None) -> dict:
    allowed = {
        "transfer_submitted": {"payout_ready", "on_hold", "cancelled"},
        "on_hold": {"payout_ready", "cancelled"},
        "payout_ready": {"completed", "on_hold"},
    }
    current = get_order(order_id)
    if not current:
        raise LookupError("حواله یافت نشد.")
    if to_status not in allowed.get(current["status"], set()):
        raise ValueError("تغییر وضعیت حواله مجاز نیست.")

    fields = {"status": to_status, "admin_note": (note or "").strip() or current.get("admin_note")}
    if to_status == "payout_ready":
        fields.update({"crypto_confirmed_by": admin_id, "crypto_confirmed_at": "now()"})
    elif to_status == "completed":
        fields.update({"paid_by": admin_id, "paid_at": "now()"})

    from datetime import datetime, timezone
    if "crypto_confirmed_at" in fields:
        fields["crypto_confirmed_at"] = datetime.now(timezone.utc).isoformat()
    if "paid_at" in fields:
        fields["paid_at"] = datetime.now(timezone.utc).isoformat()

    result = db.get_client().table("remittance_orders").update(fields).eq("id", order_id).eq("status", current["status"]).execute()
    if not result.data:
        raise RuntimeError("وضعیت حواله تغییر نکرد؛ ممکن است همزمان توسط مدیر دیگری تغییر کرده باشد.")
    db.get_client().table("remittance_status_history").insert({
        "order_id": order_id,
        "from_status": current["status"],
        "to_status": to_status,
        "changed_by": admin_id,
        "note": note,
    }).execute()
    audit_service.record(action=f"remittance_{to_status}", entity="remittance", entity_id=order_id, actor=admin_id)
    updated = result.data[0]
    await notify_customer(updated)
    return {**updated, "order_code": remittance_code(order_id)}


async def notify_admins(order: dict, event: Optional[str] = None) -> None:
    if not ADMIN_CHAT_IDS:
        return
    status = str(order.get("status") or "")
    if event is None:
        event = "payout_ready" if status == "payout_ready" else "status_update"

    title = {
        "tx_submitted": "🔎 حواله جدید — تراکنش ثبت شد",
        "payout_ready": "✅ بلاکچین تایید شد — آماده پرداخت",
    }.get(event, "🌍 به‌روزرسانی حواله")

    code = remittance_code(order["id"])
    tx_line = f"\nTx Hash: {order.get('tx_hash')}" if order.get("tx_hash") else ""
    verification_line = ""
    if order.get("verification_status"):
        verification_line = f"\nتایید بلاکچین: {order.get('verification_status')}"
        if order.get("chain_confirmations") is not None:
            verification_line += f" — {order.get('chain_confirmations')} confirmations"

    text = (
        f"{title}\n\n"
        f"کد حواله: {code}\n"
        f"فرستنده: {order.get('sender_name') or '—'}\n"
        f"کشور فرستنده: {order.get('sender_country') or '—'}\n"
        f"دارایی: {order.get('crypto_amount')} {order.get('asset')}\n"
        f"شبکه: {order.get('network')}\n"
        f"گیرنده: {order.get('beneficiary_full_name') or '—'}\n"
        f"شماره تماس: {order.get('beneficiary_phone') or '—'}\n"
        f"موقعیت: {order.get('beneficiary_province') or '—'} / {order.get('beneficiary_city') or '—'}\n"
        f"آدرس: {order.get('beneficiary_address') or '—'}\n"
        f"مبلغ قابل پرداخت: {float(order.get('payout_afn') or 0):,.0f} AFN\n"
        f"کارمزد خدمت: {float(order.get('fee_percent') or 0):g}%\n"
        f"وضعیت: {status}"
        f"{verification_line}{tx_line}"
    )

    try:
        bot = _admin()
        from keyboards import admin_remittance_keyboard
        markup = admin_remittance_keyboard(order["id"], status)
        document_bytes = None
        if event == "tx_submitted" and order.get("beneficiary_id_document_path"):
            document_bytes = db.download_private_file(USDT_KYC_DOCS_BUCKET, order["beneficiary_id_document_path"])
        for admin_id in ADMIN_CHAT_IDS:
            if document_bytes:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=document_bytes,
                    caption=f"🪪 تذکره گیرنده — {order.get('beneficiary_full_name') or code}",
                )
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=markup)
    except Exception:
        logger.exception("ارسال اعلان حواله به مدیر ناموفق بود")


async def notify_customer(order: dict) -> None:
    code = remittance_code(order["id"])
    status = order["status"]
    if status == "payout_ready":
        text = (
            f"✅ حوالهٔ شما ({code}) آمادهٔ پرداخت در افغانستان است.\n\n"
            f"گیرنده: {order['beneficiary_full_name']}\n"
            f"مبلغ قابل دریافت: {float(order['payout_afn']):,.0f} افغانی\n"
            f"کد دریافت: {order['pickup_code']}\n\n"
            "کد دریافت را فقط با گیرنده شریک کنید. گیرنده هنگام دریافت باید تذکره همراه داشته باشد."
        )
    elif status == "completed":
        text = f"✅ حوالهٔ شما ({code}) با موفقیت به گیرنده پرداخت و تکمیل شد."
    elif status == "on_hold":
        text = f"⏸ حوالهٔ شما ({code}) برای بررسی بیشتر موقتاً متوقف شده است. برای پیگیری: {SUPPORT_TELEGRAM_USERNAME}"
    elif status == "cancelled":
        text = f"❌ حوالهٔ شما ({code}) لغو شد. برای جزئیات با پشتیبانی تماس بگیرید: {SUPPORT_TELEGRAM_USERNAME}"
    else:
        return
    try:
        await _customer().send_message(chat_id=order["chat_id"], text=text)
    except Exception:
        logger.exception("ارسال وضعیت حواله به مشتری ناموفق بود")
