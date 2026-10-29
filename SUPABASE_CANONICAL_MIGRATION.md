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
