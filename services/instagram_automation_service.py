"""
اتوماسیون کامنت اینستاگرام Saraf — دو رفتار کاملاً مستقل روی هر کامنت جدید:

  ۱) اگر متن کامنت شامل یکی از INSTAGRAM_COMMENT_KEYWORDS باشد (مثلاً «صراف»)،
     بلافاصله یک دایرکت خصوصی (private reply) حاوی لینک ربات تلگرام فرستاده
     می‌شود — بدون هیچ شرط فالو (طبق تصمیم شما؛ توجه: Instagram Graph API اصلاً
     هیچ endpoint رسمی برای «آیا کاربر X مرا فالو کرده؟» ندارد، پس این تصمیم هم
     از نظر فنی ساده‌تر و هم صادقانه‌تر است تا یک گیت خودگزارشیِ غیرقابل‌اتکا).
  ۲) اگر INSTAGRAM_AI_REPLY_ENABLED روشن باشد، زیر **همهٔ** کامنت‌های پست‌ها
     (هر متنی، طبق تصمیم شما) یک پاسخ عمومی با هوش مصنوعی (از طریق OpenRouter)
     نوشته می‌شود.

هر دو رفتار مستقل‌اند و می‌توانند روی یک کامنت هم‌زمان اجرا شوند.

جریان فنی:
  Meta → POST به /webhooks/instagram (این وبهوک در api.py سوار می‌شود) →
  امضا با X-Hub-Signature-256 تایید می‌شود → برای هر کامنت جدید:
    - idempotency: comment_id در جدول ig_comment_events ثبت می‌شود؛ اگر قبلاً
      بوده (retry وبهوک متا)، به‌کلی نادیده گرفته می‌شود.
    - کامنت‌های خودِ پیج (یعنی پاسخ‌های AI خودمان) رد می‌شوند تا حلقهٔ
      بی‌نهایت پیش نیاید.
    - مسیر کلمهٔ کلیدی → private reply
    - مسیر AI → OpenRouter → public reply روی همان کامنت

نیازمند:
  - INSTAGRAM_APP_SECRET (برای تایید امضای وبهوک)
  - INSTAGRAM_WEBHOOK_VERIFY_TOKEN (برای handshake اولیهٔ GET)
  - همان FACEBOOK_PAGE_ACCESS_TOKEN و INSTAGRAM_BUSINESS_ACCOUNT_ID موجود
  - OPENROUTER_API_KEY (برای پاسخ AI؛ اگر خالی باشد، این بخش صرفاً غیرفعال
    می‌ماند و مسیر دایرکت/کلمهٔ کلیدی بدون مشکل کار می‌کند)

راهنمای کامل تنظیم Webhook در Meta Dashboard: INSTAGRAM_COMMENTS_SETUP_GUIDE.md
"""
import hashlib
import hmac
import logging
from typing import Optional

import httpx

from config import (
    FACEBOOK_PAGE_ACCESS_TOKEN,
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
from services import supabase_service as db

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = 20.0
# سقف طول پاسخ AI روی یک کامنت — یک کامنت طولانی و پاراگراف‌مانند غیرطبیعی به‌نظر
# می‌رسد؛ system prompt هم همین را می‌خواهد، این یک محافظ نهایی است.
_AI_REPLY_MAX_CHARS = 400


# ---------------------------------------------------------------------------
# تایید امضای وبهوک
# ---------------------------------------------------------------------------
def verify_webhook_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """امضای X-Hub-Signature-256 را با INSTAGRAM_APP_SECRET تایید می‌کند تا
    مطمئن شویم درخواست واقعاً از متا آمده، نه یک POST جعلی از جای دیگر."""
    if not INSTAGRAM_APP_SECRET:
        logger.warning(
            "INSTAGRAM_APP_SECRET تنظیم نشده — امضای وبهوک تایید نمی‌شود (فقط برای توسعهٔ محلی قابل‌قبول است، هرگز در production)."
        )
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(INSTAGRAM_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


# ---------------------------------------------------------------------------
# پردازش payload وبهوک
# ---------------------------------------------------------------------------
async def handle_webhook_payload(payload: dict) -> None:
    if payload.get("object") != "instagram":
        return
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            value = change.get("value") or {}
            await _process_comment(value)


async def _process_comment(value: dict) -> None:
    comment_id = value.get("id")
    text = (value.get("text") or "").strip()
    from_user = value.get("from") or {}
    from_id = from_user.get("id")
    username = from_user.get("username")
    media_id = (value.get("media") or {}).get("id")

    if not comment_id:
        return

    # جلوگیری از حلقهٔ بی‌نهایت: کامنتی که خودِ پیج گذاشته (شامل پاسخ‌های AI
    # قبلی ما) هرگز دوباره پردازش نمی‌شود.
    if from_id and str(from_id) == str(INSTAGRAM_BUSINESS_ACCOUNT_ID):
        return

    if not db.try_claim_ig_comment_event(comment_id, media_id, username, text):
        return  # قبلاً پردازش شده (webhook retry)

    dm_sent = False
    if _matches_keyword(text):
        ok, detail = await _send_private_reply(comment_id, text=INSTAGRAM_DM_LINK_MESSAGE.format(bot_link=TELEGRAM_BOT_LINK))
        dm_sent = ok
        if not ok:
            logger.warning("ارسال دایرکت خودکار برای کامنت %s ناموفق بود: %s", comment_id, detail)

    ai_replied = False
    if INSTAGRAM_AI_REPLY_ENABLED and text:
        ai_text = await _generate_ai_reply(text, username)
        if ai_text:
            ok, detail = await _reply_to_comment_publicly(comment_id, ai_text)
            ai_replied = ok
            if not ok:
                logger.warning("ارسال پاسخ AI برای کامنت %s ناموفق بود: %s", comment_id, detail)

    db.mark_ig_comment_event(comment_id, dm_sent=dm_sent, ai_replied=ai_replied)


def _matches_keyword(text: str) -> bool:
    if not text or not INSTAGRAM_COMMENT_KEYWORDS:
        return False
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in INSTAGRAM_COMMENT_KEYWORDS)


# ---------------------------------------------------------------------------
# Graph API: دایرکت خصوصی (private reply) روی یک کامنت مشخص
# ---------------------------------------------------------------------------
def _extract_graph_error(resp: httpx.Response) -> str:
    try:
        err = resp.json().get("error", {})
        parts = [err.get("message") or resp.text[:300]]
        if err.get("type"):
            parts.append(f"type={err['type']}")
        if err.get("code") is not None:
            parts.append(f"code={err['code']}")
        return " | ".join(str(p) for p in parts)
    except Exception:
        return (resp.text or "پاسخ نامشخص از Graph API")[:300]


async def _send_private_reply(comment_id: str, text: str) -> tuple[bool, str]:
    """Meta فقط اجازهٔ یک private reply در کل عمر هر کامنت را می‌دهد (و فقط تا
    ۷ روز بعد از کامنت) — این یک محدودیت سمت متا است، نه محدودیت این کد."""
    if not INSTAGRAM_BUSINESS_ACCOUNT_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        return False, "INSTAGRAM_BUSINESS_ACCOUNT_ID یا FACEBOOK_PAGE_ACCESS_TOKEN تنظیم نشده"

    url = f"{GRAPH_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/messages"
    params = {"access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    body = {"recipient": {"comment_id": comment_id}, "message": {"text": text}}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, params=params, json=body)
        if resp.status_code >= 400:
            return False, _extract_graph_error(resp)
        return True, "ok"
    except Exception as exc:
        logger.exception("خطای شبکه هنگام ارسال دایرکت خودکار اینستاگرام")
        return False, f"خطای شبکه/غیرمنتظره: {exc}"


async def _reply_to_comment_publicly(comment_id: str, text: str) -> tuple[bool, str]:
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        return False, "FACEBOOK_PAGE_ACCESS_TOKEN تنظیم نشده"

    url = f"{GRAPH_BASE}/{comment_id}/replies"
    params = {"message": text, "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, params=params)
        if resp.status_code >= 400:
            return False, _extract_graph_error(resp)
        return True, "ok"
    except Exception as exc:
        logger.exception("خطای شبکه هنگام ارسال پاسخ عمومی به کامنت اینستاگرام")
        return False, f"خطای شبکه/غیرمنتظره: {exc}"


# ---------------------------------------------------------------------------
# OpenRouter: تولید پاسخ AI برای کامنت
# ---------------------------------------------------------------------------
async def _generate_ai_reply(comment_text: str, username: Optional[str]) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        logger.info("OPENROUTER_API_KEY تنظیم نشده؛ پاسخ AI به کامنت رد شد.")
        return None

    user_line = f"@{username} این کامنت را گذاشته: {comment_text}" if username else comment_text
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # این دو هدر اختیاری‌اند اما OpenRouter توصیه می‌کند برای رتبه‌بندی/آمار بدهید
        "HTTP-Referer": "https://saraf.example.com",
        "X-Title": "Saraf Instagram Auto-Reply",
    }
    body = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": OPENROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_line},
        ],
        "max_tokens": 150,
        "temperature": 0.7,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(OPENROUTER_URL, headers=headers, json=body)
        if resp.status_code >= 400:
            logger.error("خطای OpenRouter (HTTP %s): %s", resp.status_code, resp.text[:300])
            return None
        data = resp.json()
        reply = data["choices"][0]["message"]["content"].strip()
        if not reply:
            return None
        if len(reply) > _AI_REPLY_MAX_CHARS:
            reply = reply[: _AI_REPLY_MAX_CHARS - 1].rstrip() + "…"
        return reply
    except Exception:
        logger.exception("خطا در فراخوانی OpenRouter برای پاسخ AI")
        return None
