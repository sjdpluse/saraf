"""Mini App reviews endpoints.

Users authenticated by Telegram Mini App initData can publish comments.  Only
Telegram IDs configured in ADMIN_CHAT_IDS can post/edit the official «صراف»
reply.  The browser never decides who is an admin; authorization is enforced
on the server for every reply mutation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from config import ADMIN_CHAT_IDS, BOT_TOKEN
from services import supabase_service as db
from services import webapp_auth

MAX_REVIEW_LENGTH = 800
MAX_REPLY_LENGTH = 1200
POST_COOLDOWN_SECONDS = 30


class ReviewCreateRequest(BaseModel):
    body: str


class ReviewReplyRequest(BaseModel):
    body: str


def _authenticate(init_data: Optional[str]) -> dict:
    try:
        return webapp_auth.verify_init_data(init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _clean_body(value: str, *, max_length: int = MAX_REVIEW_LENGTH) -> str:
    body = " ".join(str(value or "").strip().split())
    if len(body) < 3:
        raise HTTPException(status_code=400, detail="متن نظر باید حداقل ۳ حرف باشد.")
    if len(body) > max_length:
        raise HTTPException(status_code=400, detail=f"متن نباید بیشتر از {max_length} حرف باشد.")
    return body


def _display_name(user: dict) -> str:
    name = " ".join(
        part.strip()
        for part in (str(user.get("first_name") or ""), str(user.get("last_name") or ""))
        if part.strip()
    )
    return (name or "کاربر صراف")[:80]


def _is_admin(user: dict) -> bool:
    try:
        return int(user.get("id")) in set(ADMIN_CHAT_IDS)
    except (TypeError, ValueError):
        return False


def _public_review(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "display_name": row.get("display_name") or "کاربر صراف",
        "body": row.get("body") or "",
        "admin_reply": row.get("admin_reply"),
        "admin_replied_at": row.get("admin_replied_at"),
        "created_at": row.get("created_at"),
    }


async def list_reviews(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    user = _authenticate(x_telegram_init_data)
    try:
        query = (
            db.get_client()
            .table("miniapp_reviews")
            .select("id,display_name,body,admin_reply,admin_replied_at,created_at", count="exact")
            .eq("is_visible", True)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        result = query.execute()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="دریافت نظرات در حال حاضر ممکن نیست.") from exc

    return {
        "items": [_public_review(row) for row in (result.data or [])],
        "total": int(getattr(result, "count", 0) or 0),
        "is_admin": _is_admin(user),
    }


async def create_review(
    payload: ReviewCreateRequest,
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    user = _authenticate(x_telegram_init_data)
    body = _clean_body(payload.body)
    chat_id = int(user["id"])

    try:
        latest = (
            db.get_client()
            .table("miniapp_reviews")
            .select("created_at")
            .eq("chat_id", chat_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if latest.data:
            raw = latest.data[0].get("created_at")
            if raw:
                created = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds()
                if age < POST_COOLDOWN_SECONDS:
                    raise HTTPException(status_code=429, detail="لطفاً چند لحظه بعد نظر بعدی را ثبت کنید.")

        row = {
            "chat_id": chat_id,
            "display_name": _display_name(user),
            "username": str(user.get("username") or "")[:80] or None,
            "body": body,
            "is_visible": True,
        }
        result = db.get_client().table("miniapp_reviews").insert(row).execute()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="ثبت نظر ناموفق بود. لطفاً دوباره تلاش کنید.") from exc

    if not result.data:
        raise HTTPException(status_code=503, detail="ثبت نظر ناموفق بود.")
    return _public_review(result.data[0])


async def reply_to_review(
    review_id: int,
    payload: ReviewReplyRequest,
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    user = _authenticate(x_telegram_init_data)
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="فقط مدیر صراف اجازهٔ پاسخ به نظرات را دارد.")

    body = _clean_body(payload.body, max_length=MAX_REPLY_LENGTH)
    try:
        result = (
            db.get_client()
            .table("miniapp_reviews")
            .update({
                "admin_reply": body,
                "admin_replied_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", review_id)
            .eq("is_visible", True)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="ثبت پاسخ صراف ناموفق بود.") from exc

    if not result.data:
        raise HTTPException(status_code=404, detail="نظر موردنظر پیدا نشد.")
    return _public_review(result.data[0])


def install() -> None:
    if getattr(FastAPI, "_saraf_reviews_extension_installed", False):
        return
    original_init = FastAPI.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.add_api_route("/api/reviews", list_reviews, methods=["GET"], name="miniapp_reviews_list")
        self.add_api_route("/api/reviews", create_review, methods=["POST"], name="miniapp_reviews_create")
        self.add_api_route(
            "/api/reviews/{review_id}/reply",
            reply_to_review,
            methods=["POST"],
            name="miniapp_reviews_reply",
        )

    FastAPI.__init__ = patched_init
    FastAPI._saraf_reviews_extension_installed = True
