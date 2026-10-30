## 2026-10-30 — Original admin completion media backend deployed safely (latest)

- Migrated ORIGINAL `admin_bot.py` image / document Transaction Details path:
  signed original administrator in the original React Mini App may upload
  JPG/PNG/WEBP or PDF (<=8 MB), which the gated original Supabase Edge admin
  function posts to the SAME original customer bot's Telegram API to obtain
  a usable native Telegram `file_id`. The 10-minute HMAC attestation binds
  this bot file ID to the specific original order and original admin. It
  cannot grant order completion without the separately private admin RPC.
- Changed staged `saraf_original_admin_finalize_order` to accept either
  original transaction text or real Telegram media proof in the existing
  `usdt_orders.completion_proof_file_*` columns, inside the same atomic
  financial status transition with existing audit and trust profile. Includes
  PostgreSQL test cases rejecting empty, malformed or cross-origin fake
  proof and confirming idempotency.
- The admin UI uploads original media and only offers payment completion
  when supported text or an order-bound 10-minute proof has been supplied.
  The completed-order notification sends the media to the customer using
  that original Telegram bot identity.
- The canonical Supabase project `cvernmhpnsgdtegvblyc` **admin Edge
  version 2 was actually deployed and fetched back** with `index.ts`,
  `telegram-auth.mjs`, `proof.mjs` and `proof-upload.mjs`. Runtime
  still requires existing PRIVATE administrator allowlist,
  `SARAF_ORIGINAL_ADMIN_READ_ENABLED` and
  `SARAF_ORIGINAL_ADMIN_WRITES_ENABLED` before any admin RPC or upload.
  No private feature flags were switched on.
- GitHub branch code SHA `0b709259b` passed all five CI workflows,
  including isolated PostgreSQL admin/media proof invariants, Deno
  build, original React, Python and public negative checks. No original
  Telegram Serverless webhook was switched and no live payment or
  customer row was touched.

**Still blocked:** The staged 7-parameter admin media financial RPC is not
yet applied to canonical production, and the full set of customer financial
Edge functions / release must be reconciled and end-to-end tested with the
actual original Telegram bot before private feature enablement. Cron/
Meta automation has not been cut over. Admin feature flags remain OFF,
so production operations cannot be performed from the new Mini App.

## 2026-10-30 — Signed full original Saraf Serverless CANDIDATE built (latest)

**Not a production cutover.** The ORIGINAL @sarafiaf_bot webhook and
Railway deployment have not been replaced. All full-money and KYC services
remain independently gated by PRIVATE Supabase feature flags; no live money
or customer tables were altered by this branch.

### Completed real migration work in this branch
- Original 1200×760 in-person visit-pass PNG and 1320×900 original
  customer order-preview PNG now render locally in the original React
  Telegram Mini App; no Railway image service or pass-download URL.
  The customer card validates signed owner/active quote and configured
  chain address in the gated Supabase Edge before rendering, uses fully
  local MIT-licensed QR encoding, and can include a 60-second **owner-only**
  signed KYC selfie. The local pass uses explicit download confirmation
  on browsers without the File System Access API.
- Original old `usdt_*` Telegram callback messages safely route to
  signed Telegram Mini App, and the original 5-star rating callback
  links directly to the original `orders` route, which now supports
  `?action=orders`. No unsigned financial transitions.
- Canonical original Supabase KYC profile reports the original configured
  USD threshold and uploads enabled flag (both private settings); original
  KYC upload refuses sensitive documents without a configured admin.
- Signed original administrator Mini App covers pending customer KYC,
  90-second privately signed admin-only ID/selfie previews, verified/rejected
  transitions, original restricted reason and canonical audit history.
  Existing `public.user_profiles` and `public.audit_log` only.
- Signed original administrator order tools include /usdtconfirm,
  original reject, and proof-gated manual completion (Tx Hash / transaction
  details 4–2000 chars required) using the original allowed states and
  the original trust score/counter formula. Idempotent and auditable.
- Signed original remittance admin tools include the original
  transfer_submitted→payout_ready / hold / cancel and
  payout_ready→completed transitions; code matching enforced
  server-side using the **original six-digit beneficiary pickup code**.
  The private code is delivered to the customer when payout_ready and is
  **never returned in admin HTTP JSON**. Original blockchain confirmations
  and beneficiary ID are shown in the signed admin inbox. Payout is a
  manual operator decision after ID and crypto receipt verification.
- The staged original remittance SQL code now generates pickup codes
  using PostgreSQL cryptographic UUID entropy, instead of predictable
  SQL `random()`. No new wallet, payment product, duplicate customer
  ledger, or cash settlement automation.
- Original admin/customer Telegram alerts after successful canonical
  order creation, submission, verification and settlement mirror the
  original status messages; duplicate/idempotent retries do not resend.
- Added `webapp/.env.telegram-original-full` and the explicit
  `npm run build:telegram-original-full` script to compile the FULL
  signed original customer/KYC/admin/remittance UI without falling back
  to Railway. It contains **public boolean build flags ONLY**.
- Updated the existing CI workflow to produce TWO completely separate
  audited artifacts: `saraf-original-serverless-preview` (read-only)
  and `saraf-original-full-migration-candidate` (full signed
  React transport). This is a build only, **no tgcloud push**.

### Actual automated validation
GitHub Actions run **41018854979** on commit `e19126d1a` completed
all five checks successfully: isolated PostgreSQL original finance/admin
and money idempotency tests, Python remittance, React UI,
Telegram native Deno/full-candidate build, and deployed public negative
security tests. The full candidate artifact was uploaded to the run.
Later source-only documentation changes do not imply live cutover.

### Hard remaining production blockers (do NOT claim ready)
1. The exact CURRENT migration code for all signed Supabase Edge functions
   and all service-role-only staged SQL RPCs has **not** been deployed /
   migrated into the canonical production project. Never turn on server-side
   financial/KYC/admin feature flags before signed real-bot end-to-end
   testing and private admin review.
2. The full Telegram Serverless candidate is **not yet published** to the
   original BotFather-controlled bot, and the current main-branch release
   workflow intentionally rejects `publish` until full parity. This
   rollout requires the BotFather CLI credential and real signed
   initData tests with **the ORIGINAL bot**, verified funds and backup.
3. Completion media upload and sending original transaction details
   photos/documents to customers, original separate admin bot
   inline-keyboard UX, and original chat-side KYC photo-conversation
   require further exact parity (the signed Mini App already supports
   valid text Tx details and image-based KYC).
4. Cron market snapshots / social posts and Meta webhook queue/worker
   are staged Railway-free but disabled pending private credentials,
   original platform webhook reconfiguration, reliability, and rollback
   tests. These schedules will not run from a nondefault PR branch.
5. Real canonical KYC storage, user ownership, wallet/deposit
   reconciliation, manual cash payout and irreversible completed-order
   paths have **synthetic** tests only; no live financial transactions
   were generated or approved during migration.

**Release safety:** Do NOT silently switch away from Railway or merge an
incomplete release. Preserve old webhook and customer records until
these checks are explicitly green for the exact original bot, then
perform a reversible cutover.

## 2026-10-29 — original remittance RPC integration and production readiness (latest)

- Repaired the isolated PostgreSQL 16 fixture to include canonical
  `asset_price_usd` and `usd_value` columns (verified read-only against
  the real Supabase schema); original order/remittance CI is green.
- Preserved the complete ORIGINAL `api_remittance.py` -> `remittance_v2.py`
  15-asset registry, optional V2 exposure flag, original network aliases,
  configured wallet precedence and CoinGecko pricing aliases (including
  WBTC/BTCB -> BTC and WETH -> ETH). No new asset or custom settlement
  policy was introduced.
- Prevented the original V2 financial bug in the staged port where
  `USDT=1 USD` was assumed for ALL tokens. Price comes from server-side
  CoinGecko, and the quote is saved to canonical existing remittance
  `asset_price_usd` and `usd_value` fields. Original 30s worker price
  cache now exists, without stale payout quotes.
- Made independent CoinGecko and live AFN FX fetches concurrent to
  keep original signed Mini App requests inside the 18s client timeout.
  Uses Decimal-compatible ROUND_HALF_UP for the USD display/identity
  value rather than JS Math.round.
- The originally configurable
  `USDT_IDENTITY_VERIFICATION_THRESHOLD_USD` is now enforced consistently
  by the signed Edge handler and staged SQL RPC; neither token quantity
  nor a hardcoded threshold may bypass original KYC policy.
- Added pure V2 registry and value regression tests and isolated PG16
  integration tests proving owner isolation, asset/network whitelist,
  BTC KYC USD threshold, idempotency, audit history and pickup privacy.
  These tests never use production credentials.

**Production remains blocked** pending faithful in-person PNG pass/download,
KYC selfie/order-card rendering and notifications, exact chat USDT/USDC
callback coverage, separate admin settlement workflow, signed media
and customer money E2E tests, scheduled original jobs/Meta, BotFather
deployment and rollback rehearsal. No production finance data or webhook was
changed in this commit series. Read-only bridge deployments are unrelated
to financial activation, and green synthetic CI alone is insufficient.

## 2026-10-29 — original V2 remittance provider, network and valuation parity (latest)

- Inspected ORIGINAL `api_remittance.py`, `remittance_v2.py`,
  `remittance_asset_registry.py`, `remittance_wallet_config.py`,
  `remittance_price_service.py`, and `money.py` in `main`.
  The production API installs the original V2 quote function even when
  optional V2 asset exposure is disabled.
- Ported the **15 original asset types** and their exact supported networks,
  including the existing `SOLANA -> SOL` and `BTC -> BITCOIN` normalizations,
  into pure Edge-compatible `remittance.mjs`. Wrapped BTC/ETH pricing aliases
  reproduce original CoinGecko IDs. Optional V2 assets stay OFF unless
  `REMITTANCE_V2_ENABLED=true`, same as the original wallet registry.
- Ported configured original `REMITTANCE_WALLETS_JSON` and the
  `REMITTANCE_<ASSET>_<NETWORK>_WALLET` fallback, with no hardcoded
  additional recipient wallets or fake payout addresses. Missing wallets
  are not offered.
- Replaced the **incorrect $1-per-token assumption** in the staged signed
  remittance Edge handler with server-fetched CoinGecko USD price, original
  fee percentage, USD-converted amount limits and Decimal-compatible rounding;
  stored the original price and USD value in the existing
  `public.remittance_orders` columns. Financial write flag remains OFF.
- Extended the **staged canonical RPC** to accept only the original 15
  assets on the original allowed chain list. SQL isolation tests prove that
  **0.01 BTC at $40,000 triggers the $250 KYC threshold** (not raw token
  amount), while the verified synthetic account can create its own order.
  Original idempotency, TX ownership, private pickup code and audit tests
  remain in place.
- Ran the original financial migration test workflow in an isolated
  PostgreSQL 16 container, plus Deno typechecking, React build and native
  menu tests. See GitHub Actions for the exact per-commit green verdict.

**Still NOT production complete**: exact original in-person pass (PNG download),
signed preview/customer selfie and order-card media, chat-side financial
callbacks, separate admin bot operations/settlement and customer alerts,
end-to-end private file upload/receipt/beneficiary access, scheduled
snapshots and Meta automation reliability, and a verified rollback/cutover.
No live finance RPC was installed, no finance secrets were activated,
the original bot webhook was untouched, and the release publish guard
must remain active.

## 2026-10-29 — original remittance valuation preserved (latest)

- Inspected the **existing production Supabase schema read-only** using the
  Supabase connector; confirmed that `remittance_orders` already contains
  `asset_price_usd`, `usd_value`, `verification_status`, and the existing
  audit/status history columns. No production rows or schema were changed.
- Corrected the staged original remittance RPC to retain
  `asset_price_usd` and `usd_value` on the **same canonical record**, and
  to check the $250 original identity threshold on **USD value**, not on raw
  cryptocurrency quantity. The signed Edge action now supplies those
  arguments and checks owner KYC at USD value > 250.
- Extended isolated PostgreSQL 16 synthetic fixtures to call the revised
  RPC signature; added static regression checks to prevent silent removal of
  the canonical USD-value fields. No new ledger, bank details or wallet
  addresses have been created.

**Scope warning:** This change preserves the already-staged USDT/USDC
remittance pathway only. Existing main:services/remittance_v2.py supports
additional opt-in assets and networks with CoinGecko USD conversion; these
are **not** yet supported by the gated serverless Edge function. Do NOT
activate financial writes or remove the release gate until full parity,
verified upstream prices/wallets, payout approval, admin bot notifications,
media handling, and signed original-bot end-to-end testing pass.

## 2026-10-29 — original calculator and broadcast command parity (latest)

- Restored ORIGINAL `handlers/currency.py` bid/ask calculator semantics
  in Telegram ForceReply: selling foreign currency multiplies the Saraf
  **buy** rate, and buying multiplies its **sell** rate; Sarai Shahzada
  local quote appears separately when available. This replaces the
  incorrect global reference-only calculation.
- Extracted pure parity `legacy_calculators.js` for existing gold and
  silver calculation rules and original rounded per-gram USD/AFN values.
  Original silver now retains **four decimal USD per gram** before applying
  the established making charge/deduction. Regression tests cover
  18k/24k, bid/ask direction, local unavailability and input rejection.
- Fixed original profile/history bot replies that displayed literal
  `\\n` instead of line breaks.
- Original `/broadcast` now opens the already-built signed original
  admin Mini App composer, with limited optional message prefill and
  required second confirmation; the chat command never independently
  sends messages or bypasses the server-side OFF flag / admin allowlist.
- Added the calculator module to the strict Telegram Serverless
  preview release allowlist; still **no new ledger or finance handler**
  in the uploadable release.

**Remaining blockers are unchanged:** full original financial chat callbacks
and admin/KYC media, customer financial notifications and card assets,
multi-asset remittance/payout 1:1 semantics, scheduled jobs and Meta
automation reliability, live original-bot signed full-path testing,
backup/rollback rehearsal and production cutover. Synthetic CI and static
builds are not proof of a fully migrated operating service. Production
publish and webhook switching remain BLOCKED.

## 2026-10-29 — original admin command migration (this increment)

- Added signed Telegram Mini App admin page in original React navigation and
  preserved `/stats`, `/spreads`, `/setspread`, `/usdtpending`,
  `/usdtconfirm` command names in native Telegram handlers.
- The bot ONLY provides a link to original Mini App for privileged commands;
  unsigned `message.from.id` is NEVER forwarded as an authenticated finance
  actor. The new server-side `saraf-original-admin` Edge Function validates
  actual Telegram Mini App HMAC and the PRIVATE
  `SARAF_ADMIN_CHAT_IDS` allowlist. Read and write have independent
  OFF-by-default server-side toggles
  `SARAF_ORIGINAL_ADMIN_READ_ENABLED` and
  `SARAF_ORIGINAL_ADMIN_WRITES_ENABLED`.
- Added staged service-role-only original existing-table admin SQL RPCs for
  one-time order confirmation and spread updates, with order state-machine
  checks and audit history; **no SQL installed on live canonical Supabase**.
- Synthetic PostgreSQL 16 admin safety tests PASS; original React/Telegram
  native build and Deno module validation PASS. No customer finance rows
  touched. Deployed `saraf-original-admin` Edge **ACTIVE v1, disabled**.
- `/broadcast` remains deliberately OFF until an owned, consent-aware
  delivery pipeline is tested. The legacy chat-photo KYC/receipt workflows,
  full financial callback flows, social-trigger reliability, and the complete
  original FastAPI/JustMarkets utilities are not yet 1:1.
- **Production release is STILL BLOCKED**; do not remove Railway or switch
  BotFather webhook because compile and synthetic tests are not real live
  signed-user/admin/financial parity.

## Additional Railway removal work (2026-10-29)

- Created a **disabled-by-default** original Facebook/Instagram Meta HTTP
  webhook receiver at `supabase/functions/saraf-original-meta-webhook/`.
  It verifies Meta `X-Hub-Signature-256` over raw payload bytes,
  supports original GET handshake, and only enqueues events for the
  unchanged original Python Facebook comment / Instagram comment and DM
  processors. The receiver is **deployed ACTIVE v1** but still OFF without
  `SARAF_ORIGINAL_META_WEBHOOKS_ENABLED=true`.
- Added `supabase/sql/saraf_original_meta_transport_STAGED.sql` with a
  private, locked, de-duplicated Meta event queue and retryable leases. This
  SQL has **NOT** been applied to production.
- Added `scripts/run_original_meta_worker.py` and a default-OFF GitHub
  Actions workflow invoking unchanged Python Meta handlers without Railway;
  no Meta credentials were installed or AI replies transmitted.
- Added synthetic PostgreSQL CI for queue ownership/permissions,
  duplicate deliveries and lease/retry behavior, plus real HMAC tampering
  tests for the webhook implementation. GitHub tests pass.
- Original scheduled rate and social-post Python code has an additional
  disabled GitHub Actions scheduler on the migration branch. GitHub
  scheduled workflows only operate after the branch is merged to the
  default branch, properly configured and enabled; timing is best effort.
- Full Telegram inline financial chat callbacks, administrator command
  parity, original Media/photo flows, signed production Telegram session
  test, final BotFather/TGCloud deployment, and safe rollback still
  remain incomplete. **Do not switch the original webhook or disable
  Railway yet.**

## 29 October 2026 — existing finance and Railway replacement progress

- **Original finance backend staged**: `supabase/functions/saraf-original-transactions/`
  ports the existing original USDT/USDC quote logic, the original 50/30/20
  pricing, original networks, quote persistence in existing `usdt_quotes`,
  original buy/sell requests and remittance create / submit TX into existing
  `usdt_orders` and `remittance_orders`. Original React API calls are routed
  through a single feature-gated signed Telegram Supabase adapter.
- **Synthetic atomic PostgreSQL tests PASS** for original quote ownership,
  one-use consumption, 5-digit order references, idempotent retries, KYC
  threshold, remittance receiver privacy, and TX ownership. Tests run
  exclusively against disposable PG16, **not actual customer records**.
- `saraf_original_usdt_order_rpc_STAGED.sql` and
  `saraf_original_remittance_rpc_STAGED.sql` use existing financial tables.
  **These SQL functions have NOT been deployed to production Supabase.**
- **Deployed as disabled Supabase Edge Functions** (ACTIVE means serving a
  disabled response when the feature flag is false):
  `saraf-original-transactions` v1,
  `saraf-legacy-kyc` v1,
  `saraf-legacy-uploads` v1.
  Original bot HMAC signature verification is required, and separate
  server-only enablement secrets default to **OFF**:
  `SARAF_ORIGINAL_FINANCIAL_API_ENABLED`,
  `SARAF_ORIGINAL_KYC_ENABLED`, and
  `SARAF_ORIGINAL_UPLOADS_ENABLED`.
  **Deployed does NOT mean enabled or safe for live financial traffic**.
- Existing React frontend financial route remains OFF unless
  `VITE_SARAF_ORIGINAL_TRANSACTIONS_ENABLED=true` at build time.
  Never enable without the original SQL functions and full E2E validation.
- Original Python `jobs.py` can now execute through an ephemeral GitHub
  Actions runner using unchanged business logic and original provider
  credentials; its scheduled job workflow defaults OFF and is untested with
  real Meta tokens. This is not a guarantee of reliable cron timing.
- Full original Telegram bot admin commands, all media flows, Meta
  HTTP webhooks and media/card generator behavior are **not** completely
  migrated. Do not switch @sarafiaf_bot webhook or publish production
  while these differences remain.
- The original 50 previous orders and all historical customer records
  remain unchanged in the canonical Supabase project.

**Status: INCOMPLETE migration, production publish remains BLOCKED.**

## Verified deployment update — 2026-10-29
- A NEW, read-only, public-market-data-only Supabase Edge Function
  `saraf-public-history` was deployed to the existing canonical project
  `cvernmhpnsgdtegvblyc` (ACTIVE v1). It exposes only historical exchange,
  gold, local market pricing, and stored currency spread percentages; no
  customer identities, KYC, wallets, orders, or transfers.
- The original @sarafiaf_bot **webhook has not been switched**. The Telegram
  Serverless handler deployment is still blocked by the incomplete
  original financial workflows and external Meta automation parity.
- Staged JavaScript replicas of original fixed-point stablecoin pricing,
  original Saraf bid/ask spreads and 1/7/30/90-day comparison handlers are
  committed, with no permission for client-side financial order writes.
- Supabase Edge deployment returned ACTIVE, but an end-to-end HTTP
  verification could not be performed from the current network.
- NEVER describe this as a fully migrated trading/settlement system.
  Existing records were left untouched.

## Latest migration-only progress — original parity (2026-10-29)

- Pure fixed-point `legacy_stablecoin_pricing.js` now reproduces the
  EXISTING Python `money.py` and `usdt_service.py` 50/30/20 supplier/Saraf/
  customer breakdown, USD/Afghani rounding and original remittance fee maths.
  It performs **no** order, balance or payout writes. Regression tests included.
- `legacy_rate_engine.js` reproduces original Sarai Shahzada-first reference
  rate selection, spread defaults, historical local-first logic and original
  USD-only threshold for social auto-post decisions.
- `legacy_live_rates.js` now uses that original spread + local market
  logic for the Telegram bot's `cur:` callbacks rather than falsely showing
  only global reference prices.
- `legacy_compare.js` restores the original 1/7/30/90-day comparison flow.
  A **staged** public-price-only Supabase Edge function
  `supabase/functions/saraf-public-history/index.ts` reads **only**
  `currency_history`, `gold_history`, `local_market_history` and
  `spread_settings`; it does not query customer/finance/KYC data.
  This new Edge function has **NOT** been deployed.
- Supabase Telegram history bridge source was restricted from any
  `app*.tgcloud.ai` origin to the original
  `https://app8533795882.tgcloud.ai` host. The patched source is staged
  in GitHub, NOT deployed to the live bridge.
- The Telegram build packaging includes required callback, legacy rates
  and historical comparison modules; tests run on GitHub without cloning.
- This migration retains original history and UI; current production
  trading endpoints still explicitly fail closed pending exact original
  order/quote/callback state-machine port and live end-to-end testing.

**NO complete Railway exit can be claimed while financial endpoints,
admin commands, background jobs, Meta webhooks and complete signed original
Telegram Mini App session tests remain unfinished.** The production
BotFather webhook and existing customer data have not been changed.

## Follow-up migration changes (same original functionality, no new finance)

- Removed the previously invented `saraf-finance` Edge Function, chain
  watcher, two-operator payout SQL, new quote/remittance schema, rate limiter,
  speculative financial UI adapter, its CI suite and finance rollout notes
  from the migration branch. Those were not requested and do **not** belong
  in a faithful Railway exit. No historic database row was changed.
- Restored original customer financial paths to an explicit `NOT_MIGRATED`
  response; unlike the prior speculative connector, this does not replace
  the established financial calculations or quietly create an alternate
  set of orders.
- Ported the original **reviews manager reply** to the existing owner-signed
  Supabase bridge (requires secret `SARAF_ADMIN_CHAT_IDS` to match Python's
  admin allowlist) and restored the original review character limits and
  comment cooldown. This revised bridge is staged in GitHub, **not live**.
- Added **original** KYC document/selfie multipart workflow to the existing
  `usdt-kyc-docs` private storage bucket, and original 24-hour signed
  receipt URLs / remittance beneficiary document paths, via staged Supabase
  Edge adapters. These are **disabled by default** and not deployed.
  Original admin review/Telegram document-photo workflow and full
  end-to-end document security verification must pass before enabling.
- The original React forms route to the staged adapters without switching to
  Railway. For unsigned or unported actions, clients fail closed. Public
  bot-user secrets remain on server-side only.
- The GitHub Telegram native CI now type-checks the staged Edge functions;
  the actual original bot remains untouched and publishing is still blocked.

**Still incomplete:** original live trading and remittance quote/settlement
semantics; admin commands, Telegram-native KYC chat, historic local spreads,
scheduled snapshots and Facebook/Instagram jobs/webhooks. These require
literal porting of existing Python services and parity/e2e testing. A working
build of React or a staged upload route does not fulfill this exit criterion.

## Migration-only changes completed on this branch (2026-10-29)

This update restores existing behavior rather than adding products:

- Reverted the read-only replacements of the ORIGINAL React `App.jsx`,
  `Home.jsx`, `Menu.jsx` and `BottomNav.jsx`. Original buy, sell, KYC,
  orders, remittances, reviews and JustMarkets screens remain visible in the
  React source. Their API operations are **not yet fully migrated**, so this
  is preview-only and cannot be presented to paying customers as complete.
- Ported original `keyboards.py` labels and callback_data into
  `serverless-poc/tgcloud/lib/legacy_menus.js`. Added JavaScript handlers for
  original about/currency/gold/silver/converter callbacks, including numeric
  amount reply prompts. Historical comparisons and transactional flows remain
  pending; visible rate data is still international reference pricing, not
  equivalent to original Saraf local bid/ask spreads.
- Restored original USDT/USDC and JustMarkets Mini App deep links on the
  original @sarafiaf_bot Telegram-hosted URL.
- Updated the no-clone preview packager to include callback_query handler and
  calculators. The CI artifact `saraf-original-serverless-preview` now holds
  only this allowlisted deployment package, **not the experimental shadow
  finance modules**.
- Adapted the **staged** Supabase bridge history response to original
  `REM-000001` codes, owner TxID and status-dependent pickup-code visibility.
  This edited Edge source is **not yet redeployed** to Supabase.
- Tests for original bot keyboard callbacks and original React page coverage
  pass in GitHub Actions.

**Unported:** full original Python banking and USDT/USDC workflows,
file uploads/KYC, all admin commands and moderation, background schedules,
Meta inbound webhooks, historical local-rate comparisons, original bot
persisted user state, full FastAPI response compatibility.

The `main` workflow still **blocks publish** and does not replace the
original bot's webhook. A CI build or downloaded preview zip is not a
working complete replacement for the legacy Railway service.

# SARAF — SCOPE RESET: MIGRATION ONLY (29 Oct 2026)

## Original user request

Move **the existing original** `@sarafiaf_bot` **and the existing React Mini App**
off Railway and onto **Telegram Serverless**, retaining every already-existing
feature and data. The user did **NOT** request new financial products, a new
ledger, new bank payout controls, new commission calculations, new screens,
or a read-only replacement. A Python-to-JavaScript/TypeScript port of existing
handlers and FastAPI routes is a **migration activity**; inventing new business
behavior is not.

The original source of truth is still the `main` branch (Python bot,
FastAPI backend, existing React), not the incomplete read-only pilot.

## Required exact feature parity from ORIGINAL main

| Original functionality | Existing original files | Current Telegram-only release |
| --- | --- | --- |
| `/start`, `/about`, `/stop`, help, full keyboard | `bot.py`, `handlers/start.py`, `keyboards.py` | **Partial**; original menu layout and routes changed |
| Currency/gold/silver/crypto rates, calculator, converter | `handlers/{currency,gold,silver,crypto,converter,compare}.py` | **Partial**; new reference-rate flows differ |
| Inline button callbacks | `bot.py`: `about:`, `cur:`, `curcalc:`, `gold:`, `goldcalc_mode:`, `goldcalc_karat:`, `silvercalc_mode:`, `cmp_target:`, `cmp_period:`, `convfrom:`, `convto:`, `convamt:`, `usdt_*` | **Missing** `tgcloud/handlers/callback_query.js` entirely in release |
| User profile, contact, KYC, images, USDT/USDC buy/sell | `handlers/kyc.py`, `handlers/usdt.py`, `api.py`, `services/usdt_*py` | **Not equivalent**; original React buy/sell and KYC pages explicitly blocked |
| Orders/history, ratings, reviews | `api.py`, `services/reviews_api_extension.py` | Supabase history/reviews **partially bridged**, requires signed original-bot e2e tests |
| Remittances (quote, create, TX, docs, history) | `services/remittance_api_router.py`, `services/remittance_*py` | **Not equivalent**; original React remittance page explicitly blocked |
| In-person codes, stablecoin preview/card, payment configuration | `services/stablecoin_api_extension.py`, `services/card_service.py` | **Missing** from release |
| Original bot admin (/broadcast,/stats,/setspread,/spreads,/usdtpending,/usdtconfirm) | `bot.py`, `handlers/admin.py` | **Missing** from release |
| Original scheduled snapshots and local market refresh | `jobs.py` | **Not fully ported** |
| Original scheduled Facebook & Instagram posting | `jobs.py` and `services/*instagram*py`, `services/*facebook*py` | **Missing** |
| Meta/Instagram/Facebook inbound webhooks | `api.py`, `services/*webhook_router.py` | **Missing**; Telegram handlers cannot directly replace unauthenticated Meta HTTP webhook endpoints |
| Existing historical customers/KYC/orders/remittances | Existing Supabase | **Preserve as-is**; no new ledger, no fabricated user data |

## Correction made now

The GitHub Actions workflow on `main` named
`Saraf migration preview ONLY – full parity pending (do not publish)`
**explicitly blocks publish**, before `tgcloud push` or webhook sync.
This prevents accidental replacement of the original functioning bot
with the significantly reduced, read-only pilot.
Preview remains available for diagnostic comparison.

The earlier Draft PR #41 includes prototype-only work that **must not be
mistaken for a finished migration**. The staged speculative finance SQL
and new financial workflows are **OUT OF SCOPE** for the user's request:
they must not be deployed, added to the release, or used to change historical
financial status. They should be excluded/removed from the migration PR once
the faithful port is complete.

## Technical fact

Telegram Serverless executes **JavaScript (V8)** modules, not the original
Python `python-telegram-bot` or FastAPI processes; its Mini App static
host does not run Python HTTP API routes, recurring Python jobs, or external
Meta webhook HTTP receivers. Therefore the faithful route to removing
Railway is:

- Existing React Mini App → build and host on Telegram Serverless.
- Existing Telegram bot handlers/updates → port to Telegram JS handlers,
  including ALL original message and callback flows.
- Existing Python FastAPI backend routes → compatible JS/TypeScript endpoints
  on Telegram and/or secured Supabase Edge Functions **with identical
  semantics, response shapes, ownership rules and existing data**.
- Existing recurring tasks and non-Telegram external HTTP webhooks →
  appropriate Supabase Cron and Supabase Edge Functions; Railway eliminated.
- Existing Supabase DB, private document storage and business logic →
  preserve unchanged unless a **necessary compatible migration** is reviewed.
- Original Telegram BotFather serverless credentials and link → same
  `@sarafiaf_bot`, never change username or silently replace user accounts.

## Exit criteria for production publish

A release is READY only after **all original bot commands/callbacks,
all actual Mini App screens and FastAPI routes, scheduled tasks, external
webhooks, private uploads, admin controls and money flows** have verified
end-to-end parity against the original Python implementation and a rollback
path has been rehearsed. A GitHub build success or a read-only preview is NOT
proof of parity.

**Current status: NOT READY; NO BOT PUBLISH AUTHORIZED.**
