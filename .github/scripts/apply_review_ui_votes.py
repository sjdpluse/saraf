from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, content):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Reviews API: add per-user like/dislike votes and aggregate counts.
# ---------------------------------------------------------------------------
write("services/reviews_api_extension.py", r'''"""Mini App reviews endpoints.

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
''')


# ---------------------------------------------------------------------------
# Vote table migration.
# ---------------------------------------------------------------------------
write("supabase/migrations/20260906_002_miniapp_review_votes.sql", r'''-- Like/dislike votes for Mini App reviews.
create table if not exists public.miniapp_review_votes (
    review_id bigint not null references public.miniapp_reviews(id) on delete cascade,
    chat_id bigint not null,
    vote smallint not null check (vote in (-1, 1)),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (review_id, chat_id)
);

create index if not exists miniapp_review_votes_review_idx
    on public.miniapp_review_votes (review_id, vote);

alter table public.miniapp_review_votes enable row level security;
''')


# ---------------------------------------------------------------------------
# Frontend API vote method.
# ---------------------------------------------------------------------------
path = "webapp/src/lib/api.js"
text = read(path)
needle = '''  replyToReview: (reviewId, body) => request(`/reviews/${reviewId}/reply`, { method: "POST", body: { body } }),\n'''
replacement = needle + '''  voteReview: (reviewId, vote) => request(`/reviews/${reviewId}/vote`, { method: "POST", body: { vote } }),\n'''
if replacement not in text:
    assert needle in text
    text = text.replace(needle, replacement, 1)
write(path, text)


# ---------------------------------------------------------------------------
# Reviews page: Afghan Solar Hijri month names, lean UI, 7-item reveal, votes.
# ---------------------------------------------------------------------------
write("webapp/src/pages/Reviews.jsx", r'''import { useEffect, useMemo, useState } from "react";
import {
  CaretRight,
  ChatCircleText,
  CheckCircle,
  PaperPlaneTilt,
  PencilSimple,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
} from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { SARAF_LOGO_URL } from "../lib/brand";
import Skeleton from "../components/Skeleton";

const MAX_REVIEW_LENGTH = 800;
const INITIAL_VISIBLE_REVIEWS = 7;
const REVIEWS_COVER_URL = "https://i.postimg.cc/j2LNsV6J/ec67a9b5ebaf057dfccee73a663f086e.jpg";
const AFGHAN_MONTHS = ["حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله", "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت"];
const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

function toFaDigits(value) {
  return String(value ?? "").replace(/\d/g, (digit) => FA_DIGITS[Number(digit)]);
}

function formatAfghanDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  try {
    const parts = new Intl.DateTimeFormat("en-u-ca-persian", {
      timeZone: "Asia/Kabul",
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(date);
    const get = (type) => parts.find((part) => part.type === type)?.value || "";
    const month = AFGHAN_MONTHS[Math.max(0, Number(get("month")) - 1)] || "";
    return `${toFaDigits(get("day"))} ${month} ${toFaDigits(get("year"))}، ${toFaDigits(get("hour"))}:${toFaDigits(get("minute"))}`;
  } catch (_) {
    return "";
  }
}

function initials(name) {
  const parts = String(name || "کاربر").trim().split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map((part) => part[0]).join("") || "ک";
}

function ReviewCard({ review, isAdmin, onReply, onVote, showError }) {
  const [editing, setEditing] = useState(false);
  const [reply, setReply] = useState(review.admin_reply || "");
  const [saving, setSaving] = useState(false);
  const [voting, setVoting] = useState(false);

  async function submitReply() {
    const value = reply.trim();
    if (value.length < 3) return showError("پاسخ باید حداقل ۳ حرف باشد.");
    setSaving(true);
    try {
      await onReply(review.id, value);
      setEditing(false);
    } catch (_) {
    } finally {
      setSaving(false);
    }
  }

  async function submitVote(nextVote) {
    if (voting) return;
    const resolvedVote = Number(review.user_vote) === nextVote ? 0 : nextVote;
    setVoting(true);
    try {
      await onVote(review.id, resolvedVote);
    } finally {
      setVoting(false);
    }
  }

  return (
    <article className="review-card">
      <div className="review-head">
        <div className="review-avatar">{initials(review.display_name)}</div>
        <div className="review-author">
          <div className="review-author-name">{review.display_name}</div>
          <div className="review-date">{formatAfghanDate(review.created_at)}</div>
        </div>
        <div className="review-verified"><CheckCircle size={17} weight="fill" /></div>
      </div>

      <div className="review-body">{review.body}</div>

      <div className="review-votes" aria-label="لایک یا دیس‌لایک نظر">
        <button
          type="button"
          className={`review-vote-btn ${Number(review.user_vote) === 1 ? "active like" : ""}`}
          aria-pressed={Number(review.user_vote) === 1}
          onClick={() => submitVote(1)}
          disabled={voting}
        >
          <ThumbsUp size={16} weight={Number(review.user_vote) === 1 ? "fill" : "regular"} />
          <span className="num">{Number(review.likes || 0).toLocaleString()}</span>
        </button>
        <button
          type="button"
          className={`review-vote-btn ${Number(review.user_vote) === -1 ? "active dislike" : ""}`}
          aria-pressed={Number(review.user_vote) === -1}
          onClick={() => submitVote(-1)}
          disabled={voting}
        >
          <ThumbsDown size={16} weight={Number(review.user_vote) === -1 ? "fill" : "regular"} />
          <span className="num">{Number(review.dislikes || 0).toLocaleString()}</span>
        </button>
      </div>

      {review.admin_reply && !editing && (
        <div className="official-reply">
          <div className="official-reply-head">
            <img src={SARAF_LOGO_URL} alt="صراف" />
            <div>
              <div className="official-name"><ShieldCheck size={15} weight="fill" /> صراف</div>
              <div className="review-date">{formatAfghanDate(review.admin_replied_at)}</div>
            </div>
          </div>
          <div className="official-reply-body">{review.admin_reply}</div>
        </div>
      )}

      {isAdmin && !editing && (
        <button type="button" className="review-admin-action" onClick={() => setEditing(true)}>
          <PencilSimple size={15} /> {review.admin_reply ? "ویرایش پاسخ صراف" : "پاسخ به این نظر"}
        </button>
      )}

      {isAdmin && editing && (
        <div className="review-reply-editor">
          <textarea
            className="review-textarea compact"
            value={reply}
            onChange={(e) => setReply(e.target.value.slice(0, 1200))}
            placeholder="پاسخ صراف را بنویسید…"
            maxLength={1200}
          />
          <div className="review-compose-footer">
            <span className="review-counter num">{reply.length}/1200</span>
            <div className="review-editor-actions">
              <button type="button" className="review-cancel-btn" onClick={() => { setEditing(false); setReply(review.admin_reply || ""); }} disabled={saving}>لغو</button>
              <button type="button" className="review-submit-btn small" onClick={submitReply} disabled={saving || reply.trim().length < 3}>
                {saving ? <span className="spinner" /> : <><PaperPlaneTilt size={15} weight="fill" /> ثبت پاسخ</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

export default function Reviews({ navigate, showError }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const canSubmit = useMemo(() => body.trim().length >= 3 && !submitting, [body, submitting]);
  const visibleItems = showAll ? items : items.slice(0, INITIAL_VISIBLE_REVIEWS);
  const hiddenCount = Math.max(0, items.length - INITIAL_VISIBLE_REVIEWS);

  async function load() {
    setLoading(true);
    try {
      const reviews = await api.getReviews(50, 0);
      setItems(reviews.items || []);
      setTotal(Number(reviews.total || 0));
      setIsAdmin(Boolean(reviews.is_admin));
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "دریافت نظرات ناموفق بود.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitReview() {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      const created = await api.createReview(body.trim());
      setItems((prev) => [created, ...prev]);
      setTotal((prev) => prev + 1);
      setBody("");
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "ثبت نظر ناموفق بود.");
    } finally {
      setSubmitting(false);
    }
  }

  async function replyToReview(id, replyBody) {
    try {
      const updated = await api.replyToReview(id, replyBody);
      setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...updated } : item)));
      return updated;
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "ثبت پاسخ صراف ناموفق بود.");
      throw e;
    }
  }

  async function voteOnReview(id, vote) {
    try {
      const updated = await api.voteReview(id, vote);
      setItems((prev) => prev.map((item) => (
        item.id === id
          ? { ...item, likes: updated.likes, dislikes: updated.dislikes, user_vote: updated.user_vote }
          : item
      )));
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "ثبت لایک/دیس‌لایک ناموفق بود.");
      throw e;
    }
  }

  return (
    <div className="app-shell reviews-page">
      <div className="header">
        <button className="back-btn" onClick={() => navigate("home")} aria-label="بازگشت"><CaretRight size={18} weight="bold" /></button>
        <h1><ChatCircleText size={19} className="header-icon" weight="fill" /> نظرات کاربران</h1>
        <div className="header-spacer" />
      </div>

      <div className="reviews-cover-card animate-in" aria-hidden="true">
        <img src={REVIEWS_COVER_URL} alt="" />
        <ThumbsUp className="reviews-cover-like" weight="fill" />
      </div>

      <div className="reviews-list-head">
        <div className="reviews-list-title">همهٔ نظرات <span className="reviews-count num">{total.toLocaleString()}</span></div>
        {isAdmin && <span className="admin-mode-badge"><ShieldCheck size={14} weight="fill" /> مدیریت</span>}
      </div>

      <section className="review-compose-card animate-in" style={{ animationDelay: "0.04s" }}>
        <div className="review-compose-title">نظر شما</div>
        <textarea
          className="review-textarea"
          value={body}
          onChange={(e) => setBody(e.target.value.slice(0, MAX_REVIEW_LENGTH))}
          placeholder="نظر خود را بنویسید…"
          maxLength={MAX_REVIEW_LENGTH}
        />
        <div className="review-compose-footer">
          <span className={`review-counter num ${body.length > 740 ? "near-limit" : ""}`}>{body.length}/{MAX_REVIEW_LENGTH}</span>
          <button type="button" className="review-submit-btn" onClick={submitReview} disabled={!canSubmit}>
            {submitting ? <span className="spinner" /> : <><PaperPlaneTilt size={16} weight="fill" /> نشر نظر</>}
          </button>
        </div>
      </section>

      {loading && <Skeleton count={4} />}
      {!loading && items.length === 0 && (
        <div className="empty-state animate-in">
          <ChatCircleText size={44} className="empty-icon" />
          <div>هنوز نظری ثبت نشده است.</div>
        </div>
      )}

      {!loading && visibleItems.map((review) => (
        <ReviewCard
          key={review.id}
          review={review}
          isAdmin={isAdmin}
          onReply={replyToReview}
          onVote={voteOnReview}
          showError={showError}
        />
      ))}

      {!loading && !showAll && hiddenCount > 0 && (
        <button type="button" className="reviews-show-more" onClick={() => setShowAll(true)}>
          نمایش بیشتر <span className="num">({hiddenCount.toLocaleString()})</span>
        </button>
      )}
    </div>
  );
}
''')


# ---------------------------------------------------------------------------
# Replace the previous review-specific CSS with the lean layout requested.
# ---------------------------------------------------------------------------
path = "webapp/src/index.css"
text = read(path)
marker = "/* === Mini App Reviews UI ================================================= */"
if marker in text:
    text = text.split(marker, 1)[0].rstrip() + "\n\n"
text += r'''/* === Mini App Reviews UI ================================================= */
.stats-row-three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.stat-box-button {
  width: 100%;
  font: inherit;
  color: inherit;
  cursor: pointer;
  transition: transform 0.16s var(--ease-ios), box-shadow 0.16s var(--ease-ios), background 0.16s ease;
}

.stat-box-button:active {
  transform: scale(0.96);
  background: var(--color-card-hover);
  box-shadow: var(--shadow-xs);
}

.reviews-page {
  gap: 12px;
}

.reviews-cover-card {
  position: relative;
  overflow: hidden;
  width: 100%;
  border-radius: var(--radius-lg);
  background: #111;
  box-shadow: var(--shadow-card);
  line-height: 0;
}

.reviews-cover-card img {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}

.reviews-cover-like {
  position: absolute;
  inset: 50% auto auto 50%;
  transform: translate(-50%, -50%);
  width: clamp(72px, 24vw, 122px);
  height: clamp(72px, 24vw, 122px);
  color: #fff;
  opacity: 0.1;
  pointer-events: none;
}

.reviews-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 2px 2px;
}

.reviews-list-title {
  font-weight: 850;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 7px;
}

.reviews-count {
  min-width: 24px;
  height: 24px;
  padding: 0 7px;
  border-radius: var(--radius-pill);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-elevated);
  color: var(--color-text-muted);
  font-size: 10px;
}

.admin-mode-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-primary);
  background: var(--color-info-bg);
  border-radius: var(--radius-pill);
  padding: 6px 9px;
  font-size: 10px;
  font-weight: 700;
}

.review-compose-card,
.review-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.review-compose-card {
  border-radius: var(--radius-lg);
  padding: 16px;
}

.review-compose-title {
  font-weight: 850;
  font-size: 14px;
}

.review-textarea {
  width: 100%;
  min-height: 104px;
  resize: vertical;
  margin-top: 10px;
  border: 1px solid var(--color-border-strong);
  border-radius: 15px;
  background: #fbfbfd;
  padding: 12px 13px;
  font: inherit;
  font-size: 13px;
  line-height: 1.8;
  color: var(--color-text);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.review-textarea:focus {
  border-color: rgba(0, 113, 227, 0.5);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.08);
}

.review-textarea.compact {
  min-height: 88px;
  margin-top: 0;
}

.review-compose-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 9px;
}

.review-counter {
  font-size: 10.5px;
  color: var(--color-text-faint);
}

.review-counter.near-limit {
  color: var(--color-warn);
}

.review-submit-btn,
.review-cancel-btn,
.review-admin-action,
.reviews-show-more,
.review-vote-btn {
  border: 0;
  font-family: inherit;
  cursor: pointer;
}

.review-submit-btn {
  min-height: 40px;
  border-radius: 13px;
  padding: 0 15px;
  background: var(--gradient-primary);
  color: #fff;
  font-weight: 750;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 8px 18px rgba(0, 113, 227, 0.18);
}

.review-submit-btn.small {
  min-height: 36px;
  padding: 0 12px;
}

.review-submit-btn:disabled,
.review-vote-btn:disabled {
  opacity: 0.45;
  cursor: default;
}

.review-card {
  border-radius: 19px;
  padding: 15px;
  animation: fadeInUp 0.28s var(--ease-ios) both;
}

.review-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.review-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eaf4ff, #d7eaff);
  color: var(--color-primary-dark);
  font-size: 12px;
  font-weight: 850;
  flex-shrink: 0;
  border: 1px solid rgba(0, 113, 227, 0.09);
}

.review-author {
  flex: 1;
  min-width: 0;
}

.review-author-name {
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.review-date {
  font-size: 10px;
  color: var(--color-text-faint);
  margin-top: 2px;
}

.review-verified {
  color: var(--color-primary);
  display: flex;
}

.review-body,
.official-reply-body {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.9;
}

.review-body {
  font-size: 13px;
  color: var(--color-text);
  padding: 12px 2px 3px;
}

.review-votes {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 8px;
}

.review-vote-btn {
  min-width: 58px;
  height: 34px;
  padding: 0 10px;
  border-radius: var(--radius-pill);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: var(--color-bg-elevated);
  color: var(--color-text-muted);
  font-size: 11px;
  transition: transform 0.14s var(--ease-ios), background 0.14s ease, color 0.14s ease;
}

.review-vote-btn:active {
  transform: scale(0.94);
}

.review-vote-btn.active.like {
  background: var(--color-buy-bg);
  color: var(--color-buy);
}

.review-vote-btn.active.dislike {
  background: var(--color-sell-bg);
  color: var(--color-sell);
}

.official-reply {
  margin-top: 13px;
  border-radius: 16px;
  padding: 12px;
  background: linear-gradient(135deg, rgba(0, 113, 227, 0.07), rgba(10, 132, 255, 0.035));
  border: 1px solid rgba(0, 113, 227, 0.12);
}

.official-reply-head {
  display: flex;
  align-items: center;
  gap: 9px;
}

.official-reply-head img {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  object-fit: cover;
  background: #fff;
  box-shadow: var(--shadow-xs);
}

.official-name {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--color-primary-dark);
  font-size: 12px;
  font-weight: 850;
}

.official-reply-body {
  margin-top: 9px;
  font-size: 12.5px;
  color: #23415f;
}

.review-admin-action {
  margin-top: 9px;
  background: transparent;
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 4px;
}

.review-reply-editor {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.review-editor-actions {
  display: flex;
  align-items: center;
  gap: 7px;
}

.review-cancel-btn {
  min-height: 36px;
  border-radius: 12px;
  padding: 0 11px;
  background: var(--color-bg-elevated);
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
}

.reviews-show-more {
  width: 100%;
  min-height: 44px;
  border-radius: 15px;
  background: var(--color-card);
  color: var(--color-primary);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 370px) {
  .stat-box {
    padding: 11px 7px;
  }
  .stat-box .stat-value {
    font-size: 16px;
  }
  .stat-box .stat-label {
    font-size: 9.5px;
  }
}
'''
write(path, text)
