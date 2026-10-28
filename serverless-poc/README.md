# Saraf → Telegram Serverless | Safety-first migration

**STATUS: READ-ONLY TEST BOT PILOT; NOT DEPLOYED OR RUNTIME-TESTED. DO NOT DEPLOY TO THE LIVE SARAF BOT.**  
**This folder is not a full migration and is deliberately isolated from `bot.py`, `admin_bot_remittance.py`, and `api_remittance.py`.**

## Findings from the existing repo

- **Customer Telegram bot:** `bot.py` uses Python `python-telegram-bot` and `run_polling()`, extensive handlers and a `JobQueue`.
- **Admin Telegram bot:** `admin_bot_remittance.py` runs a separate polling bot with a separate token.
- **REST backend:** `api_remittance.py` + `api.py` expose FastAPI routes for rates, KYC, USDT/USDC orders, private documents, payments, reviews and remittances.
- **Mini App:** `webapp/` is React/Vite. Its `vite.config.js` uses `base: '/miniapp/'`; `webapp/src/lib/api.js` makes `fetch('/api/...')` calls.
- **Persistent business records:** `services/supabase_service.py` stores users, trade orders, KYC, remittances, currency/gold/silver history and settings in Supabase.
- **Tasks and external integrations:** `jobs.py` schedules rates and social posts; `remittance_watcher.py` polls blockchain confirmations; the Instagram/Facebook routers accept public Meta webhook calls. `services/post_image_service.py` depends on Playwright.

## Technical compatibility

Telegram's native Serverless runtime (Oct 2026) runs **JavaScript modules** in V8, not Python processes. Runtime imports are the platform SDK and project-local `.js` files only; no `python-telegram-bot`, FastAPI, npm runtime packages, Playwright, or filesystem. Handlers respond to Telegram updates, Mini App endpoints are callable by a verified user of the bot's Mini App, and native static hosting serves Vite builds on a `tgcloud.ai` host.

**Therefore: a zero-Railway migration is plausible, but a 100%-Telegram-only lift-and-shift is NOT.**

| Current component | Destination / required action |
| --- | --- |
| `bot.py`, `handlers/*` | Rewrite in `tgcloud/handlers/message.js`, `callback_query.js`, `lib/*` |
| `admin_bot_remittance.py`, `admin_bot.py` | **Separate** Telegram Serverless project for the admin bot |
| `webapp/` | Adapt Vite `base` to `/`, deploy static files from built `dist`; change API client to `Telegram.WebApp.Serverless.call(name, input, callback)` |
| FastAPI Mini App API | Rewrite sensitive logic to authenticated Serverless `endpoints/*.js` (cannot simply proxy `fetch('/api/...')`) |
| `supabase_service.py` | Initially retain external Supabase to preserve financial/KYC history. Do NOT silently switch to Telegram SQLite |
| `jobs.py` / chain watcher | Replace continuous polling with an independently scheduled runner or supported database/edge scheduler; re-check failure, delay and idempotency handling |
| Meta public GET/POST webhooks | Keep a small externally reachable endpoint (e.g. a serverless function), because Telegram Mini App endpoints only accept authenticated Mini App calls |
| Playwright/Pillow image production | Move to client-side generated assets or external stateless image renderer, not the Telegram V8 runtime |

## Safe proof-of-concept validation (use an EMPTY TEST BOT)

1. In **@BotFather**, choose a *different, disposable test bot* → **Serverless** → enable; if early access is not available, request access. Never paste a CLI token or Bot API token into GitHub or this chat.
2. Install Node.js >= 18, then from this folder run `npm install`.
3. Run `npx tgcloud login`; provide the **Serverless CLI token** from BotFather (it is different from the Bot API token).
4. Inspect local status with `npx tgcloud status` / `npx tgcloud diff`.
5. Deploy **only to the test bot** with `npx tgcloud push`.
6. Create the **test-only** SQLite table with `npx tgcloud migrate` and carefully review and confirm the migration prompt.
7. Verify `npx tgcloud webhook`, then use `npx tgcloud webhook sync` if needed. Test /start and /ping twice; counter must persist between invocations. Then test the read-only buttons for currencies, gold, silver, crypto and `/convert USD AFN 100`. No trading functionality is enabled.

## Production exit criteria (not yet met)

- [ ] Both customer and admin bot update handlers ported and tested with dedicated test bots.
- [ ] All Mini App routes ported and RPC client adapted, including receipt, private document and identity-verification uploads.
- [ ] Exact quote expiration, idempotency keys, payment state transitions, operator permissions and audit logs preserved.
- [ ] Existing Supabase order/KYC/financial records backed up and verified unchanged; least-privilege access implemented.
- [ ] Meta webhooks and price/chain schedulers running outside Railway.
- [ ] Static Mini App build loads assets from `/`, calls Serverless RPC and works inside Telegram.
- [ ] Callback-query routing, permissions, document upload, transaction confirmation, duplicate-update replay and failure/retry cases tested.
- [ ] Changeover window planned, live webhook cutover verified, and rollback tested **before** stopping Railway.

## Warnings

- Do not call `tgcloud push` against the production bot yet. The platform synchronizes/deletes modules to match your working `tgcloud/` project.
- Telegram Serverless availability is still access-controlled for some bots.
- This POC has **no trading capabilities**, accepts **no payment**, and uses its own test database table. It now ports display-only international currency rates, precious-metal reference pricing, six crypto tickers and an AFN-based converter. It deliberately does NOT claim parity with local Afghan markets or the production Saraf spread engine. External fetch behavior and real Telegram deployments have not yet been tested.
- Official docs: https://core.telegram.org/bots/serverless
