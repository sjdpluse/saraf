"""
Instagram Comment Automation — Saraf
====================================

Flow:

Instagram
    ↓
Meta Webhook
    ↓
/webhooks/instagram
    ↓
handle_webhook_payload()
    ↓
_process_comment()
    ├── Keyword → Instagram Private Reply
    └── AI → Instagram Public Reply


IMPORTANT

Comment Automation از:

    Instagram API with Instagram Login

استفاده می‌کند.

بنابراین:

    Host:
        graph.instagram.com

    Token:
        INSTAGRAM_USER_ACCESS_TOKEN

و نباید برای DM / Comment Reply از Facebook Page Access Token
استفاده شود.
"""

import hashlib
import hmac
import logging
from typing import Optional

import httpx

from config import (
    INSTAGRAM_AI_REPLY_ENABLED,
    INSTAGRAM_APP_SECRET,
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    INSTAGRAM_BUSINESS_USERNAME,
    INSTAGRAM_COMMENT_KEYWORDS,
    INSTAGRAM_DM_LINK_MESSAGE,
    INSTAGRAM_GRAPH_API_VERSION,
    INSTAGRAM_USER_ACCESS_TOKEN,
    INSTAGRAM_USER_ID,
    OPENROUTER_API_KEY,
    OPENROUTER_FALLBACK_MODELS,
    OPENROUTER_MODEL,
    OPENROUTER_SYSTEM_PROMPT,
    TELEGRAM_BOT_LINK,
)

from services import (
    supabase_service as db,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# Instagram API
# ============================================================

GRAPH_BASE = (
    f"https://graph.instagram.com/"
    f"{INSTAGRAM_GRAPH_API_VERSION}"
)


# ============================================================
# OpenRouter
# ============================================================

OPENROUTER_URL = (
    "https://openrouter.ai/"
    "api/v1/chat/completions"
)


_TIMEOUT = 20.0

_AI_REPLY_MAX_CHARS = 400


# ============================================================
# Webhook Signature
# ============================================================

def verify_webhook_signature(
    raw_body: bytes,
    signature_header: Optional[str],
) -> bool:
    """
    Verify Meta X-Hub-Signature-256.
    """

    if not INSTAGRAM_APP_SECRET:
        logger.error(
            "INSTAGRAM_APP_SECRET تنظیم نشده؛ "
            "Webhook رد شد."
        )
        return False

    if not signature_header:
        logger.warning(
            "Instagram Webhook بدون "
            "X-Hub-Signature-256 دریافت شد."
        )
        return False

    if not signature_header.startswith(
        "sha256="
    ):
        logger.warning(
            "فرمت Instagram Webhook "
            "signature نامعتبر است."
        )
        return False

    expected = hmac.new(
        INSTAGRAM_APP_SECRET.encode(
            "utf-8"
        ),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    provided = (
        signature_header
        .split("=", 1)[1]
    )

    valid = hmac.compare_digest(
        expected,
        provided,
    )

    if not valid:
        logger.warning(
            "امضای Instagram Webhook "
            "معتبر نیست."
        )

    return valid


# ============================================================
# Webhook payload
# ============================================================

async def handle_webhook_payload(
    payload: dict,
) -> None:
    """
    Instagram comment webhook processor.

    هر دو شکل payload را پشتیبانی می‌کند:

    1)
        entry.field
        entry.value

    2)
        entry.changes[].field
        entry.changes[].value
    """

    if payload.get("object") != "instagram":
        logger.info(
            "Instagram webhook ignored "
            "object=%s",
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
            "Instagram webhook entry "
            "ساختار نامعتبر دارد."
        )
        return

    logger.info(
        "Instagram webhook payload "
        "received entries=%s",
        len(entries),
    )

    processed_in_payload: set[str] = set()

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
        # Format 1
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
        # Format 2
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
                "Instagram webhook entry "
                "بدون comment event بود. "
                "keys=%s",
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
                    in processed_in_payload
                ):
                    logger.info(
                        "Duplicate comment در همان "
                        "payload نادیده گرفته شد "
                        "comment_id=%s",
                        comment_id_str,
                    )
                    continue

                processed_in_payload.add(
                    comment_id_str
                )

            logger.info(
                "Instagram webhook event "
                "field=%s comment_id=%s",
                field,
                comment_id or "unknown",
            )

            try:
                await _process_comment(
                    value
                )

            except Exception:
                logger.exception(
                    "خطای غیرمنتظره در پردازش "
                    "Instagram comment "
                    "comment_id=%s",
                    comment_id or "unknown",
                )


# ============================================================
# Process Comment
# ============================================================

async def _process_comment(
    value: dict,
) -> None:
    comment_id = value.get(
        "id"
    )

    if not comment_id:
        logger.warning(
            "Instagram comment بدون id "
            "دریافت شد."
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
    )

    username = (
        from_user.get("username")
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
    )

    logger.info(
        "Instagram comment received "
        "comment_id=%s media_id=%s "
        "username=%s",
        comment_id,
        media_id or "unknown",
        username or "unknown",
    )

    # ========================================================
    # Prevent loop
    # ========================================================

    own_ids = {
        str(value)
        for value in (
            INSTAGRAM_USER_ID,
            INSTAGRAM_BUSINESS_ACCOUNT_ID,
        )
        if value
    }

    if (
        from_id
        and str(from_id)
        in own_ids
    ):
        logger.info(
            "کامنت خود اکانت Saraf "
            "نادیده گرفته شد "
            "comment_id=%s",
            comment_id,
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
            "نادیده گرفته شد "
            "comment_id=%s",
            comment_id,
        )
        return

    # ========================================================
    # Idempotency
    # ========================================================

    claimed = (
        db.try_claim_ig_comment_event(
            comment_id,
            str(media_id)
            if media_id
            else None,
            username or None,
            text,
        )
    )

    if not claimed:
        logger.info(
            "Instagram comment قبلاً "
            "پردازش شده است "
            "comment_id=%s",
            comment_id,
        )
        return

    dm_sent = False
    ai_replied = False

    # ========================================================
    # Keyword → Private Reply
    # ========================================================

    if _matches_keyword(
        text
    ):
        logger.info(
            "Instagram keyword detected "
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
                    "Instagram Private Reply "
                    "ارسال شد "
                    "comment_id=%s",
                    comment_id,
                )

            else:
                logger.warning(
                    "Instagram Private Reply "
                    "ناموفق بود "
                    "comment_id=%s reason=%s",
                    comment_id,
                    detail,
                )

        except Exception:
            logger.exception(
                "خطا در Private Reply "
                "comment_id=%s",
                comment_id,
            )

    # ========================================================
    # AI → Public Comment Reply
    # ========================================================

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
                        "Instagram AI public reply "
                        "ارسال شد "
                        "comment_id=%s",
                        comment_id,
                    )

                else:
                    logger.warning(
                        "Instagram AI public reply "
                        "ناموفق بود "
                        "comment_id=%s reason=%s",
                        comment_id,
                        detail,
                    )

            else:
                logger.warning(
                    "AI response ساخته نشد "
                    "comment_id=%s",
                    comment_id,
                )

        except Exception:
            logger.exception(
                "خطا در AI public reply "
                "comment_id=%s",
                comment_id,
            )

    # ========================================================
    # Save result
    # ========================================================

    db.mark_ig_comment_event(
        comment_id,
        dm_sent=dm_sent,
        ai_replied=ai_replied,
    )


# ============================================================
# Keyword Match
# ============================================================

def _matches_keyword(
    text: str,
) -> bool:
    if not text:
        return False

    if not INSTAGRAM_COMMENT_KEYWORDS:
        return False

    lowered = (
        text.lower()
    )

    return any(
        keyword.lower()
        in lowered
        for keyword
        in INSTAGRAM_COMMENT_KEYWORDS
    )


# ============================================================
# Instagram API helpers
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
        "Accept": (
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
            str(message)
        ]

        if error.get(
            "type"
        ):
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

        if error.get(
            "fbtrace_id"
        ):
            parts.append(
                "fbtrace_id="
                f"{error['fbtrace_id']}"
            )

        return " | ".join(
            parts
        )

    except Exception:
        return (
            response.text
            or "Unknown Instagram API response"
        )[:300]


# ============================================================
# Instagram Private Reply
# ============================================================

async def _send_private_reply(
    comment_id: str,
    text: str,
) -> tuple[bool, str]:
    """
    Instagram API with Instagram Login

    POST:
    graph.instagram.com/{version}/{ig_user_id}/messages

    Authentication:
    Instagram User Access Token
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
            response = (
                await client.post(
                    url,
                    headers=(
                        _instagram_headers()
                    ),
                    json=body,
                )
            )

        if (
            response.status_code
            >= 400
        ):
            return (
                False,
                _extract_graph_error(
                    response
                ),
            )

        try:
            data = (
                response.json()
            )
        except Exception:
            data = {}

        recipient_id = (
            data.get(
                "recipient_id"
            )
        )

        message_id = (
            data.get(
                "message_id"
            )
        )

        logger.info(
            "Instagram Private Reply API "
            "success recipient_id=%s "
            "message_id=%s",
            recipient_id,
            message_id,
        )

        return (
            True,
            "ok",
        )

    except httpx.TimeoutException:
        logger.exception(
            "Instagram Private Reply timeout"
        )

        return (
            False,
            "Instagram API timeout",
        )

    except Exception as exc:
        logger.exception(
            "Instagram Private Reply "
            "network error"
        )

        return (
            False,
            f"network error: {exc}",
        )


# ============================================================
# Instagram Public Reply
# ============================================================

async def _reply_to_comment_publicly(
    comment_id: str,
    text: str,
) -> tuple[bool, str]:
    """
    Instagram API with Instagram Login

    POST:
    graph.instagram.com/{version}/{comment_id}/replies
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
            response = (
                await client.post(
                    url,
                    headers=(
                        _instagram_headers()
                    ),
                    json=body,
                )
            )

        if (
            response.status_code
            >= 400
        ):
            return (
                False,
                _extract_graph_error(
                    response
                ),
            )

        try:
            data = (
                response.json()
            )
        except Exception:
            data = {}

        reply_id = (
            data.get("id")
        )

        logger.info(
            "Instagram Public Reply API "
            "success reply_id=%s",
            reply_id,
        )

        return (
            True,
            "ok",
        )

    except httpx.TimeoutException:
        logger.exception(
            "Instagram Public Reply timeout"
        )

        return (
            False,
            "Instagram API timeout",
        )

    except Exception as exc:
        logger.exception(
            "Instagram Public Reply "
            "network error"
        )

        return (
            False,
            f"network error: {exc}",
        )


# ============================================================
# OpenRouter
# ============================================================

def _openrouter_models() -> list[str]:
    """
    مدل اصلی + fallbackها.

    Duplicateها حذف می‌شوند ولی ترتیب حفظ می‌شود.
    """

    models: list[str] = []

    for model in (
        [
            OPENROUTER_MODEL,
            *OPENROUTER_FALLBACK_MODELS,
        ]
    ):
        model = (
            model
            or ""
        ).strip()

        if (
            model
            and model
            not in models
        ):
            models.append(
                model
            )

    # محافظ نهایی
    if not models:
        models.append(
            "openrouter/free"
        )

    return models


async def _generate_ai_reply(
    comment_text: str,
    username: Optional[str],
) -> Optional[str]:
    """
    OpenRouter با Multi-model fallback.

    اگر مدل اصلی rate-limit/down شود،
    OpenRouter مدل بعدی را خودکار امتحان می‌کند.
    """

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

    models = (
        _openrouter_models()
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
            "https://t.me/sarafiaf_bot"
        ),
        "X-Title": (
            "Saraf Instagram Auto Reply"
        ),
    }

    body = {
        # مهم:
        # به‌جای model از models استفاده می‌کنیم
        # تا fallback رسمی OpenRouter فعال شود.
        "models": models,

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
            response = (
                await client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=body,
                )
            )

        if (
            response.status_code
            >= 400
        ):
            retry_after = (
                response.headers.get(
                    "Retry-After"
                )
            )

            logger.error(
                "OpenRouter error "
                "HTTP=%s retry_after=%s "
                "models=%s body=%s",
                response.status_code,
                retry_after,
                models,
                response.text[:300],
            )

            return None

        data = (
            response.json()
        )

        choices = (
            data.get("choices")
            or []
        )

        if not choices:
            logger.warning(
                "OpenRouter response "
                "choices خالی است."
            )
            return None

        first_choice = (
            choices[0]
        )

        if not isinstance(
            first_choice,
            dict,
        ):
            return None

        message = (
            first_choice
            .get("message")
            or {}
        )

        if not isinstance(
            message,
            dict,
        ):
            return None

        content = (
            message.get("content")
            or ""
        )

        reply = str(
            content
        ).strip()

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
                ]
                .rstrip()
                + "…"
            )

        selected_model = (
            data.get("model")
            or "unknown"
        )

        logger.info(
            "OpenRouter AI reply generated "
            "model=%s",
            selected_model,
        )

        return reply

    except httpx.TimeoutException:
        logger.exception(
            "OpenRouter timeout"
        )

        return None

    except Exception:
        logger.exception(
            "خطا در OpenRouter AI Reply"
        )

        return None