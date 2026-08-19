# Facebook Comment Automation — صراف

## What this adds

- `GET /webhooks/facebook` for Meta webhook verification.
- `POST /webhooks/facebook` for Facebook Page feed events.
- Public reply to keyword comments such as `صراف`, `سراف`, or `Saraf`.
- AI public replies for normal comments.
- Trusted live data from the existing صراف currency/gold/USDT services.
- Output sanitization using the same reasoning/Markdown protection already used by Instagram V2.
- Duplicate-event protection in Supabase.
- Self-comment protection so the Page does not reply to its own replies.

## 1. Supabase migration

Run:

`supabase/migrations/20260819_002_facebook_comment_automation.sql`

It creates the `fb_comment_events` table used for idempotency and processing state.

## 2. Railway variables

Add/verify:

```env
FACEBOOK_PAGE_ID=...
FACEBOOK_PAGE_ACCESS_TOKEN=...
FACEBOOK_APP_SECRET=...
FACEBOOK_WEBHOOK_VERIFY_TOKEN=...
FACEBOOK_GRAPH_API_VERSION=v26.0
FACEBOOK_AI_REPLY_ENABLED=true
FACEBOOK_COMMENT_KEYWORDS=Saraf,صراف,سراف
FACEBOOK_AI_COMMENT_MAX_CHARS=500
FACEBOOK_KEYWORD_PUBLIC_REPLY=سلام 👋 به صراف خوش آمدید. برای مشاهده نرخ‌های لحظه‌یی ارز، طلا و خدمات صراف، ربات رسمی را باز کنید:\n{bot_link}
```

The automation also reuses the existing:

```env
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=...
OPENROUTER_FALLBACK_MODELS=...
TELEGRAM_BOT_LINK=https://t.me/sarafiaf_bot
```

`FACEBOOK_APP_SECRET` must be the App Secret of the Meta app that sends the Facebook Page webhook. Do not use the Instagram Login app secret unless it is actually the same Meta app.

## 3. Meta webhook callback

Use this callback URL:

`https://beneficial-expression-production-e943.up.railway.app/webhooks/facebook`

Use exactly the same value for Meta's Verify Token and Railway's `FACEBOOK_WEBHOOK_VERIFY_TOKEN`.

For the Facebook Page webhook subscription, subscribe the Page object to the `feed` field. Comment additions arrive in `entry[].changes[]` with `field=feed`, and the automation processes only new comment events.

## 4. Permissions/token

Use a valid Facebook Page Access Token for the configured Page. The token/app must have the Page permissions required by Meta for reading Page engagement/webhooks and creating comment replies. Verify the exact permission names required by your app mode and Graph API version in the current Meta dashboard before production review.

## 5. Expected behavior

### Keyword comment

Input:

`صراف`

Expected public reply:

`سلام 👋 به صراف خوش آمدید. برای مشاهده نرخ‌های لحظه‌یی ارز، طلا و خدمات صراف، ربات رسمی را باز کنید:`

followed by the official Telegram bot link.

### Normal comment

Input:

`نرخ دالر امروز چند است؟`

Expected: the service loads current USD data from the existing صراف rate engine, gives it to AI as trusted data, sanitizes the output, and posts a short public reply.

### Praise/comment

Input:

`خدمات شما عالی است`

Expected: a short natural Dari reply, without Markdown or model reasoning.

## 6. Safety/operational rules

- Signature verification stays enabled using `X-Hub-Signature-256` and `FACEBOOK_APP_SECRET`.
- Requests with invalid signatures return HTTP 403.
- Duplicate Facebook comment webhooks are ignored.
- Page-authored comments/replies are ignored to prevent loops.
- The system does not invent financial figures.
- This version only automates public Facebook comment replies. Messenger/DM automation is intentionally separate because Meta messaging permissions and conversation-window rules differ from public Page comments.
