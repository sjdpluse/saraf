import { useEffect, useMemo, useState } from "react";
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
