"""
Instagram Webhook Subscription Service
======================================

وظیفه این سرویس:

1. بررسی می‌کند Instagram Professional Account
   به Webhookهای اپ subscribe شده یا خیر.

2. بررسی می‌کند field موردنیاز "comments"
   داخل subscribed_fields وجود دارد یا خیر.

3. اگر وجود نداشته باشد، به‌صورت خودکار subscribe می‌کند.

4. بعد از subscribe دوباره وضعیت را verify می‌کند.

این سرویس در startup وب‌سرور Railway اجرا می‌شود.

Authentication:
- Instagram User Access Token
- Instagram Professional User ID
- Instagram API with Instagram Login
"""

import logging
import os
from typing import Any

import httpx

from config import INSTAGRAM_BUSINESS_ACCOUNT_ID


logger = logging.getLogger(__name__)


# ============================================================
# Environment
# ============================================================

INSTAGRAM_USER_ACCESS_TOKEN = os.getenv(
    "INSTAGRAM_USER_ACCESS_TOKEN",
    "",
).strip()


# برای Instagram API with Instagram Login
# بهتر است INSTAGRAM_USER_ID صریحاً در Railway تنظیم شود.
INSTAGRAM_USER_ID = os.getenv(
    "INSTAGRAM_USER_ID",
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
).strip()


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


# متغیر استاندارد جدید:
# INSTAGRAM_SUBSCRIBED_FIELDS
#
# برای سازگاری با Railway فعلی شما،
# subscribed_fields قدیمی هم پشتیبانی می‌شود.
_raw_subscribed_fields = (
    os.getenv("INSTAGRAM_SUBSCRIBED_FIELDS")
    or os.getenv("subscribed_fields")
    or "comments"
)


REQUIRED_FIELDS = tuple(
    field.strip()
    for field in _raw_subscribed_fields.split(",")
    if field.strip()
)


# comments همیشه برای Comment Automation لازم است.
if "comments" not in REQUIRED_FIELDS:
    REQUIRED_FIELDS = (
        *REQUIRED_FIELDS,
        "comments",
    )


_TIMEOUT = 20.0


# ============================================================
# Helpers
# ============================================================

def _headers() -> dict[str, str]:
    """
    Header استاندارد Instagram Graph API.
    """

    return {
        "Authorization": (
            f"Bearer {INSTAGRAM_USER_ACCESS_TOKEN}"
        ),
        "Accept": "application/json",
    }


def _extract_graph_error(
    response: httpx.Response,
) -> str:
    """
    استخراج خطای خوانا از Graph API.
    """

    try:
        payload = response.json()

        if isinstance(payload, dict):
            error = payload.get("error") or {}
        else:
            error = {}

        message = (
            error.get("message")
            or response.text[:500]
            or "Instagram Graph API error"
        )

        parts = [str(message)]

        error_type = error.get("type")

        if error_type:
            parts.append(
                f"type={error_type}"
            )

        code = error.get("code")

        if code is not None:
            parts.append(
                f"code={code}"
            )

        subcode = error.get(
            "error_subcode"
        )

        if subcode is not None:
            parts.append(
                f"subcode={subcode}"
            )

        trace_id = error.get(
            "fbtrace_id"
        )

        if trace_id:
            parts.append(
                f"fbtrace_id={trace_id}"
            )

        return " | ".join(parts)

    except Exception:
        return (
            response.text[:500]
            or "Unknown Instagram Graph API error"
        )


def _extract_subscribed_fields(
    payload: dict[str, Any],
) -> set[str]:
    """
    subscribed_fields را از پاسخ GET /subscribed_apps استخراج می‌کند.

    ساختار response ممکن است بسته به نسخه API کمی متفاوت باشد،
    بنابراین چند حالت را پشتیبانی می‌کنیم.
    """

    result: set[str] = set()

    data = payload.get("data")

    if not isinstance(data, list):
        return result

    for item in data:

        if not isinstance(item, dict):
            continue

        fields = (
            item.get("subscribed_fields")
            or item.get("fields")
            or []
        )

        if isinstance(fields, str):

            fields = [
                value.strip()
                for value in fields.split(",")
                if value.strip()
            ]

        if not isinstance(fields, list):
            continue

        for field in fields:

            if field:
                result.add(
                    str(field).strip()
                )

    return result


def _subscription_url() -> str:
    return (
        f"{GRAPH_BASE}/"
        f"{INSTAGRAM_USER_ID}/"
        f"subscribed_apps"
    )


# ============================================================
# Current subscription
# ============================================================

async def get_subscription_status() -> dict[str, Any]:
    """
    وضعیت واقعی subscription را از Instagram می‌خواند.
    """

    if not INSTAGRAM_USER_ACCESS_TOKEN:

        return {
            "ok": False,
            "configured": False,
            "reason": (
                "INSTAGRAM_USER_ACCESS_TOKEN "
                "تنظیم نشده است."
            ),
            "subscribed_fields": [],
            "required_fields": list(
                REQUIRED_FIELDS
            ),
        }


    if not INSTAGRAM_USER_ID:

        return {
            "ok": False,
            "configured": False,
            "reason": (
                "INSTAGRAM_USER_ID "
                "تنظیم نشده است."
            ),
            "subscribed_fields": [],
            "required_fields": list(
                REQUIRED_FIELDS
            ),
        }


    url = _subscription_url()


    try:

        async with httpx.AsyncClient(
            timeout=_TIMEOUT
        ) as client:

            response = await client.get(
                url,
                headers=_headers(),
            )


        if response.status_code >= 400:

            detail = _extract_graph_error(
                response
            )

            return {
                "ok": False,
                "configured": True,
                "reason": detail,
                "http_status": (
                    response.status_code
                ),
                "subscribed_fields": [],
                "required_fields": list(
                    REQUIRED_FIELDS
                ),
            }


        try:
            payload = response.json()

        except Exception:

            return {
                "ok": False,
                "configured": True,
                "reason": (
                    "Instagram پاسخ JSON "
                    "معتبر برنگرداند."
                ),
                "subscribed_fields": [],
                "required_fields": list(
                    REQUIRED_FIELDS
                ),
            }


        subscribed = (
            _extract_subscribed_fields(
                payload
            )
        )


        return {
            "ok": True,
            "configured": True,
            "reason": "ok",
            "subscribed_fields": sorted(
                subscribed
            ),
            "required_fields": list(
                REQUIRED_FIELDS
            ),
            "missing_fields": sorted(
                set(REQUIRED_FIELDS)
                - subscribed
            ),
        }


    except httpx.TimeoutException:

        logger.exception(
            "Timeout هنگام بررسی "
            "Instagram webhook subscription"
        )

        return {
            "ok": False,
            "configured": True,
            "reason": (
                "Instagram Graph API timeout"
            ),
            "subscribed_fields": [],
            "required_fields": list(
                REQUIRED_FIELDS
            ),
        }


    except Exception as exc:

        logger.exception(
            "خطای غیرمنتظره هنگام بررسی "
            "Instagram webhook subscription"
        )

        return {
            "ok": False,
            "configured": True,
            "reason": (
                f"network error: {exc}"
            ),
            "subscribed_fields": [],
            "required_fields": list(
                REQUIRED_FIELDS
            ),
        }


# ============================================================
# Subscribe
# ============================================================

async def subscribe_webhook_fields(
    fields: list[str] | tuple[str, ...],
) -> tuple[bool, str]:
    """
    اکانت Instagram را به fieldهای موردنیاز subscribe می‌کند.
    """

    if not INSTAGRAM_USER_ACCESS_TOKEN:

        return (
            False,
            "INSTAGRAM_USER_ACCESS_TOKEN تنظیم نشده",
        )


    if not INSTAGRAM_USER_ID:

        return (
            False,
            "INSTAGRAM_USER_ID تنظیم نشده",
        )


    normalized_fields = sorted(
        {
            str(field).strip()
            for field in fields
            if str(field).strip()
        }
    )


    if not normalized_fields:

        return (
            False,
            "هیچ subscribed_field مشخص نشده",
        )


    url = _subscription_url()


    params = {
        "subscribed_fields": (
            ",".join(
                normalized_fields
            )
        )
    }


    try:

        async with httpx.AsyncClient(
            timeout=_TIMEOUT
        ) as client:

            response = await client.post(
                url,
                headers=_headers(),
                params=params,
            )


        if response.status_code >= 400:

            return (
                False,
                _extract_graph_error(
                    response
                ),
            )


        try:
            payload = response.json()

        except Exception:

            payload = {}


        success = payload.get(
            "success"
        )


        # بعضی responseهای Graph API ممکن است
        # بدون success explicit برگردند ولی HTTP 2xx باشند.
        if success is False:

            return (
                False,
                (
                    "Instagram API "
                    "success=false برگرداند"
                ),
            )


        logger.info(
            "Instagram webhook fields "
            "subscribe شدند: %s",
            ",".join(
                normalized_fields
            ),
        )


        return True, "ok"


    except httpx.TimeoutException:

        logger.exception(
            "Timeout هنگام subscribe کردن "
            "Instagram webhook"
        )

        return (
            False,
            "Instagram Graph API timeout",
        )


    except Exception as exc:

        logger.exception(
            "خطای شبکه هنگام subscribe کردن "
            "Instagram webhook"
        )

        return (
            False,
            f"network error: {exc}",
        )


# ============================================================
# Startup auto-fix
# ============================================================

async def ensure_webhook_subscription() -> bool:
    """
    هنگام startup Railway اجرا می‌شود.

    مراحل:

    1. subscription فعلی را می‌خواند.
    2. بررسی می‌کند comments فعال است.
    3. اگر نبود، به‌صورت خودکار subscribe می‌کند.
    4. دوباره وضعیت را verify می‌کند.

    این تابع idempotent است:
    اگر subscription از قبل درست باشد چیزی تغییر نمی‌دهد.
    """

    logger.info(
        "Checking Instagram webhook "
        "subscription..."
    )


    if not INSTAGRAM_USER_ACCESS_TOKEN:

        logger.error(
            "Instagram automation configuration error: "
            "INSTAGRAM_USER_ACCESS_TOKEN "
            "تنظیم نشده است."
        )

        return False


    if not INSTAGRAM_USER_ID:

        logger.error(
            "Instagram automation configuration error: "
            "INSTAGRAM_USER_ID "
            "تنظیم نشده است."
        )

        return False


    logger.info(
        "Instagram webhook account configured "
        "user_id=%s required_fields=%s",
        INSTAGRAM_USER_ID,
        ",".join(
            REQUIRED_FIELDS
        ),
    )


    # --------------------------------------------------------
    # مرحله 1: وضعیت فعلی
    # --------------------------------------------------------

    status = await get_subscription_status()


    if not status.get("ok"):

        logger.error(
            "Unable to read Instagram webhook "
            "subscription: %s",
            status.get(
                "reason",
                "unknown error",
            ),
        )

        return False


    subscribed = set(
        status.get(
            "subscribed_fields",
            [],
        )
    )


    required = set(
        REQUIRED_FIELDS
    )


    missing = (
        required
        - subscribed
    )


    # --------------------------------------------------------
    # از قبل درست است
    # --------------------------------------------------------

    if not missing:

        logger.info(
            "Instagram webhook subscription OK. "
            "subscribed_fields=%s",
            ",".join(
                sorted(subscribed)
            )
            or "unknown",
        )

        return True


    logger.warning(
        "Instagram webhook subscription "
        "missing fields: %s",
        ",".join(
            sorted(missing)
        ),
    )


    # --------------------------------------------------------
    # مرحله 2: subscribe خودکار
    # --------------------------------------------------------

    desired_fields = sorted(
        subscribed
        | required
    )


    ok, detail = (
        await subscribe_webhook_fields(
            desired_fields
        )
    )


    if not ok:

        logger.error(
            "Instagram automatic webhook "
            "subscription FAILED: %s",
            detail,
        )

        return False


    # --------------------------------------------------------
    # مرحله 3: verify
    # --------------------------------------------------------

    verification = (
        await get_subscription_status()
    )


    if not verification.get("ok"):

        logger.error(
            "Instagram subscription created "
            "but verification failed: %s",
            verification.get(
                "reason",
                "unknown error",
            ),
        )

        return False


    verified_fields = set(
        verification.get(
            "subscribed_fields",
            [],
        )
    )


    still_missing = (
        required
        - verified_fields
    )


    if still_missing:

        logger.error(
            "Instagram webhook subscription "
            "verification FAILED. "
            "Still missing: %s",
            ",".join(
                sorted(still_missing)
            ),
        )

        return False


    logger.info(
        "Instagram webhook subscription "
        "successfully verified. "
        "subscribed_fields=%s",
        ",".join(
            sorted(verified_fields)
        ),
    )


    return True