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
