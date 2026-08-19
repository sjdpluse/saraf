"""
Instagram webhook router for صراف Automation V2.

GET  /webhooks/instagram -> Meta verification handshake
POST /webhooks/instagram -> comments + direct-message events

The POST endpoint returns 200 quickly and performs API/AI work in FastAPI
BackgroundTasks so Meta does not consider the webhook slow.
"""

import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from config import INSTAGRAM_APP_SECRET, INSTAGRAM_WEBHOOK_VERIFY_TOKEN
from services import instagram_automation_v2

logger = logging.getLogger(__name__)
router = APIRouter()


def _escape_unicode_for_meta_signature(raw_body: bytes) -> bytes:
    """
    Return the payload with non-ASCII Unicode code points escaped using
    lowercase JSON-style \uXXXX sequences while preserving every ASCII byte
    exactly as received.

    Meta documents that some Event Notification signatures are generated from
    an escaped-unicode representation of the payload. The normal raw-body HMAC
    remains the primary validation path; this representation is only a secure
    compatibility fallback.
    """
    text = raw_body.decode("utf-8")
    escaped: list[str] = []

    for char in text:
        codepoint = ord(char)

        if codepoint <= 0x7F:
            escaped.append(char)
            continue

        if codepoint <= 0xFFFF:
            escaped.append(f"\\u{codepoint:04x}")
            continue

        # JSON represents code points above U+FFFF as a UTF-16 surrogate pair.
        value = codepoint - 0x10000
        high = 0xD800 + (value >> 10)
        low = 0xDC00 + (value & 0x3FF)
        escaped.append(f"\\u{high:04x}\\u{low:04x}")

    return "".join(escaped).encode("utf-8")


def _verify_instagram_signature(
    raw_body: bytes,
    signature_header: Optional[str],
) -> tuple[bool, str]:
    """
    Validate X-Hub-Signature-256 without weakening webhook security.

    Validation order:
    1. HMAC-SHA256 over the exact raw request body (standard path).
    2. HMAC-SHA256 over Meta's documented escaped-Unicode representation.

    Both paths use the same configured Instagram App Secret and constant-time
    comparison. Requests that match neither representation are rejected.
    """
    if not INSTAGRAM_APP_SECRET:
        logger.error("INSTAGRAM_APP_SECRET تنظیم نشده؛ Webhook رد شد.")
        return False, "missing_app_secret"

    if not signature_header or not signature_header.startswith("sha256="):
        return False, "missing_or_invalid_header"

    provided = signature_header.split("=", 1)[1].strip().lower()
    if not provided:
        return False, "empty_signature"

    secret = INSTAGRAM_APP_SECRET.encode("utf-8")

    expected_raw = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected_raw, provided):
        return True, "raw"

    try:
        escaped_body = _escape_unicode_for_meta_signature(raw_body)
    except UnicodeDecodeError:
        return False, "invalid_utf8"

    # No need to compute the same digest twice for ASCII-only payloads.
    if escaped_body != raw_body:
        expected_escaped = hmac.new(
            secret,
            escaped_body,
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(expected_escaped, provided):
            return True, "escaped_unicode"

    return False, "signature_mismatch"


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

    signature_valid, signature_mode = _verify_instagram_signature(
        raw_body,
        x_hub_signature_256,
    )

    if not signature_valid:
        logger.warning(
            "Instagram webhook signature invalid; request rejected. reason=%s",
            signature_mode,
        )
        raise HTTPException(status_code=403, detail="invalid signature")

    if signature_mode == "escaped_unicode":
        logger.info("Instagram webhook signature validated via escaped-unicode compatibility path.")

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
