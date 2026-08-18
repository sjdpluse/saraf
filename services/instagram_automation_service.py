"""
Instagram Comment Automation for Saraf
======================================

این سرویس processor مشترک Instagram Comment Automation است.

ورودی می‌تواند از دو مسیر باشد:

1. Webhook رسمی Meta
2. Polling رسمی Instagram Graph API

رفتار:
- Keyword -> Private Reply / DM
- AI Enabled -> Public Reply
- هر comment_id فقط یک بار پردازش می‌شود.

Authentication:
- Instagram User Access Token
- graph.instagram.com
"""

import hashlib
import hmac
import logging
import os
from typing import Optional

import httpx

from config import (
    INSTAGRAM_APP_SECRET,
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    INSTAGRAM_COMMENT_KEYWORDS,
    INSTAGRAM_DM_LINK_MESSAGE,
    INSTAGRAM_AI_REPLY_ENABLED,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_SYSTEM_PROMPT,
    TELEGRAM_BOT_LINK,
)

from services import instagram_comment_store


logger = logging.getLogger(__name__)


# ============================================================
# Instagram API with Instagram Login
# ============================================================

INSTAGRAM_USER_ACCESS_TOKEN = os.getenv(
    "INSTAGRAM_USER_ACCESS_TOKEN",
    "",
).strip()


INSTAGRAM_USER_ID = os.getenv(
    "INSTAGRAM_USER_ID",
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
).strip()


INSTAGRAM_BUSINESS_USERNAME = os.getenv(
    "INSTAGRAM_BUSINESS_USERNAME",
    "",
).strip().lstrip("@").lower()


INSTAGRAM_GRAPH_API_VERSION = os.getenv(
    "INSTAGRAM_GRAPH_API_VERSION",
    "v24.0",
).strip()

if not INSTAGRAM_GRAPH_API_VERSION.startswith("v"):
    INSTAGRAM_GRAPH_API_VERSION = (
        f"v{INSTAGRAM_GRAPH_API_VERSION}"
    )


GRAPH_BASE = (
    f"https://graph.instagram.com/"
    f"{INSTAGRAM_GRAPH_API_VERSION}"
)


# ============================================================
# OpenRouter
# ============================================================

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

_TIMEOUT = 20.0

_AI_REPLY_MAX_CHARS = 400


# ============================================================
# Webhook signature verification
# ============================================================

def verify_webhook_signature(
    raw_body: bytes,
    signature_header: Optional[str],
) -> bool:
    """
    تایید X-Hub-Signature-256.

    فقط مسیر Webhook از این تابع استفاده می‌کند.
    Polling نیازی به Webhook signature ندارد.
    """

    if not INSTAGRAM_APP_SECRET:
        logger.error(
            "INSTAGRAM_APP_SECRET تنظیم نشده؛ "
            "Webhook به دلیل امنیتی رد شد."
        )
        return False

    if not signature_header:
        logger.warning(
            "Webhook بدون X-Hub-Signature-256 دریافت شد."
        )
        return False

    if not signature_header.startswith(
        "sha256="
    ):
        logger.warning(
            "فرمت X-Hub-Signature-256 نامعتبر است."
        )
        return False

    expected = hmac.new(
        INSTAGRAM_APP_SECRET.encode(
            "utf-8"
        ),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    provided = signature_header.split(
        "=",
        1,
    )[1]

    valid = hmac.compare_digest(
        expected,
        provided,
    )

    if not valid:
        logger.warning(
            "امضای Webhook Instagram معتبر نیست."
        )

    return valid


# ============================================================
# Main webhook handler
# ============================================================

async def handle_webhook_payload(
    payload: dict,
) -> None:
    """
    پردازش Instagram Webhook.

    پشتیبانی از:

    FORMAT 1:
        entry.field
        entry.value

    FORMAT 2:
        entry.changes[].field
        entry.changes[].value
    """

    if payload.get("object") != "instagram":
        logger.warning(
            "Instagram webhook ignored: object=%s",
            payload.get("object"),
        )
        return

    entries = (
        payload.get("entry")
        or []
    )

    if not isinstance(
        entries,
        list,
    ):
        logger.warning(
            "Instagram webhook invalid "
            "entry type=%s",
            type(entries).__name__,
        )
        return

    logger.info(
        "Instagram webhook payload received "
        "entries=%s",
        len(entries),
    )

    processed_comment_ids: set[str] = set()

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            continue

        events: list[
            tuple[str, dict]
        ] = []

        # ----------------------------------------------------
        # FORMAT 1
        # ----------------------------------------------------

        direct_field = entry.get(
            "field"
        )

        direct_value = entry.get(
            "value"
        )

        if (
            direct_field
            in (
                "comments",
                "live_comments",
            )
            and isinstance(
                direct_value,
                dict,
            )
        ):
            events.append(
                (
                    direct_field,
                    direct_value,
                )
            )

        # ----------------------------------------------------
        # FORMAT 2
        # ----------------------------------------------------

        changes = (
            entry.get("changes")
            or []
        )

        if isinstance(
            changes,
            list,
        ):
            for change in changes:
                if not isinstance(
                    change,
                    dict,
                ):
                    continue

                field = change.get(
                    "field"
                )

                value = (
                    change.get("value")
                    or {}
                )

                if field not in (
                    "comments",
                    "live_comments",
                ):
                    continue

                if not isinstance(
                    value,
                    dict,
                ):
                    continue

                events.append(
                    (
                        field,
                        value,
                    )
                )

        if not events:
            logger.info(
                "Instagram webhook entry ignored "
                "field=%s keys=%s",
                direct_field,
                sorted(
                    entry.keys()
                ),
            )
            continue

        for field, value in events:
            comment_id = value.get(
                "id"
            )

            if comment_id:
                comment_id_str = str(
                    comment_id
                )

                if (
                    comment_id_str
                    in processed_comment_ids
                ):
                    logger.info(
                        "Duplicate comment inside "
                        "same webhook ignored "
                        "comment_id=%s",
                        comment_id_str,
                    )
                    continue

                processed_comment_ids.add(
                    comment_id_str
                )

            logger.info(
                "Instagram webhook event "
                "field=%s comment_id=%s",
                field,
                comment_id or "unknown",
            )

            try:
                await process_comment(
                    value,
                    source="webhook",
                )

            except Exception:
                logger.exception(
                    "خطای غیرمنتظره هنگام "
                    "پردازش Instagram comment "
                    "field=%s comment_id=%s",
                    field,
                    comment_id or "unknown",
                )


# ============================================================
# Process one comment
# ============================================================

async def process_comment(
    value: dict,
    *,
    source: str = "webhook",
) -> None:
    """
    Processor مشترک بین Webhook و Polling.
    """

    comment_id = value.get(
        "id"
    )

    if not comment_id:
        logger.warning(
            "Instagram comment بدون "
            "comment_id دریافت شد."
        )
        return

    comment_id = str(
        comment_id
    )

    text = (
        value.get("text")
        or ""
    ).strip()

    from_user = (
        value.get("from")
        or {}
    )

    if not isinstance(
        from_user,
        dict,
    ):
        from_user = {}

    from_id = (
        from_user.get("id")
        or value.get("from_id")
    )

    username = (
        from_user.get("username")
        or value.get("username")
        or ""
    )

    username = str(
        username
    ).strip()

    media = (
        value.get("media")
        or {}
    )

    if not isinstance(
        media,
        dict,
    ):
        media = {}

    media_id = (
        media.get("id")
        or value.get("media_id")
    )

    comment_timestamp = value.get(
        "timestamp"
    )

    logger.info(
        "Instagram comment received "
        "source=%s comment_id=%s "
        "media_id=%s username=%s",
        source,
        comment_id,
        media_id or "unknown",
        username or "unknown",
    )

    # ========================================================
    # Prevent loop
    # ========================================================

    own_ids = {
        str(x)
        for x in (
            INSTAGRAM_USER_ID,
            INSTAGRAM_BUSINESS_ACCOUNT_ID,
        )
        if x
    }

    if (
        from_id
        and str(from_id)
        in own_ids
    ):
        logger.info(
            "کامنت خود اکانت Saraf "
            "نادیده گرفته شد."
        )
        return

    if (
        INSTAGRAM_BUSINESS_USERNAME
        and username
        and username.lower()
        == INSTAGRAM_BUSINESS_USERNAME
    ):
        logger.info(
            "کامنت username خود Saraf "
            "نادیده گرفته شد."
        )
        return

    # ========================================================
    # Idempotency
    # ========================================================

    claimed = (
        instagram_comment_store
        .claim_comment(
            comment_id,
            media_id=(
                str(media_id)
                if media_id
                else None
            ),
            commenter_id=(
                str(from_id)
                if from_id
                else None
            ),
            username=(
                username
                or None
            ),
            text=text,
            comment_timestamp=(
                str(comment_timestamp)
                if comment_timestamp
                else None
            ),
            source=source,
        )
    )

    if not claimed:
        return

    # ========================================================
    # Keyword -> Private Reply
    # ========================================================

    dm_sent = False

    if _matches_keyword(
        text
    ):
        logger.info(
            "Keyword detected "
            "comment_id=%s",
            comment_id,
        )

        try:
            dm_text = (
                INSTAGRAM_DM_LINK_MESSAGE
                .format(
                    bot_link=(
                        TELEGRAM_BOT_LINK
                    )
                )
            )

            ok, detail = (
                await _send_private_reply(
                    comment_id=comment_id,
                    text=dm_text,
                )
            )

            dm_sent = ok

            if ok:
                logger.info(
                    "Private Reply ارسال شد "
                    "comment_id=%s",
                    comment_id,
                )

            else:
                logger.warning(
                    "Private Reply ناموفق بود "
                    "comment_id=%s reason=%s",
                    comment_id,
                    detail,
                )

        except Exception:
            logger.exception(
                "خطا در مسیر Private Reply "
                "comment_id=%s",
                comment_id,
            )

    # ========================================================
    # AI -> Public Reply
    # ========================================================

    ai_replied = False

    if (
        INSTAGRAM_AI_REPLY_ENABLED
        and text
    ):
        try:
            ai_text = (
                await _generate_ai_reply(
                    comment_text=text,
                    username=(
                        username
                        or None
                    ),
                )
            )

            if ai_text:
                ok, detail = (
                    await _reply_to_comment_publicly(
                        comment_id=comment_id,
                        text=ai_text,
                    )
                )

                ai_replied = ok

                if ok:
                    logger.info(
                        "AI public reply ارسال شد "
                        "comment_id=%s",
                        comment_id,
                    )

                else:
                    logger.warning(
                        "AI public reply ناموفق بود "
                        "comment_id=%s reason=%s",
                        comment_id,
                        detail,
                    )

            else:
                logger.warning(
                    "OpenRouter پاسخی تولید نکرد "
                    "comment_id=%s",
                    comment_id,
                )

        except Exception:
            logger.exception(
                "خطا در مسیر AI Reply "
                "comment_id=%s",
                comment_id,
            )

    # ========================================================
    # Store result
    # ========================================================

    instagram_comment_store.mark_comment(
        comment_id,
        dm_sent=dm_sent,
        ai_replied=ai_replied,
    )


# ============================================================
# Keyword matching
# ============================================================

def _matches_keyword(
    text: str,
) -> bool:
    if not text:
        return False

    if not INSTAGRAM_COMMENT_KEYWORDS:
        return False

    lowered = text.lower()

    return any(
        keyword.lower()
        in lowered
        for keyword
        in INSTAGRAM_COMMENT_KEYWORDS
    )


# ============================================================
# Instagram Graph helpers
# ============================================================

def _instagram_headers() -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer "
            f"{INSTAGRAM_USER_ACCESS_TOKEN}"
        ),
        "Content-Type": (
            "application/json"
        ),
    }


def _extract_graph_error(
    response: httpx.Response,
) -> str:
    try:
        payload = (
            response.json()
        )

        if isinstance(
            payload,
            dict,
        ):
            error = (
                payload.get("error")
                or {}
            )
        else:
            error = {}

        message = (
            error.get("message")
            or response.text[:300]
            or "Instagram API error"
        )

        parts = [
            message
        ]

        if error.get("type"):
            parts.append(
                f"type={error['type']}"
            )

        if (
            error.get("code")
            is not None
        ):
            parts.append(
                f"code={error['code']}"
            )

        if (
            error.get(
                "error_subcode"
            )
            is not None
        ):
            parts.append(
                "subcode="
                f"{error['error_subcode']}"
            )

        return " | ".join(
            str(part)
            for part in parts
        )

    except Exception:
        return (
            response.text
            or "پاسخ نامشخص Instagram API"
        )[:300]


# ============================================================
# Private Reply
# ============================================================

async def _send_private_reply(
    comment_id: str,
    text: str,
) -> tuple[bool, str]:
    """
    Private Reply به commenter.

    POST
    /{IG_USER_ID}/messages
    """

    if not INSTAGRAM_USER_ACCESS_TOKEN:
        return (
            False,
            "INSTAGRAM_USER_ACCESS_TOKEN "
            "تنظیم نشده",
        )

    if not INSTAGRAM_USER_ID:
        return (
            False,
            "INSTAGRAM_USER_ID "
            "تنظیم نشده",
        )

    url = (
        f"{GRAPH_BASE}/"
        f"{INSTAGRAM_USER_ID}/messages"
    )

    body = {
        "recipient": {
            "comment_id": (
                comment_id
            ),
        },
        "message": {
            "text": text,
        },
    }

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT
        ) as client:
            response = await client.post(
                url,
                headers=(
                    _instagram_headers()
                ),
                json=body,
            )

        if response.status_code >= 400:
            return (
                False,
                _extract_graph_error(
                    response
                ),
            )

        try:
            data = response.json()
        except Exception:
            data = {}

        message_id = data.get(
            "message_id"
        )

        recipient_id = data.get(
            "recipient_id"
        )

        logger.info(
            "Instagram Private Reply success "
            "recipient_id=%s message_id=%s",
            recipient_id,
            message_id,
        )

        return True, "ok"

    except httpx.TimeoutException:
        logger.exception(
            "Timeout هنگام ارسال "
            "Instagram Private Reply"
        )

        return (
            False,
            "Instagram API timeout",
        )

    except Exception as exc:
        logger.exception(
            "خطای شبکه هنگام ارسال "
            "Instagram Private Reply"
        )

        return (
            False,
            f"network error: {exc}",
        )


# ============================================================
# Public Reply
# ============================================================

async def _reply_to_comment_publicly(
    comment_id: str,
    text: str,
) -> tuple[bool, str]:
    """
    پاسخ عمومی زیر comment.

    POST
    /{COMMENT_ID}/replies
    """

    if not INSTAGRAM_USER_ACCESS_TOKEN:
        return (
            False,
            "INSTAGRAM_USER_ACCESS_TOKEN "
            "تنظیم نشده",
        )

    url = (
        f"{GRAPH_BASE}/"
        f"{comment_id}/replies"
    )

    body = {
        "message": text,
    }

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT
        ) as client:
            response = await client.post(
                url,
                headers=(
                    _instagram_headers()
                ),
                json=body,
            )

        if response.status_code >= 400:
            return (
                False,
                _extract_graph_error(
                    response
                ),
            )

        try:
            data = response.json()

            reply_id = data.get(
                "id"
            )

        except Exception:
            reply_id = None

        logger.info(
            "Instagram public reply success "
            "reply_id=%s",
            reply_id,
        )

        return True, "ok"

    except httpx.TimeoutException:
        logger.exception(
            "Timeout هنگام ارسال "
            "Instagram public reply"
        )

        return (
            False,
            "Instagram API timeout",
        )

    except Exception as exc:
        logger.exception(
            "خطای شبکه هنگام ارسال "
            "Instagram public reply"
        )

        return (
            False,
            f"network error: {exc}",
        )


# ============================================================
# OpenRouter AI
# ============================================================

async def _generate_ai_reply(
    comment_text: str,
    username: Optional[str],
) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        logger.warning(
            "OPENROUTER_API_KEY تنظیم نشده؛ "
            "AI Reply غیرفعال است."
        )

        return None

    if username:
        user_message = (
            f"@{username} این کامنت را "
            f"در صفحه Saraf گذاشته است:\n"
            f"{comment_text}"
        )

    else:
        user_message = (
            comment_text
        )

    headers = {
        "Authorization": (
            f"Bearer "
            f"{OPENROUTER_API_KEY}"
        ),
        "Content-Type": (
            "application/json"
        ),
        "HTTP-Referer": (
            "https://saraf.example.com"
        ),
        "X-Title": (
            "Saraf Instagram Auto Reply"
        ),
    }

    body = {
        "model": (
            OPENROUTER_MODEL
        ),
        "messages": [
            {
                "role": "system",
                "content": (
                    OPENROUTER_SYSTEM_PROMPT
                ),
            },
            {
                "role": "user",
                "content": (
                    user_message
                ),
            },
        ],
        "max_tokens": 150,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT
        ) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=headers,
                json=body,
            )

        if response.status_code >= 400:
            logger.error(
                "OpenRouter error HTTP %s: %s",
                response.status_code,
                response.text[:300],
            )

            return None

        data = response.json()

        choices = data.get(
            "choices",
            [],
        )

        if not choices:
            logger.warning(
                "OpenRouter choices خالی است."
            )

            return None

        message = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        reply = (
            message.strip()
        )

        if not reply:
            return None

        if (
            len(reply)
            > _AI_REPLY_MAX_CHARS
        ):
            reply = (
                reply[
                    : _AI_REPLY_MAX_CHARS
                    - 1
                ].rstrip()
                + "…"
            )

        return reply

    except httpx.TimeoutException:
        logger.exception(
            "OpenRouter timeout"
        )

        return None

    except Exception:
        logger.exception(
            "خطا در فراخوانی OpenRouter"
        )

        return None