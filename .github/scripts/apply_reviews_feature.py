from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, content):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# WhatsApp / Telegram prepared text: use the Persian brand name «صراف».
# ---------------------------------------------------------------------------
for path in [
    "webapp/src/components/WhatsAppSupport.jsx",
    "webapp/src/pages/Orders.jsx",
    "webapp/src/pages/Buy.jsx",
    "webapp/src/pages/Sell.jsx",
]:
    text = read(path)
    text = text.replace("Saraf", "صراف")
    write(path, text)


# ---------------------------------------------------------------------------
# Orders: tracking actions are only meaningful while an order is pending.
# ---------------------------------------------------------------------------
path = "webapp/src/pages/Orders.jsx"
text = read(path)
needle = '''function orderCode(order) {\n  const asset = orderAsset(order);\n  return `${asset}-${String(order.id).padStart(5, "0")}`;\n}\n'''
replacement = needle + '''\nfunction canTrackOrder(order) {\n  return order?.status === "pending";\n}\n'''
assert needle in text
text = text.replace(needle, replacement, 1)
old = '''      <div className="card animate-in order-tracking-card" style={{ animationDelay: "0.03s" }}>\n        <div className="section-title">رهگیری سفارش {code}</div>\n        <TrackingActions order={order} />\n      </div>\n'''
new = '''      {canTrackOrder(order) && (\n        <div className="card animate-in order-tracking-card" style={{ animationDelay: "0.03s" }}>\n          <div className="section-title">رهگیری سفارش {code}</div>\n          <TrackingActions order={order} />\n        </div>\n      )}\n'''
assert old in text
text = text.replace(old, new, 1)
old = '''            <TrackingActions order={o} stopPropagation />\n'''
new = '''            {canTrackOrder(o) && <TrackingActions order={o} stopPropagation />}\n'''
assert old in text
text = text.replace(old, new, 1)
write(path, text)


# ---------------------------------------------------------------------------
# Reviews backend: authenticated public comments + server-enforced admin reply.
# ---------------------------------------------------------------------------
write("services/reviews_api_extension.py", r'''"""Mini App reviews endpoints.

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
''')

path = "services/__init__.py"
text = read(path)
text = text.replace(
    "from services.usdt_api_guard import install as _install_usdt_api_guard\n",
    "from services.usdt_api_guard import install as _install_usdt_api_guard\nfrom services.reviews_api_extension import install as _install_reviews_api_extension\n",
)
text = text.replace(
    "_install_usdt_api_guard()\n",
    "_install_usdt_api_guard()\n_install_reviews_api_extension()\n",
)
write(path, text)


# ---------------------------------------------------------------------------
# Supabase migration for comments and official replies.
# ---------------------------------------------------------------------------
write("supabase/migrations/20260906_001_miniapp_reviews.sql", r'''-- Mini App user reviews and official Saraf replies.
-- Access is through the authenticated FastAPI service only; no direct client policies.

create table if not exists public.miniapp_reviews (
    id bigint generated by default as identity primary key,
    chat_id bigint not null,
    display_name text not null check (char_length(display_name) between 1 and 80),
    username text,
    body text not null check (char_length(body) between 3 and 800),
    admin_reply text check (admin_reply is null or char_length(admin_reply) between 3 and 1200),
    admin_replied_at timestamptz,
    is_visible boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists miniapp_reviews_visible_created_idx
    on public.miniapp_reviews (is_visible, created_at desc);

create index if not exists miniapp_reviews_chat_created_idx
    on public.miniapp_reviews (chat_id, created_at desc);

alter table public.miniapp_reviews enable row level security;

comment on table public.miniapp_reviews is
    'User comments shown in the Saraf Mini App. Official replies are written by ADMIN_CHAT_IDS through the server API.';
''')


# ---------------------------------------------------------------------------
# Frontend API methods.
# ---------------------------------------------------------------------------
path = "webapp/src/lib/api.js"
text = read(path)
needle = '''  getMyOrders: () => request("/usdt/orders/me"),\n  getStats: () => request("/usdt/stats"),\n  getPaymentInfo: () => request("/usdt/payment-info"),\n'''
replacement = '''  getMyOrders: () => request("/usdt/orders/me"),\n  getStats: () => request("/usdt/stats"),\n  getReviews: (limit = 20, offset = 0) => request(`/reviews?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`),\n  createReview: (body) => request("/reviews", { method: "POST", body: { body } }),\n  replyToReview: (reviewId, body) => request(`/reviews/${reviewId}/reply`, { method: "POST", body: { body } }),\n  getPaymentInfo: () => request("/usdt/payment-info"),\n'''
assert needle in text
text = text.replace(needle, replacement, 1)
write(path, text)


# ---------------------------------------------------------------------------
# Full Reviews page.
# ---------------------------------------------------------------------------
write("webapp/src/pages/Reviews.jsx", r'''import { useEffect, useMemo, useState } from "react";
import {
  CaretRight,
  ChatCircleText,
  CheckCircle,
  PaperPlaneTilt,
  PencilSimple,
  ShieldCheck,
  Star,
} from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { SARAF_LOGO_URL } from "../lib/brand";
import Skeleton from "../components/Skeleton";

const MAX_REVIEW_LENGTH = 800;

function formatDate(value) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat("fa-AF", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch (_) {
    return "";
  }
}

function initials(name) {
  const parts = String(name || "کاربر").trim().split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map((part) => part[0]).join("") || "ک";
}

function ReviewCard({ review, isAdmin, onReply, showError }) {
  const [editing, setEditing] = useState(false);
  const [reply, setReply] = useState(review.admin_reply || "");
  const [saving, setSaving] = useState(false);

  async function submitReply() {
    const value = reply.trim();
    if (value.length < 3) return showError("پاسخ باید حداقل ۳ حرف باشد.");
    setSaving(true);
    try {
      await onReply(review.id, value);
      setEditing(false);
    } catch (_) {
      // onReply خطای قابل نمایش را مدیریت می‌کند.
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="review-card">
      <div className="review-head">
        <div className="review-avatar">{initials(review.display_name)}</div>
        <div className="review-author">
          <div className="review-author-name">{review.display_name}</div>
          <div className="review-date">{formatDate(review.created_at)}</div>
        </div>
        <div className="review-verified" title="کاربر تاییدشده در تلگرام"><CheckCircle size={17} weight="fill" /></div>
      </div>

      <div className="review-body">{review.body}</div>

      {review.admin_reply && !editing && (
        <div className="official-reply">
          <div className="official-reply-head">
            <img src={SARAF_LOGO_URL} alt="صراف" />
            <div>
              <div className="official-name"><ShieldCheck size={15} weight="fill" /> صراف</div>
              <div className="review-date">پاسخ رسمی · {formatDate(review.admin_replied_at)}</div>
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
            placeholder="پاسخ رسمی صراف را بنویسید…"
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
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = useMemo(() => body.trim().length >= 3 && !submitting, [body, submitting]);

  async function load() {
    setLoading(true);
    try {
      const [reviews, publicStats] = await Promise.all([api.getReviews(50, 0), api.getStats().catch(() => null)]);
      setItems(reviews.items || []);
      setTotal(Number(reviews.total || 0));
      setIsAdmin(Boolean(reviews.is_admin));
      setStats(publicStats);
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
      setItems((prev) => prev.map((item) => (item.id === id ? updated : item)));
      return updated;
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "ثبت پاسخ صراف ناموفق بود.");
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

      <section className="reviews-summary-card animate-in">
        <div className="reviews-summary-icon"><ChatCircleText size={24} weight="fill" /></div>
        <div className="reviews-summary-copy">
          <div className="reviews-summary-title">تجربهٔ کاربران صراف</div>
          <div className="reviews-summary-subtitle">نظر خود را بنویسید؛ پاسخ‌های دارای نشان «صراف» مستقیماً توسط مدیریت ثبت می‌شوند.</div>
        </div>
        <div className="reviews-summary-stats">
          <div><strong className="num">{total.toLocaleString()}</strong><span>نظر</span></div>
          <div><strong className="num">{stats?.average_rating ? Number(stats.average_rating).toFixed(1) : "—"}</strong><span><Star size={12} weight="fill" /> امتیاز</span></div>
        </div>
      </section>

      <section className="review-compose-card animate-in" style={{ animationDelay: "0.04s" }}>
        <div className="review-compose-title">نظر شما</div>
        <div className="review-compose-subtitle">تجربه، پیشنهاد یا دیدگاه‌تان درباره خدمات صراف را با دیگر کاربران شریک کنید.</div>
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

      <div className="reviews-list-head">
        <div>
          <div className="reviews-list-title">همهٔ نظرات</div>
          <div className="reviews-list-subtitle">جدیدترین نظرات در بالا نمایش داده می‌شوند.</div>
        </div>
        {isAdmin && <span className="admin-mode-badge"><ShieldCheck size={14} weight="fill" /> حالت مدیریت</span>}
      </div>

      {loading && <Skeleton count={4} />}
      {!loading && items.length === 0 && (
        <div className="empty-state animate-in">
          <ChatCircleText size={44} className="empty-icon" />
          <div>هنوز نظری ثبت نشده است.</div>
          <div className="notice" style={{ justifyContent: "center" }}>اولین نظر را شما بنویسید.</div>
        </div>
      )}

      {!loading && items.map((review) => (
        <ReviewCard key={review.id} review={review} isAdmin={isAdmin} onReply={replyToReview} showError={showError} />
      ))}
    </div>
  );
}
''')


# ---------------------------------------------------------------------------
# App routing.
# ---------------------------------------------------------------------------
path = "webapp/src/App.jsx"
text = read(path)
assert 'import Orders from "./pages/Orders";' in text
text = text.replace('import Orders from "./pages/Orders";\n', 'import Orders from "./pages/Orders";\nimport Reviews from "./pages/Reviews";\n', 1)
needle = '        {page === "orders" && <Orders navigate={navigate} showError={showError} />}\n'
replacement = needle + '        {page === "reviews" && <Reviews navigate={navigate} showError={showError} />}\n'
assert needle in text
text = text.replace(needle, replacement, 1)
write(path, text)


# ---------------------------------------------------------------------------
# Home: comments card on the left of average rating; shows live comment count.
# ---------------------------------------------------------------------------
path = "webapp/src/pages/Home.jsx"
text = read(path)
text = text.replace('  Star,\n} from "@phosphor-icons/react";', '  Star,\n  ChatCircleText,\n} from "@phosphor-icons/react";', 1)
text = text.replace('  const [stats, setStats] = useState(null);\n', '  const [stats, setStats] = useState(null);\n  const [reviewsCount, setReviewsCount] = useState(null);\n', 1)
old = '''  useEffect(() => {\n    let mounted = true;\n    api.getStats().then((s) => mounted && setStats(s)).catch(() => {});\n    return () => { mounted = false; };\n  }, []);\n'''
new = '''  useEffect(() => {\n    let mounted = true;\n    api.getStats().then((s) => mounted && setStats(s)).catch(() => {});\n    api.getReviews(1, 0).then((r) => mounted && setReviewsCount(Number(r.total || 0))).catch(() => {});\n    return () => { mounted = false; };\n  }, []);\n'''
assert old in text
text = text.replace(old, new, 1)
old = '''      {stats && stats.completed_orders > 0 && (\n        <div className="stats-row animate-in" style={{ animationDelay: "0.06s" }}>\n          <div className="stat-box">\n            <Users size={20} className="stat-icon" weight="fill" />\n            <div className="stat-value num">{stats.completed_orders.toLocaleString()}</div>\n            <div className="stat-label">معاملهٔ تکمیل‌شده</div>\n          </div>\n          <div className="stat-box">\n            <Star size={20} className="stat-icon" weight="fill" />\n            <div className="stat-value num">{stats.average_rating ? stats.average_rating.toFixed(1) : "—"}</div>\n            <div className="stat-label">میانگین امتیاز کاربران</div>\n          </div>\n        </div>\n      )}\n'''
new = '''      {stats && (\n        <div className="stats-row stats-row-three animate-in" style={{ animationDelay: "0.06s" }}>\n          <div className="stat-box">\n            <Users size={20} className="stat-icon" weight="fill" />\n            <div className="stat-value num">{Number(stats.completed_orders || 0).toLocaleString()}</div>\n            <div className="stat-label">معاملهٔ تکمیل‌شده</div>\n          </div>\n          <div className="stat-box">\n            <Star size={20} className="stat-icon" weight="fill" />\n            <div className="stat-value num">{stats.average_rating ? Number(stats.average_rating).toFixed(1) : "—"}</div>\n            <div className="stat-label">میانگین امتیاز کاربران</div>\n          </div>\n          <button type="button" className="stat-box stat-box-button" onClick={() => navigate("reviews")}>\n            <ChatCircleText size={20} className="stat-icon" weight="fill" />\n            <div className="stat-value num">{reviewsCount === null ? "—" : reviewsCount.toLocaleString()}</div>\n            <div className="stat-label">نظرات کاربران</div>\n          </button>\n        </div>\n      )}\n'''
assert old in text
text = text.replace(old, new, 1)
write(path, text)


# ---------------------------------------------------------------------------
# Reviews styling, aligned with the existing light/blue glass design system.
# ---------------------------------------------------------------------------
path = "webapp/src/index.css"
text = read(path)
marker = "/* === Mini App Reviews UI ================================================= */"
if marker not in text:
    text += r'''

/* === Mini App Reviews UI ================================================= */
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

.reviews-summary-card,
.review-compose-card,
.review-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
}

.reviews-summary-card {
  border-radius: var(--radius-lg);
  padding: 17px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: center;
}

.reviews-summary-icon {
  width: 46px;
  height: 46px;
  border-radius: 15px;
  background: var(--color-info-bg);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.reviews-summary-title {
  font-size: 15px;
  font-weight: 800;
}

.reviews-summary-subtitle,
.review-compose-subtitle,
.reviews-list-subtitle {
  color: var(--color-text-muted);
  font-size: 11.5px;
  line-height: 1.75;
  margin-top: 3px;
}

.reviews-summary-stats {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  border-top: 1px solid var(--color-border);
  padding-top: 12px;
}

.reviews-summary-stats > div {
  background: var(--color-bg-elevated);
  border-radius: 13px;
  padding: 10px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.reviews-summary-stats strong {
  font-size: 18px;
}

.reviews-summary-stats span {
  color: var(--color-text-muted);
  font-size: 10.5px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.review-compose-card {
  border-radius: var(--radius-lg);
  padding: 17px;
}

.review-compose-title,
.reviews-list-title {
  font-weight: 800;
  font-size: 14px;
}

.review-textarea {
  width: 100%;
  min-height: 112px;
  resize: vertical;
  margin-top: 12px;
  border: 1px solid var(--color-border-strong);
  border-radius: 16px;
  background: #fbfbfd;
  padding: 13px 14px;
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
  min-height: 92px;
  margin-top: 0;
}

.review-compose-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
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
.review-admin-action {
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

.review-submit-btn:disabled {
  opacity: 0.45;
  cursor: default;
  box-shadow: none;
}

.reviews-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 2px 2px;
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
  padding: 12px 2px 2px;
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
  margin-top: 11px;
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
