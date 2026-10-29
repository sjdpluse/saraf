## Additional hardened controls — 29 October 2026

The financial release is still **OFF**, but additional independent financial
controls have now been added to the real Saraf migration branch:

- Two-person payout readiness: `saraf_payout_dual_control_staged.sql`
  enrolls distinct verified Telegram operators in a database allowlist.
  A verified blockchain transfer alone is insufficient. Each operator must
  separately sign off against the **same** immutable on-chain proof snapshot.
  When token contract, logs or block hash changes, earlier approvals stop
  qualifying. A recipient cannot approve their own payout.
- The `saraf_prepare_payout_after_dual_approval` function moves an item
  into a manual payout **queue**, never transfers customer money.
  Any new transition to `completed` remains forbidden until a
  separately verifiable bank/cash settlement system is integrated.
- `saraf-finance-rate-limit-staged.sql` implements 5-minute quota
  windows shared between Supabase Edge instances for quotes, orders,
  remittance TX claims and authorized operator review actions.
- `saraf-operator-review` Edge Function independently requires a signed
  original-bot Mini App Telegram identity, two operator IDs enrolled in
  secure Supabase secrets, enabled DB operator ACL, and a separate
  **off-by-default** `SARAF_OPERATOR_REVIEW_ENABLED` secret switch.
- Remittance quote issuance is restricted to EVM networks, because real
  Tron/Solana proof verification is **not** implemented and must never
  allow a customer to send funds they cannot prove.
- `SARAF_FINANCE_ACTIVATION_RUNBOOK.md` records the full live-readiness
  checklist, verified suppliers, wallet keys, operator enrollment and
  payout integration blockers.
- Existing live Supabase still contains 50 historical orders and
  one unverified `payout_ready` remittance; no data was changed.

**Not deployed to production:** all new SQL, new Edge Functions and operator
approvals. Only the original read-only Telegram/Supabase bridge remains live.
A passing test on ephemeral PostgreSQL is NOT authorization to accept real funds.

# Saraf financial backend and transaction security — 29 October 2026

**Scope:** `@sarafiaf_bot`, existing canonical Supabase project `cvernmhpnsgdtegvblyc`.
**Status: substantial financial backend implemented and tested in isolated CI,
NOT deployed or enabled on real money.**

## Implemented directly in GitHub (no local clone required)
1. `supabase/sql/saraf_atomic_finance_staged.sql` — canonical verified-rate table,
   server-owned receiving wallets, quote issuance with NUMERIC pricing, row-lock
   and one-time quote consumption, idempotency fingerprints, duplicate quote
   unique index, KYC/ownership checks, daily cap, audit records, service-role-only
   RPC functions.
2. `supabase/sql/saraf_atomic_remittance_staged.sql` — remittance quotes,
   transaction-safe request submission and replay handling, cross-user isolation,
   unique (network,txHash) enforcement, claim-only TX input and database trigger
   that forbids *new* payout_ready/completed transitions without independently
   verified, amount-matched blockchain evidence and >=12 confirmations.
3. `supabase/functions/saraf-finance/index.ts` — HMAC-authenticated,
   original-bot-only server API for quote/order/remittance requests with
   server-secret `SARAF_FINANCIAL_WRITES_ENABLED`, default OFF. No customer can
   decide their own rates, amounts, user IDs, or payout confirmations.
4. `supabase/functions/saraf-chain-verifier/evm.mjs` — canonical receipt,
   chain ID, contract, destination wallet, token transfer amount and confirmation
   verification. `index.ts` is cron-secret-only, default OFF. **EVM token
   verification only**; Tron/Solana/Bitcoin providers are not implemented.
5. `webapp/src/lib/financeBridge.js` and changed `api.js` — financial RPC
   routes point at the canonical Supabase store, not independent Telegram SQLite.
   UI flag is OFF by default; there is no Railway fallback.
6. GitHub Actions `Saraf financial backend invariants` tests SQL against an
   **ephemeral PostgreSQL 16**, exercises quote consumption, user isolation,
   retries, concurrency race, remittance payouts and signature/chain proof
   checks; Deno type-checks the Edge functions. No production database writes.

## Critical LIVE read-only audit observation

The real Supabase project contains **remittance ID 9** currently
`payout_ready` while `verification_status='pending'`,
`chain_confirmations=0`, and no `chain_verified_at` timestamp.
**Do not pay or complete this remittance based on this status alone.**
It requires reconciliation with actual bank/cash handover and independent
blockchain evidence. No historic order or status was changed.

## Explicit launch blockers (do not bypass)

- Staged SQL migrations were **NOT applied to live Supabase** (they contain
  new order/payout behavior). Review and backup the 50 orders, 10 remittances
  and storage before applying and doing integration tests in an isolated
  Supabase project.
- The finance and chain verifier functions were **NOT deployed**.
- Supplier-verified, expiring FX rates, operator Telegram IDs, verified
  asset/network deposit wallets, and RPC + token contracts have not been
  configured; none were invented.
- Actual online bank payment verification, settlement execution, multi-factor
  operator approvals, Tron/Solana verification, and full operational monitoring
  are not implemented and remain **disabled**.
- If a read-only bot version is published, keep it read-only; do not switch
  on finance/KYC feature flags or remove the protections without sign-off.

## Current live, proven services
The separately deployed `saraf-telegram-bridge` is active and its unsigned
and forged request rejection tests passed. Existing financial records in
Supabase remain untouched.

**Safe outcome:** protect prior customers and financial balances while preparing
a deployable, testable backend, rather than falsely declaring money movements live.
