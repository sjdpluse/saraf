import asyncio
import logging
import os
from datetime import datetime, timezone

from services import audit_service, supabase_service as db
from services import remittance_service
from services.remittance_chain_verifier import verify_order

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("remittance_watcher")

POLL_SECONDS = max(15, int(os.getenv("REMITTANCE_WATCH_INTERVAL_SECONDS", "30")))
BATCH_SIZE = max(1, min(100, int(os.getenv("REMITTANCE_WATCH_BATCH_SIZE", "25"))))


def _pending_orders():
    result = (
        db.get_client()
        .table("remittance_orders")
        .select("*")
        .eq("status", "transfer_submitted")
        .not_.is_("tx_hash", "null")
        .order("chain_last_checked_at", desc=False, nullsfirst=True)
        .limit(BATCH_SIZE)
        .execute()
    )
    return result.data or []


async def _mark_verified(order: dict, update: dict):
    now = datetime.now(timezone.utc).isoformat()
    fields = {
        **update,
        "chain_last_checked_at": now,
        "chain_verified_at": now,
        "status": "payout_ready",
        "crypto_confirmed_at": now,
        "crypto_confirmed_by": None,
        "admin_note": "Blockchain verified automatically",
    }
    result = (
        db.get_client()
        .table("remittance_orders")
        .update(fields)
        .eq("id", order["id"])
        .eq("status", "transfer_submitted")
        .execute()
    )
    if not result.data:
        return
    db.get_client().table("remittance_status_history").insert({
        "order_id": order["id"],
        "from_status": "transfer_submitted",
        "to_status": "payout_ready",
        "changed_by": None,
        "note": "Blockchain verified automatically",
    }).execute()
    audit_service.record(
        action="remittance_blockchain_verified",
        entity="remittance",
        entity_id=order["id"],
        actor=None,
    )
    updated = result.data[0]
    await remittance_service.notify_customer(updated)
    await remittance_service.notify_admins(updated)
    logger.info("Verified remittance %s tx=%s", order["id"], order.get("tx_hash"))


def _mark_checked(order: dict, update: dict):
    update = dict(update)
    update["chain_last_checked_at"] = datetime.now(timezone.utc).isoformat()
    (
        db.get_client()
        .table("remittance_orders")
        .update(update)
        .eq("id", order["id"])
        .eq("status", "transfer_submitted")
        .execute()
    )


async def check_once():
    for order in _pending_orders():
        result = await asyncio.to_thread(verify_order, order)
        update = result.as_update(asset=order["asset"], network=order["network"])
        if result.status == "verified":
            await _mark_verified(order, update)
        else:
            await asyncio.to_thread(_mark_checked, order, update)
            if result.status in {"mismatch", "failed", "unsupported"}:
                logger.warning(
                    "Remittance %s verification=%s error=%s",
                    order["id"], result.status, result.error,
                )


async def main():
    logger.info("Remittance watcher started interval=%ss batch=%s", POLL_SECONDS, BATCH_SIZE)
    while True:
        try:
            await check_once()
        except Exception:
            logger.exception("Watcher iteration failed")
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
