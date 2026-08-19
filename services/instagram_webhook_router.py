"""
Instagram webhook router for Saraf Automation V2.

GET  /webhooks/instagram -> Meta verification handshake
POST /webhooks/instagram -> comments + direct-message events

The POST endpoint returns 200 quickly and performs API/AI work in FastAPI
BackgroundTasks so Meta does not consider the webhook slow.

The Facebook Page webhook router is included here as a sibling router so api.py
can keep a single social-webhook include point.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from config import INSTAGRAM_WEBHOOK_VERIFY_TOKEN
from services import (
    facebook_comment_automation,
    facebook_webhook_router,
    instagram_automation_v2,
    social_ai_adapters,
    social_ai_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()
router.include_router(facebook_webhook_router.router)

# Swap only the AI/live-data layer. Existing Meta webhook, deduplication,
# conversation-memory, and reply transport logic remain unchanged.
instagram_automation_v2._generate_ai_reply = social_ai_adapters.instagram_generate_reply
instagram_automation_v2._build_trusted_live_data = social_ai_service.build_trusted_live_data
facebook_comment_automation._generate_ai_reply = social_ai_adapters.facebook_generate_reply


@router.get("/webhooks/instagram")
async def verify_instagram_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if (
        mode == "subscribe"
        and token
        and INSTAGRAM_WEBHOOK_VERIFY_TOKEN
        and token == INSTAGRAM_WEBHOOK_VERIFY_TOKEN
    ):
        return PlainTextResponse(challenge or "")

    logger.warning("Instagram webhook verification rejected.")
    raise HTTPException(status_code=403, detail="verify token mismatch")


@router.post("/webhooks/instagram")
async def receive_instagram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=None, alias="X-Hub-Signature-256"),
):
    raw_body = await request.body()

    if not instagram_automation_v2.verify_webhook_signature(
        raw_body,
        x_hub_signature_256,
    ):
        logger.warning("Instagram webhook signature invalid; request rejected.")
        raise HTTPException(status_code=403, detail="invalid signature")

    try:
        payload = await request.json()
    except Exception:
        logger.exception("Instagram webhook JSON invalid.")
        return JSONResponse({"status": "ignored"})

    background_tasks.add_task(
        instagram_automation_v2.handle_webhook_payload,
        payload,
    )
    return JSONResponse({"status": "received"})
