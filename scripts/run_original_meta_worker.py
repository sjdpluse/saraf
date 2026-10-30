"""Consume *verified* Meta webhook envelopes using Saraf's original Python code.

The Supabase Edge receiver verifies Meta signatures before enqueuing.
This worker executes the ORIGINAL Instagram/Facebook handlers unchanged,
including original duplicate protection and existing AI adapters.
It does not store an alternate account ledger or use Railway.
"""
import argparse
import asyncio
import logging
import os

LOGGER = logging.getLogger("saraf.original_meta_worker")


def claim(db):
    result = db.rpc("saraf_claim_original_meta_delivery", {}).execute()
    rows = result.data or []
    return rows[0] if rows else None


def finish(db, delivery_id, succeeded, error=None):
    db.rpc("saraf_finish_original_meta_delivery", {
        "p_id": delivery_id, "p_success": bool(succeeded),
        "p_error": str(error or "")[:150] if not succeeded else None,
    }).execute()


async def process(row):
    from services import (
        instagram_automation_v2,
        facebook_comment_automation,
        social_ai_adapters,
        social_ai_service,
    )
    # Exactly the adapter bindings from original instagram_webhook_router.py.
    instagram_automation_v2._generate_ai_reply = (
        social_ai_adapters.instagram_generate_reply
    )
    instagram_automation_v2._build_trusted_live_data = (
        social_ai_service.build_trusted_live_data
    )
    facebook_comment_automation._generate_ai_reply = (
        social_ai_adapters.facebook_generate_reply
    )

    platform = row["platform"]
    payload = row["payload"]
    if not isinstance(payload, dict):
        raise ValueError("Invalid queued Meta envelope")
    if platform == "facebook" and payload.get("object") == "page":
        await facebook_comment_automation.handle_webhook_payload(payload)
    elif platform == "instagram" and payload.get("object") == "instagram":
        await instagram_automation_v2.handle_webhook_payload(payload)
    else:
        raise ValueError("Unknown queued Meta platform or object")


async def work(max_items):
    from services import supabase_service as db_service

    db = db_service.get_client()
    done = failed = 0
    for _ in range(max_items):
        row = await asyncio.to_thread(claim, db)
        if row is None:
            break
        delivery_id = int(row["delivery_id"])
        try:
            await asyncio.wait_for(process(row), timeout=100)
        except Exception as exc:
            LOGGER.exception(
                "Original Meta handler failed; delivery will retry. Delivery ID=%s",
                delivery_id
            )
            # Do not log raw Meta messages, credentials, sender IDs or PII.
            await asyncio.to_thread(finish, db, delivery_id, False, type(exc).__name__)
            failed += 1
        else:
            await asyncio.to_thread(finish, db, delivery_id, True)
            done += 1
    print(f"Original Meta delivery worker: completed={done} retryable={failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    if os.getenv("SARAF_ORIGINAL_META_WORKER_ENABLED") != "true":
        raise SystemExit("Meta worker disabled; no external post or DM will be sent.")
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        raise SystemExit("Original canonical Supabase config missing.")
    if not 1 <= args.limit <= 30:
        raise SystemExit("Invalid batch size")
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(work(args.limit))
