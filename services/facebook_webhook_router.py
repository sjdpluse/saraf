"""Facebook Page webhook router for صراف comment automation."""

import logging
import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from services import facebook_comment_automation

logger = logging.getLogger(__name__)
router = APIRouter()

FACEBOOK_WEBHOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN", "").strip()


@router.get("/webhooks/facebook")
async def verify_facebook_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if (
        mode == "subscribe"
        and token
        and FACEBOOK_WEBHOOK_VERIFY_TOKEN
        and token == FACEBOOK_WEBHOOK_VERIFY_TOKEN
    ):
        return PlainTextResponse(challenge or "")

    logger.warning("Facebook webhook verification rejected.")
    raise HTTPException(status_code=403, detail="verify token mismatch")


@router.post("/webhooks/facebook")
async def receive_facebook_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=None, alias="X-Hub-Signature-256"),
):
    raw_body = await request.body()

    if not facebook_comment_automation.verify_webhook_signature(
        raw_body,
        x_hub_signature_256,
    ):
        logger.warning("Facebook webhook signature invalid; request rejected.")
        raise HTTPException(status_code=403, detail="invalid signature")

    try:
        payload = await request.json()
    except Exception:
        logger.exception("Facebook webhook JSON invalid.")
        return JSONResponse({"status": "ignored"})

    background_tasks.add_task(
        facebook_comment_automation.handle_webhook_payload,
        payload,
    )
    return JSONResponse({"status": "received"})
