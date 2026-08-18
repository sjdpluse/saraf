"""
Instagram Comment Polling Service
=================================

Fallback رسمی برای زمانی که Meta App هنوز Published نشده و
رویداد comments از Webhook production دریافت نمی‌شود.

روش کار:

1. فهرست آخرین Mediaهای Instagram Professional Account را می‌گیرد.
2. comments_count هر Media را بررسی می‌کند.
3. فقط Mediaهایی را که تغییر کرده‌اند scan می‌کند.
4. هر چند دقیقه یک Full Re-scan سبک انجام می‌دهد تا edge caseهایی مانند
   delete + new comment با count یکسان از دست نروند.
5. کامنت‌های جدید را به instagram_automation_service.process_comment
   تحویل می‌دهد.
6. همان idempotency مشترک Webhook/Polling استفاده می‌شود.

این Polling از API رسمی Instagram استفاده می‌کند و Scraping نیست.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from services import instagram_automation_service as automation


logger = logging.getLogger(__name__)


# ============================================================
# Environment
# ============================================================

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(
        name,
        "true" if default else "false",
    ).strip().lower()

    return raw in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_int(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(name, str(default)).strip()

    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default

    return max(
        minimum,
        min(maximum, value),
    )


# عمداً پیش‌فرض False است تا بعد از deploy ناخواسته شروع به پاسخ دادن نکند.
POLLING_ENABLED = _env_bool(
    "INSTAGRAM_COMMENT_POLLING_ENABLED",
    False,
)

# فاصله Polling
POLL_INTERVAL_SECONDS = _env_int(
    "INSTAGRAM_COMMENT_POLL_INTERVAL_SECONDS",
    30,
    15,
    3600,
)

# چند پست/Reel اخیر بررسی شوند
MEDIA_LIMIT = _env_int(
    "INSTAGRAM_COMMENT_POLL_MEDIA_LIMIT",
    10,
    1,
    50,
)

# تعداد comment در هر page
COMMENTS_LIMIT = _env_int(
    "INSTAGRAM_COMMENT_POLL_COMMENTS_LIMIT",
    100,
    10,
    100,
)

# حداکثر چند صفحه از کامنت‌ها برای یک media scan شود
MAX_COMMENT_PAGES = _env_int(
    "INSTAGRAM_COMMENT_POLL_MAX_PAGES",
    3,
    1,
    10,
)

# فقط کامنت‌هایی که از این مقدار جدیدترند پردازش شوند.
#
# 900 = پانزده دقیقه.
# این محافظ باعث می‌شود در اولین Deploy ناگهان صدها کامنت قدیمی جواب نگیرند.
LOOKBACK_SECONDS = _env_int(
    "INSTAGRAM_COMMENT_POLL_LOOKBACK_SECONDS",
    900,
    60,
    604800,
)

# حتی اگر comments_count تغییر نکرد، هر چند وقت یک‌بار دوباره scan شود.
FORCE_RESCAN_SECONDS = _env_int(
    "INSTAGRAM_COMMENT_POLL_FORCE_RESCAN_SECONDS",
    300,
    60,
    3600,
)


_TIMEOUT = 20.0


# ============================================================
# Runtime state
# ============================================================

_poll_lock = asyncio.Lock()

_initialized = False

_last_comment_counts: dict[str, Optional[int]] = {}

_last_force_rescan_monotonic = 0.0


# ============================================================
# Helpers
# ============================================================

def _headers() -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer "
            f"{automation.INSTAGRAM_USER_ACCESS_TOKEN}"
        ),
        "Accept": "application/json",
    }


def _extract_graph_error(
    response: httpx.Response,
) -> str:
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

        if error.get("type"):
            parts.append(
                f"type={error['type']}"
            )

        if error.get("code") is not None:
            parts.append(
                f"code={error['code']}"
            )

        if error.get("error_subcode") is not None:
            parts.append(
                f"subcode={error['error_subcode']}"
            )

        if error.get("fbtrace_id"):
            parts.append(
                f"fbtrace_id={error['fbtrace_id']}"
            )

        return " | ".join(parts)

    except Exception:
        return (
            response.text[:500]
            or "Unknown Instagram Graph API error"
        )


def _parse_timestamp(
    value: Optional[str],
) -> Optional[datetime]:
    if not value:
        return None

    raw = str(value).strip()

    if not raw:
        return None

    try:
        # 2026-08-18T10:20:30Z
        if raw.endswith("Z"):
            raw = (
                raw[:-1]
                + "+00:00"
            )

        dt = datetime.fromisoformat(raw)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:
        logger.warning(
            "Instagram comment timestamp "
            "قابل parse نبود: %s",
            value,
        )
        return None


def _is_recent_comment(
    comment: dict,
    cutoff: datetime,
) -> bool:
    timestamp = _parse_timestamp(
        comment.get("timestamp")
    )

    # اگر timestamp وجود نداشت، comment را از دست نمی‌دهیم.
    if timestamp is None:
        return True

    return timestamp >= cutoff


def _comment_sort_key(
    comment: dict,
) -> datetime:
    timestamp = _parse_timestamp(
        comment.get("timestamp")
    )

    return (
        timestamp
        or datetime.min.replace(
            tzinfo=timezone.utc
        )
    )


def _read_comment_count(
    media: dict,
) -> Optional[int]:
    raw = media.get(
        "comments_count"
    )

    if raw is None:
        return None

    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ============================================================
# Instagram API
# ============================================================

async def _fetch_media_snapshot(
    client: httpx.AsyncClient,
) -> list[dict]:
    """
    آخرین mediaهای Instagram Professional Account را می‌خواند.
    """

    url = (
        f"{automation.GRAPH_BASE}/"
        f"{automation.INSTAGRAM_USER_ID}/media"
    )

    params = {
        "fields": (
            "id,"
            "timestamp,"
            "comments_count,"
            "media_product_type"
        ),
        "limit": MEDIA_LIMIT,
    }

    response = await client.get(
        url,
        headers=_headers(),
        params=params,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            "Instagram media polling failed: "
            + _extract_graph_error(
                response
            )
        )

    payload = response.json()

    data = payload.get("data") or []

    if not isinstance(data, list):
        raise RuntimeError(
            "Instagram /media پاسخ data معتبر ندارد."
        )

    return [
        item
        for item in data
        if isinstance(item, dict)
        and item.get("id")
    ]


async def _fetch_comments(
    client: httpx.AsyncClient,
    media_id: str,
) -> list[dict]:
    """
    چند page از comments یک media را می‌گیرد.
    """

    url = (
        f"{automation.GRAPH_BASE}/"
        f"{media_id}/comments"
    )

    params: dict[str, object] = {
        "fields": (
            "from,"
            "text,"
            "timestamp"
        ),
        "limit": COMMENTS_LIMIT,
    }

    all_comments: list[dict] = []

    for _page in range(
        MAX_COMMENT_PAGES
    ):
        response = await client.get(
            url,
            headers=_headers(),
            params=params,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Instagram comments polling failed "
                f"media_id={media_id}: "
                + _extract_graph_error(
                    response
                )
            )

        payload = response.json()

        data = payload.get("data") or []

        if isinstance(data, list):
            all_comments.extend(
                item
                for item in data
                if isinstance(item, dict)
                and item.get("id")
            )

        paging = (
            payload.get("paging")
            or {}
        )

        cursors = (
            paging.get("cursors")
            or {}
        )

        after = cursors.get(
            "after"
        )

        next_url = paging.get(
            "next"
        )

        if not next_url or not after:
            break

        params["after"] = after

    return all_comments


# ============================================================
# Process one Media
# ============================================================

async def _scan_media(
    client: httpx.AsyncClient,
    media_id: str,
    cutoff: datetime,
) -> int:
    comments = await _fetch_comments(
        client,
        media_id,
    )

    recent_comments = [
        comment
        for comment in comments
        if _is_recent_comment(
            comment,
            cutoff,
        )
    ]

    # قدیمی‌تر → جدیدتر
    recent_comments.sort(
        key=_comment_sort_key
    )

    processed_candidates = 0

    for comment in recent_comments:
        comment_id = comment.get(
            "id"
        )

        if not comment_id:
            continue

        value = dict(comment)

        # ساختاری مشابه Webhook تا همان processor مشترک استفاده شود.
        value["media"] = {
            "id": str(media_id)
        }

        try:
            await automation.process_comment(
                value,
                source="polling",
            )

            processed_candidates += 1

        except Exception:
            logger.exception(
                "Instagram polling processor failed "
                "media_id=%s comment_id=%s",
                media_id,
                comment_id,
            )

    return processed_candidates


# ============================================================
# Poll cycle
# ============================================================

async def poll_once() -> None:
    """
    یک cycle کامل Polling.

    Lock مانع overlap شدن دو cycle می‌شود؛
    اگر یک request بیش از interval طول بکشد،
    job بعدی وارد اجرای هم‌زمان نمی‌شود.
    """

    global _initialized
    global _last_comment_counts
    global _last_force_rescan_monotonic

    if not POLLING_ENABLED:
        return

    if not automation.INSTAGRAM_USER_ACCESS_TOKEN:
        logger.error(
            "Instagram polling غیرفعال شد: "
            "INSTAGRAM_USER_ACCESS_TOKEN تنظیم نشده."
        )
        return

    if not automation.INSTAGRAM_USER_ID:
        logger.error(
            "Instagram polling غیرفعال شد: "
            "INSTAGRAM_USER_ID تنظیم نشده."
        )
        return

    if _poll_lock.locked():
        logger.warning(
            "Instagram polling cycle قبلی هنوز "
            "در حال اجراست؛ cycle جدید skip شد."
        )
        return

    async with _poll_lock:
        now_utc = datetime.now(
            timezone.utc
        )

        cutoff = (
            now_utc
            - timedelta(
                seconds=LOOKBACK_SECONDS
            )
        )

        now_monotonic = (
            time.monotonic()
        )

        force_rescan = (
            not _initialized
            or (
                now_monotonic
                - _last_force_rescan_monotonic
                >= FORCE_RESCAN_SECONDS
            )
        )

        scanned_media = 0
        candidate_comments = 0

        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT
            ) as client:
                media_items = (
                    await _fetch_media_snapshot(
                        client
                    )
                )

                current_counts: dict[
                    str,
                    Optional[int],
                ] = {}

                for media in media_items:
                    media_id = str(
                        media["id"]
                    )

                    current_count = (
                        _read_comment_count(
                            media
                        )
                    )

                    current_counts[
                        media_id
                    ] = current_count

                    previous_count = (
                        _last_comment_counts.get(
                            media_id
                        )
                    )

                    should_scan = False

                    # اولین cycle:
                    # فقط recent comments را بررسی می‌کنیم.
                    if not _initialized:
                        should_scan = (
                            current_count is None
                            or current_count > 0
                        )

                    # Media جدید
                    elif media_id not in (
                        _last_comment_counts
                    ):
                        should_scan = (
                            current_count is None
                            or current_count > 0
                        )

                    # comments_count تغییر کرده
                    elif (
                        current_count
                        != previous_count
                    ):
                        should_scan = True

                    # Rescan دوره‌ای
                    elif force_rescan:
                        should_scan = (
                            current_count is None
                            or current_count > 0
                        )

                    if not should_scan:
                        continue

                    scanned_media += 1

                    try:
                        candidate_comments += (
                            await _scan_media(
                                client,
                                media_id,
                                cutoff,
                            )
                        )

                    except Exception:
                        logger.exception(
                            "خطا در scan کردن "
                            "Instagram media_id=%s",
                            media_id,
                        )

                _last_comment_counts = (
                    current_counts
                )

                _initialized = True

                if force_rescan:
                    _last_force_rescan_monotonic = (
                        now_monotonic
                    )

            logger.info(
                "Instagram polling cycle complete "
                "media_total=%s scanned=%s "
                "candidate_comments=%s "
                "lookback=%ss",
                len(media_items),
                scanned_media,
                candidate_comments,
                LOOKBACK_SECONDS,
            )

        except httpx.TimeoutException:
            logger.exception(
                "Instagram polling Graph API timeout"
            )

        except Exception:
            logger.exception(
                "Instagram polling cycle failed"
            )


# ============================================================
# Telegram JobQueue adapter
# ============================================================

async def poll_job(
    context,
) -> None:
    # context متعلق به python-telegram-bot است؛
    # Polling به آن احتیاج ندارد.
    del context

    await poll_once()