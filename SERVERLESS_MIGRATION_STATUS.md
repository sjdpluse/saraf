# Saraf — actual Telegram Serverless migration (work-in-progress)

**Branch:** `migration/telegram-native-serverless-poc` — Draft PR #41  
**Status:** REAL React entrypoint + native market services implemented; **financial production cutover is NOT safe yet**.

This is no longer only a proof-of-concept landing page: the build now uses **the ORIGINAL** `webapp/index.html`, `webapp/src/main.jsx`, `webapp/src/App.jsx`, Saraf design/assets and React components. The previous isolated test pages remain in the repo for reference only. No modifications were merged to `main`.

## Implemented in the existing source

- `webapp/vite.telegram.config.js`: builds the **original** React app for `/` on Telegram static hosting without modifying Railway's `vite.config.js`.
- `webapp/src/App.jsx`, `pages/Home.jsx`, `pages/Menu.jsx`, `components/BottomNav.jsx`: native Telegram routing, branded Home, Market page, original about/terms/JustMarkets guides. Financial pages are deliberately disabled only for the Telegram build; they are unchanged for Railway.
- `webapp/src/lib/api.js`, `nativeApi.js`, `runtime.js`: authenticated Telegram-native transport; unsupported calls explicitly fail **closed** rather than leaking initData or silently calling Railway.
- `webapp/src/pages/Markets.jsx`: live reference currency, gold, silver, crypto and public Sarai Shahzada rates, subject to upstream availability; no executable quote is issued.
- `serverless-poc/tgcloud/endpoints/getReadOnlyMarket.js`, `getLocalMarket.js`, `getMarketSnapshot.js`, `getSarafCapabilities.js`: native Telegram endpoints. Native miniapp calls use `Telegram.WebApp.Serverless.call` and Telegram validates the signed init data.
- `serverless-poc/tgcloud/lib/local_market_parser.js`, `local_market_service.js`: removes the Python BeautifulSoup dependency for public exchange rate parsing.
- `serverless-poc/tgcloud/lib/order_state_machine.js`: preserves Saraf's financial transition policy as a building block, **NOT** yet wired to payment/order changes.
- `serverless-poc/tgcloud.jsonc`: now deploys `serverless-poc/dist/`, **not** `react-dist/` or `miniapp/`.
- `.github/workflows/telegram-native-build.yml`: validates original Vite build and module syntax/tests. **No CI workflow deploys to the live bot**.

## Local build for original Saraf Mini App (PowerShell)

```powershell
cd "C:\\Users\\Niazi Wall\\Desktop\\saraf-serverless-test"
git status --short
git pull --ff-only
cd webapp
npm.cmd ci
npm.cmd run build:telegram
Test-Path "..\\serverless-poc\\dist\\index.html"
```

`Test-Path` must say `True`. This builds the **real** React Mini App into Telegram-ready static files.

Do **not** switch @BotFather's production Mini App URL or run `npx tgcloud push` against the financial production bot yet. Publishing this revision on the existing **test** bot is possible (from `serverless-poc/` using `npx.cmd tgcloud status` then `npx.cmd tgcloud push`) but the financial action buttons remain disabled by design.

## NOT implemented — blockers to safely remove Railway

1. **Existing Supabase business history**: users, identity documents, USDT/USDC orders, remittances, quotes, public reviews, card data and private storage remain on Supabase. No migration/export or backfill has occurred.
2. **Financial writes**: signed quotes bound to Telegram users, expiry and consumption, monetary rounding, order idempotency keys, risk/KYC authorization, receipt and ID uploads, admin permissions, audit, settlement, and money transfer verification.
3. **Admin bot**: separate token needs its own Telegram native Serverless project; existing `admin_bot_remittance.py` is still running via Python on Railway.
4. **Always-on scheduled jobs**: snapshot capture, Facebook/Instagram rate alerts and blockchain remittance watcher. Telegram event handlers cannot replace continuous/background polling alone.
5. **Meta public webhooks** and **Playwright**: require a separate webhook/media-rendering architecture (not hosted by the Telegram authenticated Mini App endpoint).
6. **Funding / secret policy**: No secret-bearing Supabase service role key, bank credential or private API key may be embedded in these JavaScript modules or static React files. A protected server-side secret or a proper native database migration with reconciled historical records is necessary before financial write operations can be enabled.

**Do not disable Railway or merge this draft PR as a completed migration.** Preserve and back up Supabase data. Cut over only after trade/payment reconciliation and rollback are demonstrated.

## Existing production must remain unaffected

The original `npm run build` remains Railway's `/miniapp/` build and uses its unchanged Python/FastAPI REST routes. The Telegram build is separate: `npm run build:telegram` sets `__SARAF_NATIVE__` so all unported financial actions are hidden or rejected. `bot.py`, `api.py` and `admin_bot_remittance.py` are unchanged.
