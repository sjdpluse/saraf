import { useEffect, useMemo, useState } from "react";
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
