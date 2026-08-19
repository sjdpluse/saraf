# صراف Instagram Automation V2 — Deployment Checklist

## What this version does

1. Every normal Instagram comment is answered by the صراف AI assistant.
2. Keyword comments use a deterministic route:
   - Public reply: `توضیحات به دایرکت شما ارسال شد. سپاس از وقتی که گذاشتید! 💚`
   - Private reply: professional صراف introduction + official Telegram bot link.
3. Direct Messages are answered by the صراف AI assistant.
4. DM conversation history is stored in Supabase.
5. Duplicate Meta webhook events are ignored.
6. صراف's own comments/messages and echo events are ignored.
7. AI can receive trusted live data from internal صراف services for currencies, gold and amount-specific USDT buy/sell questions.
8. The AI is explicitly forbidden from inventing financial numbers.
9. OpenRouter reasoning is excluded from API output and a second local sanitizer prevents reasoning/internal text from reaching Instagram.
10. Markdown markers such as `**`, `*`, headings and backticks are stripped before sending responses to Instagram.
11. User-facing branding is always `صراف`; `Saraf` is reserved only for technical identifiers, URLs or usernames.

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

Recommended `INSTAGRAM_DM_LINK_MESSAGE`:

```text
سلام 👋

به صراف خوش آمدید.

صراف یک سیستم هوشمند برای دسترسی سریع به اطلاعات بازار مالی افغانستان است؛ از نرخ لحظه‌یی ارزها و طلا تا مقایسه تغییرات بازار و دسترسی به خدمات مرتبط با تتر.

برای مشاهده نرخ‌های لحظه‌یی و استفاده از خدمات صراف، ربات رسمی را باز کنید:

{bot_link}
```

If `INSTAGRAM_DM_LINK_MESSAGE` is empty, V2 uses this professional message automatically. V2 also recognizes the previous short `سلام 👋 لینک ربات Saraf: ...` format as legacy and replaces it with the built-in professional صراف message.

## 3. Meta Webhooks

The callback remains:

`/webhooks/instagram`

The subscription must include at least:

- `comments`
- `messages`

## 4. AI output safeguards

The OpenRouter request uses:

```json
{"reasoning":{"exclude":true}}
```

This allows supported models to reason internally without returning reasoning tokens. V2 then applies a local sanitizer before any model output is sent to Instagram. It removes `<think>`/`<reasoning>` blocks, common internal-analysis phrases and Markdown formatting. If an output is still identified as internal reasoning, it is discarded and a safe plain-text response is used instead.

## 5. Expected tests

### Keyword comment

Input:

`صراف`

Expected public reply:

`توضیحات به دایرکت شما ارسال شد. سپاس از وقتی که گذاشتید! 💚`

Expected DM: professional صراف intro + `https://t.me/sarafiaf_bot`

### Praise comment

Input:

`خدمات شما عالی است`

Expected:

`سپاس از اعتماد شما 💚 خوشحالیم که خدمات صراف برایتان مفید بوده است.`

No reasoning text such as `We need to respond...` may be visible.

### Normal comment

Input:

`نرخ دالر امروز چند است؟`

Expected: AI receives the current صراف USD buy/sell quote as trusted context and answers briefly, without Markdown.

### Direct Message

Input:

`سلام، خدمات صراف چیست؟`

Expected: AI replies in Dari, stores both sides of the conversation and does not expose reasoning.

### Direct Message with live rate

Input:

`نرخ یورو چند است؟`

Expected: AI receives current صراف EUR data and must not invent any other figure.

### USDT quote

Input:

`خرید 100 تتر چند افغانی می‌شود؟`

Expected: V2 calls the internal `usdt_service.get_buy_quote(100)` and supplies that trusted calculation to AI.

## 6. Operational guardrails

- Do not set `INSTAGRAM_APP_SECRET` to a different Meta app's secret.
- Do not mix Facebook Page Access Token with the Instagram User Access Token used by this automation.
- Keep webhook signature verification enabled.
- Do not remove idempotency tables.
- Keep AI temperature low for financial support.
- Instagram replies are treated as plain text; do not rely on Markdown bold syntax.
