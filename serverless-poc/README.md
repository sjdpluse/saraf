# Saraf → Telegram Serverless | Safety-first migration

> **CURRENT MIGRATION TRACK (29 Oct 2026):** The actual original React Saraf frontend now builds with `cd webapp && npm run build:telegram`, and `tgcloud.jsonc` serves `serverless-poc/dist`. Historical Phase 2/3 test-page instructions below are superseded. See [../SERVERLESS_MIGRATION_STATUS.md](../SERVERLESS_MIGRATION_STATUS.md). Financial trade/transfer functions are still disabled until the payment and data migration is complete. Do not deploy this branch to the live financial bot or turn off Railway yet.


**STATUS: READ-ONLY TEST BOT PILOT. React variant added in source but not tested or deployed by the assistant. DO NOT DEPLOY TO THE LIVE SARAF BOT.**  
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


## Phase 2: test the Telegram-hosted Mini App (READ-ONLY)

This test UI is **not** the production React Mini App. It proves the static hosting + authenticated RPC workflow first, without moving customer orders or modifying Railway.

New files:
- `miniapp/index.html`, `miniapp/app.js`, `miniapp/app.css` — static test interface.
- `tgcloud/endpoints/getReadOnlyMarket.js` — Telegram-authenticated, read-only rate endpoint.
- `tgcloud.jsonc` now sets `static.source = "miniapp"` (its URL is served at `/` on the test bot's dedicated `tgcloud.ai` host).

On **the local branch linked to a disposable test bot**:

```powershell
cd "C:\\Users\\Niazi Wall\\Desktop\\saraf-serverless-test"
git status --short
git pull --ff-only
cd .\\serverless-poc
npx.cmd tgcloud status
npx.cmd tgcloud diff
npx.cmd tgcloud push
```

1. Inspect that the push preview deploys the `miniapp` static files and endpoint **only to the test bot**. It is normal that the CLI deploys changed modules.
2. Copy the exact `https://app<app_id>.tgcloud.ai/` URL printed by `tgcloud push`. Do not invent an app ID.
3. In **@BotFather** open the **TEST bot** → Bot Settings → Menu Button (or its Mini App settings), configure its URL to the new host.
4. Open the test Mini App from that bot **inside Telegram**. A normal external browser lacks signed Telegram init data, so the read-only RPC intentionally refuses to load.
5. Verify currencies, gold, silver, and crypto. Confirm no buy/sell, payments, remittances or KYC actions are present.

**No database migration is needed for Phase 2**; `schema.js` is unchanged.
**No production cutover**: leave Railway, the production bot and its Mini App URL unchanged.
**Runtime caveat**: these files have been committed but have not been tested against your Telegram bot; report CLI errors rather than attempting to deploy them to the production bot.


## Phase 3: Branded React pilot built from Saraf's actual frontend assets

**Current configuration:** `tgcloud.jsonc` now selects `react-dist` instead of `miniapp`. This is a **test-bot-only** staging change. The older HTML pilot remains in `miniapp/` as a fallback but no longer deploys after this branch is updated.

The source is under `../webapp/src/telegram-pilot/`. It reuses Saraf's real React/Phosphor setup and its original `CardCarousel`/card assets. This is deliberately **not the original trading App.jsx**: its separate read-only entrypoint does not import the Buy, Sell, KYC, Remittance or Railway REST API clients. It calls the existing, authenticated `getReadOnlyMarket` Telegram RPC endpoint and clearly labels all finance actions disabled. It does not touch Supabase.

### Build + release only to a test bot (PowerShell)

```powershell
cd "C:\\Users\\Niazi Wall\\Desktop\\saraf-serverless-test"
git status --short
git pull --ff-only
cd .\\webapp
npm.cmd install
npm.cmd run build:telegram-pilot
Test-Path "..\\serverless-poc\\react-dist\\index.html"
cd ..\\serverless-poc
npx.cmd tgcloud status
npx.cmd tgcloud diff
npx.cmd tgcloud push
```

Before continuing, ensure `Test-Path` reports `True`, and `tgcloud status` confirms you are targeting the **test** bot. Review the diff before pushing. Do not run the deploy if local changes would be overwritten by `git pull`.

After deploy, open the **already configured test-bot Mini App**. Verify:
- branded React homepage and original sliding Saraf cards load;
- currency, gold, silver and crypto reference rates load from the Telegram endpoint;
- buttons for payments, KYC, remittance, trading or customer order placement are **not present**;
- an external browser cannot fetch authenticated rates;
- Railway production bot and production Mini App still operate normally.

### Rollback the test static page

If the React pilot cannot build or works poorly, **do not change the production bot**. On your local test working tree, revert `static.source` to `miniapp` in `tgcloud.jsonc` and push to the **test bot only**. The prior test page remains in the repo.

This does **not** complete the full migration. We still need to port local Afghan market spread, financial quote/fee rules, Supabase access, secure private media uploads, financial idempotency/transaction state machine, admin bot, rate schedulers, blockchain verifier and Meta webhooks before Railway can safely be disabled.

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
