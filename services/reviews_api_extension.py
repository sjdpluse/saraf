"""Mini App reviews endpoints.

Users authenticated by Telegram Mini App initData can publish comments and
vote on them. Only Telegram IDs configured in ADMIN_CHAT_IDS can post/edit the
official «صراف» reply. Authorization is always enforced on the server.
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


class ReviewVoteRequest(BaseModel):
    vote: int


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


def _public_review(row: dict, *, likes: int = 0, dislikes: int = 0, user_vote: int = 0) -> dict:
    return {
        "id": row.get("id"),
        "display_name": row.get("display_name") or "کاربر صراف",
        "body": row.get("body") or "",
        "admin_reply": row.get("admin_reply"),
        "admin_replied_at": row.get("admin_replied_at"),
        "created_at": row.get("created_at"),
        "likes": int(likes or 0),
        "dislikes": int(dislikes or 0),
        "user_vote": int(user_vote or 0),
    }


def _vote_snapshots(review_ids: list[int], chat_id: int) -> dict[int, dict]:
    snapshots = {int(review_id): {"likes": 0, "dislikes": 0, "user_vote": 0} for review_id in review_ids}
    if not review_ids:
        return snapshots
    try:
        result = (
            db.get_client()
            .table("miniapp_review_votes")
            .select("review_id,chat_id,vote")
            .in_("review_id", review_ids)
            .execute()
        )
    except Exception:
        # A deployment can briefly run before the vote migration is applied.
        # Reviews remain readable and simply show zero counters in that window.
        return snapshots

    for row in result.data or []:
        review_id = int(row.get("review_id"))
        if review_id not in snapshots:
            continue
        vote = int(row.get("vote") or 0)
        if vote == 1:
            snapshots[review_id]["likes"] += 1
        elif vote == -1:
            snapshots[review_id]["dislikes"] += 1
        if int(row.get("chat_id") or 0) == chat_id:
            snapshots[review_id]["user_vote"] = vote
    return snapshots


def _review_with_vote_snapshot(row: dict, chat_id: int) -> dict:
    review_id = int(row.get("id"))
    snapshot = _vote_snapshots([review_id], chat_id)[review_id]
    return _public_review(row, **snapshot)


async def list_reviews(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    user = _authenticate(x_telegram_init_data)
    chat_id = int(user["id"])
    try:
        result = (
            db.get_client()
            .table("miniapp_reviews")
            .select("id,display_name,body,admin_reply,admin_replied_at,created_at", count="exact")
            .eq("is_visible", True)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="دریافت نظرات در حال حاضر ممکن نیست.") from exc

    rows = result.data or []
    snapshots = _vote_snapshots([int(row["id"]) for row in rows], chat_id)
    return {
        "items": [_public_review(row, **snapshots[int(row["id"])]) for row in rows],
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

        result = db.get_client().table("miniapp_reviews").insert({
            "chat_id": chat_id,
            "display_name": _display_name(user),
            "username": str(user.get("username") or "")[:80] or None,
            "body": body,
            "is_visible": True,
        }).execute()
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
    chat_id = int(user["id"])
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
    return _review_with_vote_snapshot(result.data[0], chat_id)


async def vote_review(
    review_id: int,
    payload: ReviewVoteRequest,
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    user = _authenticate(x_telegram_init_data)
    chat_id = int(user["id"])
    vote = int(payload.vote)
    if vote not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="رأی نامعتبر است.")

    try:
        review = (
            db.get_client()
            .table("miniapp_reviews")
            .select("id")
            .eq("id", review_id)
            .eq("is_visible", True)
            .limit(1)
            .execute()
        )
        if not review.data:
            raise HTTPException(status_code=404, detail="نظر موردنظر پیدا نشد.")

        votes = db.get_client().table("miniapp_review_votes")
        if vote == 0:
            votes.delete().eq("review_id", review_id).eq("chat_id", chat_id).execute()
        else:
            now = datetime.now(timezone.utc).isoformat()
            votes.upsert({
                "review_id": review_id,
                "chat_id": chat_id,
                "vote": vote,
                "updated_at": now,
            }, on_conflict="review_id,chat_id").execute()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="ثبت لایک/دیس‌لایک ناموفق بود.") from exc

    snapshot = _vote_snapshots([review_id], chat_id)[review_id]
    return {"review_id": review_id, **snapshot}


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
        self.add_api_route(
            "/api/reviews/{review_id}/vote",
            vote_review,
            methods=["POST"],
            name="miniapp_reviews_vote",
        )

    FastAPI.__init__ = patched_init
    FastAPI._saraf_reviews_extension_installed = True
