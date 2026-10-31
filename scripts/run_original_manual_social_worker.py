"""Original Saraf admin '📢 نشر پست' without Railway.

Only processes signed+idempotent requests from the original Admin Mini App.
The actual publication remains services.facebook_service and
services.instagram_service (same Python, captions, graphics, pricing, Meta API).
A failed/timeout Graph request is NEVER blindly retried: it may have posted.
"""
import argparse
import asyncio
import logging
import os

LOGGER = logging.getLogger("saraf.original_manual_social")


def assert_ready(environment=None):
    env = os.environ if environment is None else environment
    required = {
        "SARAF_ORIGINAL_SOCIAL_PUBLISH_ENABLED",
        "SARAF_ORIGINAL_CUTOVER_APPROVED",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "FACEBOOK_PAGE_ID",
        "FACEBOOK_PAGE_ACCESS_TOKEN",
        "INSTAGRAM_BUSINESS_ACCOUNT_ID",
    }
    missing = sorted(key for key in required if not env.get(key))
    if missing:
        raise RuntimeError("MISSING_REQUIRED_ORIGINAL_SOCIAL_CONFIG:" + ",".join(missing))
    if env["SARAF_ORIGINAL_SOCIAL_PUBLISH_ENABLED"] != "true" or (
        env["SARAF_ORIGINAL_CUTOVER_APPROVED"] != "true"
    ):
        raise RuntimeError("ORIGINAL_SOCIAL_PUBLICATION_NOT_ENABLED")


def claim(db):
    rows = db.rpc("saraf_original_claim_manual_social", {}).execute().data or []
    return rows[0] if rows else None


def finish(db, request_id, facebook_state, instagram_state, detail=""):
    res = db.rpc("saraf_original_finish_manual_social", {
        "p_id": request_id,
        "p_facebook": facebook_state,
        "p_instagram": instagram_state,
        "p_error": detail[:150],
    }).execute()
    if not res.data:
        raise RuntimeError("ORIGINAL_SOCIAL_QUEUE_FINISH_FAILED")


def classify(result):
    # Only explicit success is 'posted'. Any HTTP timeout or API exception can
    # have been accepted by Meta, so a failed result is NOT auto-retryable.
    if isinstance(result, BaseException):
        return "unknown"
    if isinstance(result, tuple) and len(result) == 2:
        return "posted" if result[0] is True else "unknown"
    return "unknown"


async def publish_original_pair():
    from jobs import get_current_quotes_and_metals
    from services import facebook_service, instagram_service

    quotes, gold, silver = await get_current_quotes_and_metals()
    if not quotes or not gold:
        return "failed", "failed", "ORIGINAL_RATES_UNAVAILABLE"

    # Original handlers/admin.py manual_post calls these two exact services
    # concurrently with force=True. No rewritten captions/pricing/publishing.
    facebook, instagram = await asyncio.gather(
        facebook_service.check_and_maybe_post(
            quotes, gold, silver, force=True
        ),
        instagram_service.check_and_maybe_post(
            quotes, gold, silver, force=True
        ),
        return_exceptions=True,
    )
    return classify(facebook), classify(instagram), "ORIGINAL_META_POST_DISPATCHED"


async def run_once():
    from services import supabase_service as db_service

    db = db_service.get_client()
    request = await asyncio.to_thread(claim, db)
    if not request:
        print("Original manual social queue empty.")
        return
    req_id = int(request["request_id"])
    facebook = instagram = "unknown"
    detail = "ORIGINAL_POST_OUTCOME_UNCERTAIN"
    try:
        facebook, instagram, detail = await asyncio.wait_for(
            publish_original_pair(), timeout=180,
        )
    except Exception:
        # Do not print Meta IDs, raw exceptions, or customer data.
        LOGGER.exception("Original manual publication returned uncertain state")
    finally:
        await asyncio.to_thread(finish, db, req_id, facebook, instagram, detail)
    print("Original manual social publication finalized:", facebook, instagram)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", required=True)
    args = parser.parse_args()
    assert_ready()
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(run_once())
