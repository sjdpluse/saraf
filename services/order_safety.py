"""Safety wrapper for Mini App USDT order creation.

This module deliberately wraps the existing order service instead of replacing it.
It adds database-backed idempotency and records the exact quote used by an order,
while keeping the Telegram bot flow backward compatible.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional

from services import supabase_service as db

_QUOTE_TTL_SECONDS = 10 * 60


def _fingerprint(*, chat_id: int, order_type: str, amount: float, quote: dict, fields: dict) -> str:
    payload = {
        "chat_id": chat_id,
        "order_type": order_type,
        "amount": str(amount),
        "usd_rate": str(quote.get("usd_rate")),
        "fee_percent": str(quote.get("fee_percent", 0)),
        "total_afn": str(quote.get("total_afn")),
        "total_usd": str(quote.get("total_usd")),
        "fields": fields,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_existing(chat_id: int, idempotency_key: str) -> Optional[dict]:
    try:
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
    except Exception:
        return None


def _create_quote(chat_id: int, order_type: str, amount: float, quote: dict) -> Optional[int]:
    try:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=_QUOTE_TTL_SECONDS)
        res = (
            db.get_client()
            .table("usdt_quotes")
            .insert(
                {
                    "chat_id": chat_id,
                    "order_type": order_type,
                    "usdt_amount": amount,
                    "usd_rate": quote["usd_rate"],
                    "fee_percent": quote.get("fee_percent", 0),
                    "total_afn": quote["total_afn"],
                    "total_usd": quote["total_usd"],
                    "status": "active",
                    "expires_at": expires_at.isoformat(),
                }
            )
            .execute()
        )
        return res.data[0]["id"] if res.data else None
    except Exception:
        return None


def _bind_order(order_id: int, quote_id: Optional[int], idempotency_key: str) -> None:
    fields = {"idempotency_key": idempotency_key}
    if quote_id:
        fields["quote_id"] = quote_id
    try:
        db.get_client().table("usdt_orders").update(fields).eq("id", order_id).execute()
    except Exception:
        # The order itself already exists. Do not make a successful financial
        # operation look failed solely because audit metadata could not be attached.
        pass


def _consume_quote(quote_id: Optional[int]) -> None:
    if not quote_id:
        return
    try:
        db.get_client().table("usdt_quotes").update(
            {
                "status": "consumed",
                "consumed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", quote_id).eq("status", "active").execute()
    except Exception:
        pass


def install() -> None:
    """Wrap Mini App order creation once at package-import time."""
    from services import usdt_order_service as service

    if getattr(service, "_order_safety_installed", False):
        return

    original_buy = service.create_buy_order
    original_sell = service.create_sell_order

    @wraps(original_buy)
    async def safe_buy_order(*, chat_id: int, username, full_name, phone, amount, quote,
                             payment_method, exchange_name, network, wallet_address,
                             receipt_file_id=None, source="bot"):
        if source != "miniapp":
            return await original_buy(
                chat_id=chat_id, username=username, full_name=full_name, phone=phone,
                amount=amount, quote=quote, payment_method=payment_method,
                exchange_name=exchange_name, network=network, wallet_address=wallet_address,
                receipt_file_id=receipt_file_id, source=source,
            )

        key = _fingerprint(
            chat_id=chat_id, order_type="buy", amount=amount, quote=quote,
            fields={
                "payment_method": payment_method,
                "exchange_name": exchange_name,
                "network": network,
                "wallet_address": wallet_address,
                "receipt_file_id": receipt_file_id,
            },
        )
        existing = _get_existing(chat_id, key)
        if existing:
            return {
                "order_id": existing["id"],
                "order_code": service.build_order_code(existing["id"]),
                "message": "سفارش قبلی شما برای همین درخواست موجود است.",
                "risk_level": existing.get("risk_level"),
            }

        quote_id = _create_quote(chat_id, "buy", amount, quote)
        result = await original_buy(
            chat_id=chat_id, username=username, full_name=full_name, phone=phone,
            amount=amount, quote=quote, payment_method=payment_method,
            exchange_name=exchange_name, network=network, wallet_address=wallet_address,
            receipt_file_id=receipt_file_id, source=source,
        )
        if result.get("order_id"):
            _bind_order(result["order_id"], quote_id, key)
            _consume_quote(quote_id)
            return result

        existing = _get_existing(chat_id, key)
        if existing:
            return {
                "order_id": existing["id"],
                "order_code": service.build_order_code(existing["id"]),
                "message": "سفارش شما قبلاً ثبت شده است.",
                "risk_level": existing.get("risk_level"),
            }
        return result

    @wraps(original_sell)
    async def safe_sell_order(*, chat_id: int, username, full_name, phone, amount, quote,
                              exchange_name, network, tx_proof, receive_method,
                              bank_info=None, source="bot"):
        if source != "miniapp":
            return await original_sell(
                chat_id=chat_id, username=username, full_name=full_name, phone=phone,
                amount=amount, quote=quote, exchange_name=exchange_name, network=network,
                tx_proof=tx_proof, receive_method=receive_method, bank_info=bank_info,
                source=source,
            )

        key = _fingerprint(
            chat_id=chat_id, order_type="sell", amount=amount, quote=quote,
            fields={
                "exchange_name": exchange_name,
                "network": network,
                "tx_proof": tx_proof,
                "receive_method": receive_method,
                "bank_info": bank_info,
            },
        )
        existing = _get_existing(chat_id, key)
        if existing:
            return {
                "order_id": existing["id"],
                "order_code": service.build_order_code(existing["id"]),
                "message": "سفارش قبلی شما برای همین درخواست موجود است.",
                "risk_level": existing.get("risk_level"),
            }

        quote_id = _create_quote(chat_id, "sell", amount, quote)
        result = await original_sell(
            chat_id=chat_id, username=username, full_name=full_name, phone=phone,
            amount=amount, quote=quote, exchange_name=exchange_name, network=network,
            tx_proof=tx_proof, receive_method=receive_method, bank_info=bank_info,
            source=source,
        )
        if result.get("order_id"):
            _bind_order(result["order_id"], quote_id, key)
            _consume_quote(quote_id)
            return result

        existing = _get_existing(chat_id, key)
        if existing:
            return {
                "order_id": existing["id"],
                "order_code": service.build_order_code(existing["id"]),
                "message": "سفارش شما قبلاً ثبت شده است.",
                "risk_level": existing.get("risk_level"),
            }
        return result

    service.create_buy_order = safe_buy_order
    service.create_sell_order = safe_sell_order
    service._order_safety_installed = True
