# Saraf Instagram Automation V2 — Deployment Checklist

## What this version does

1. Every normal Instagram comment is answered by Saraf AI.
2. Keyword comments use a deterministic route:
   - Public reply: `توضیحات به دایرکت شما ارسال شد. سپاس از وقتی که گذاشتید! 💚`
   - Private reply: professional Saraf introduction + official Telegram bot link.
3. Direct Messages are answered by Saraf AI.
4. DM conversation history is stored in Supabase.
5. Duplicate Meta webhook events are ignored.
6. Saraf's own comments/messages and echo events are ignored.
7. AI can receive trusted live data from Saraf services for currencies, gold and amount-specific USDT buy/sell questions.
8. The AI is explicitly forbidden from inventing financial numbers.

## 1. Supabase

Run:

`supabase/migrations/20260819_001_instagram_ai_v2.sql`

The migration creates:
- `ig_message_events`
- `ig_conversation_messages`

Do not expose either table to public clients.

## 2. Railway variables

Keep:

`INSTAGRAM_COMMENT_KEYWORDS=Saraf,صراف,سراف`

Add/verify:

```env
INSTAGRAM_AI_REPLY_ENABLED=true
INSTAGRAM_DM_AI_ENABLED=true
INSTAGRAM_KEYWORD_PUBLIC_REPLY=توضیحات به دایرکت شما ارسال شد. سپاس از وقتی که گذاشتید! 💚
INSTAGRAM_DM_HISTORY_LIMIT=8
INSTAGRAM_AI_COMMENT_MAX_CHARS=350
INSTAGRAM_AI_DM_MAX_CHARS=900
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=google/gemma-4-31b-it:free
OPENROUTER_FALLBACK_MODELS=openrouter/free
TELEGRAM_BOT_LINK=https://t.me/sarafiaf_bot
```

If `INSTAGRAM_DM_LINK_MESSAGE` currently exists in Railway and you want V2's built-in professional message, delete that variable. Otherwise its Railway value intentionally overrides the built-in text.

## 3. Meta Webhooks

The callback remains:

`/webhooks/instagram`

The subscription must include at least:

- `comments`
- `messages`

Railway logs already showed `entry.messaging` events reaching the webhook, so the delivery path exists. V2 adds the parser/AI handling that the old code lacked.

## 4. Required Instagram permissions

The Meta app/token must have the permissions required by your Instagram Login configuration for:

- comment management/replies
- messaging/DM management

The exact permission names and review requirements should be checked against the current Meta dashboard/API version before production release.

## 5. Expected tests

### Keyword comment

Input:

`صراف`

Expected public reply:

`توضیحات به دایرکت شما ارسال شد. سپاس از وقتی که گذاشتید! 💚`

Expected DM: professional Saraf intro + `https://t.me/sarafiaf_bot`

### Normal comment

Input:

`نرخ دالر امروز چند است؟`

Expected: AI receives the current Saraf USD buy/sell quote as trusted context and answers briefly.

### Direct Message

Input:

`سلام، خدمات صراف چیست؟`

Expected: AI replies in Dari and stores both sides of the conversation.

### Direct Message with live rate

Input:

`نرخ یورو چند است؟`

Expected: AI receives current Saraf EUR data and must not invent any other figure.

### USDT quote

Input:

`خرید 100 تتر چند افغانی می‌شود؟`

Expected: V2 calls Saraf's own `usdt_service.get_buy_quote(100)` and supplies that trusted calculation to AI.

## 6. Operational guardrails

- Do not set `INSTAGRAM_APP_SECRET` to a different Meta app's secret.
- Do not mix Facebook Page Access Token with the Instagram User Access Token used by this automation.
- Keep webhook signature verification enabled.
- Do not remove idempotency tables.
- Keep the AI temperature low for financial support.
