# Saraf — canonical Supabase integration for the original Telegram bot

**Last updated:** 2026-10-29  
**Status:** IMPLEMENTED IN DRAFT GITHUB BRANCH; **NOT DEPLOYED** to either the production Telegram bot or Supabase Edge Function.

## Source of truth

The verified original Supabase project is `cvernmhpnsgdtegvblyc`, status `ACTIVE_HEALTHY`.
It already contains historical records. SQL count checks (not exports) found:

| Table | Rows | Purpose |
|---|---:|---|
| `users` | 5 | Bot users |
| `user_profiles` | 20 | Customer contact/KYC references |
| `usdt_orders` | 50 | Existing financial orders |
| `remittance_orders` | 10 | Existing remittance records |
| `usdt_quotes` | 397 | Past trading quotations |
| `miniapp_reviews` | 8 | Customer reviews |

**Zero historical records were migrated or modified.** Orders/statuses are maintained where they already are.
Native Telegram SQLite tables from earlier POC are **NOT** canonical. The bot will not show fake
"zero order" history from these tables.

Existing Supabase storage buckets `usdt-cards`, `usdt-kyc-docs`,
`usdt-receipts` are private. Keep them private; do not expose private keys or document URLs
from the browser or Telegram Serverless JS modules.

## What has been implemented in GitHub

1. `supabase/functions/saraf-telegram-bridge/index.ts`: Edge Function that verifies
   Telegram Mini App signed `initData` against the **original** bot token.
   Each read and permitted profile/review write is scoped by the verified Telegram user ID.
   It never accepts a user ID from the browser for authorization.
2. `supabase/functions/saraf-telegram-bridge/telegram-auth.mjs`:
   isolated HMAC validation; checks signature, date, duplicate keys and numeric user ID.
   Security tests run via `serverless-poc/tests/supabase_bridge_auth.test.js`.
3. `webapp/src/lib/supabaseBridge.js`: frontend adapter sends only signed `initData` and
   action payload to the trusted Edge Function. No Supabase key or bot token is in static assets.
   The adapter **fails closed** until `VITE_SARAF_CANONICAL_BRIDGE_ENABLED=true` is configured at build time.
4. `webapp/src/lib/api.js` now routes actual profiles, history, public stats, ratings and
   reviews to Supabase, rather than the parallel Telegram SQLite database.
5. Original React Mini App includes `NativeAccount` and `NativeHistory` read-only
   history pages and menu links. Sensitive document collection remains disabled.
6. The customer Telegram message handler no longer shows misleading order/profile history
   from empty Telegram SQLite tables.
7. GitHub CI builds original React, tests the HMAC verifier and checks the Deno Edge Function.
   The CI does not deploy any production service.

## Deployment confirmed — 29 October 2026

The owner reports registering the ORIGINAL Saraf bot token in Supabase Edge secrets.
A connector check **independently confirmed**:

- `saraf-telegram-bridge` exists, `ACTIVE`, version 1.
- `verify_jwt = false` (only this new function; it performs its own HMAC verification).
- Deployed `index.ts` contains the Telegram HMAC verifier and no financial execution actions.
- GitHub Actions made two real, non-destructive HTTP calls to the live endpoint:
  unsigned and forged initData were both rejected with 401 (successful CI check).
- The existing React Mini App has a new explicit build mode:
  `cd webapp && npm run build:telegram-original`.
  That mode enables the browser's *public* Supabase bridge call, **without**
  ever including the bot token or service-role key in static assets.
  The `build:telegram` mode remains for isolated tests with the bridge disabled.
- GitHub CI verified the original-bot build, HMAC tests, React tests and
  Python remittance tests without deploying or modifying financial records.

**Remaining gate:** authenticated, owner-scoped reads must be exercised with
a real, fresh `initData` signed by the ORIGINAL bot, and only then may the
original bot Mini App URL switch to Telegram-hosted static assets.
The original bot has NOT been deployed or moved by the assistant;
we do not have the native Telegram cloud bot deployment credentials.

**No changes to financial orders, remittances, Vault secrets or KYC document
storage were made by these checks.** Financial writes and identity uploads
remain explicitly disabled.

## Identified original bot and no-clone release path

The owner identified the **original Saraf bot** as `@sarafiaf_bot`.
The **main** branch now contains a standalone, manually triggered GitHub Actions workflow:
`.github/workflows/saraf-original-readonly-release.yml`.
It checks out this migration branch and builds the ORIGINAL React Mini App in
`build:telegram-original` mode. The safe release packager
`scripts/prepare_saraf_original_release.mjs` selects ONLY market handlers and
read-only endpoints. It deploys **no Telegram SQLite schema**, account writes,
KYC handling, order creation, remittance submission, or admin settlement.

To use this without cloning:
1. @BotFather → select `@sarafiaf_bot` → **Serverless** → enable →
   **CLI Access** → copy its `app<id>:<secret>` access token.
   This is **not** the Bot API token stored in Supabase.
2. In GitHub repository Settings → Secrets and variables → Actions,
   create secret **`SARAF_ORIGINAL_TGCLOUD_TOKEN`** with that CLI token.
3. In GitHub Actions, run **Saraf original bot – manually approved read-only Telegram Serverless release**.
   First choose `preview`, type `sarafiaf_bot` and the **public** app ID
   (`app<id>` token prefix), and leave confirmation blank.
4. Inspect the cloud changes. **Only with a deliberate second manual action** choose
   `publish` and enter the exact approval phrase
   `PUBLISH_READ_ONLY_SARAFIAF_BOT`. This calls `tgcloud push` and
   `tgcloud webhook sync` **without** `--force` or `--drop-pending`.
5. Once published, point the **original** bot's Mini App menu button to the
   exact `https://app<id>.tgcloud.ai/` URL displayed by the workflow.
   Test account ownership on a fresh, signed original-bot Mini App session
   before announcing the system as ready.

**Do not paste either token into chat or the GitHub repository.**
GitHub's workflow does not run on push/PR and will not publish automatically.
The account and existing financial history remain in Supabase and payment writes
are still disabled.

## Launch prerequisites (in this order)

1. Protect and verify the **existing** Supabase SQL data and storage; take a point-in-time
   backup or verify a valid recovery point before any financial schema operations.
2. Configure the **original bot's** Telegram token as a Supabase Edge Function secret named
   `SARAF_TELEGRAM_BOT_TOKEN`; do **not** provide this token in chat, GitHub source,
   browser `VITE_*` variables, screenshots, public logs or actions artifact.
   The Supabase service-role key must also remain server-side only.
3. Deploy `saraf-telegram-bridge` with `verify_jwt=false` **only because**
   the handler enforces Telegram HMAC authorization itself. No financial write actions,
   private document uploads or admin settlement endpoints are available there.
4. On a trusted authenticated Mini App session of the **original** bot, test
   profile/history ownership and rejection of invalid/expired signed requests.
   Check reviews, ratings and user isolation; do not test with money.
5. Only after the Edge Function is reachable, configure the **build-only public flag**
   `VITE_SARAF_CANONICAL_BRIDGE_ENABLED=true` and rebuild the original React Mini App.
   This flag is not an authorization mechanism.
6. Confirm the original bot identity and miniapp menu URL; deploy read-only first,
   leave finance and KYC uploads gated while financial operations are audited.

**Current blocker:** The connected Supabase Edge Function deployment operation was blocked
by the available tool safety checks. No Edge Function deployment or Supabase secret changes occurred.
The user need not clone the repository, but a privileged deployment action remains necessary.

## Notes from security audit

- Most business tables are protected by RLS; the existing unrestricted policies
  on `users` and `usdt_orders` currently lack `anon` / `authenticated` table SELECT grants
  according to SQL permissions checks. Do **not** add general SELECT grants to these tables.
- Supabase advisor warns that `public.handle_new_user_notification()` is a SECURITY DEFINER
  trigger function with inherited PUBLIC EXECUTE. Consider revoking public EXECUTE
  after checking its trigger behavior; this change was **not applied**.
- Treat all KYC and bank information as sensitive and do not surface full rows to client UIs.
- The original `saraf-api` and `notify-telegram` Edge Functions remain untouched.
- Financial trading, payment settlement, remittance payout, blockchain confirmations,
  Playwright post images and Meta webhooks are **NOT** active on native Serverless.

## Supabase policies for this architecture

**Recommended:** Telegram HMAC-validated Edge Function + server-side Supabase client.
Do not use a publishable/anon key to SELECT user profiles/orders: the user is authenticated
by Telegram, not necessarily by a Supabase Auth JWT, so `auth.uid()` is not reliable here.
Do not create broad `USING (true)` policies or put secret keys into the Mini App.

This file is a deployment record and does not itself change production settings.
