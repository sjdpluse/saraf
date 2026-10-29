# Saraf financial security — controlled rollout checklist (2026-10-29)

**Deployment target:** Original @sarafiaf_bot, Supabase
`cvernmhpnsgdtegvblyc`, Telegram-hosted React Mini App.
**IMPORTANT: NOT PRODUCTION-READY OR LIVE FOR FINANCIAL TRANSACTIONS.**
The operational Finance, Chain Verifier and Operator Review functions are not
deployed. No scripts on this branch automatically alter the live financial DB.

## Existing production data and non-destructive preflight

Read-only Supabase audit, 2026-10-29:

- 50 legacy USDT/USDC orders remain in the original DB.
- One legacy remittance (ID **9**) remains **payout_ready** without independent
  chain verification. Do not pay this claim until it is reconciled manually.
- New rate registry, verified wallets, operator ACL and dual-control approval
  tables **do not yet exist on the production database**. This is intentional.
- The existing `saraf-telegram-bridge` for signed user history is separate and
  is already deployed with tests for forged and unsigned requests.

## Code completed on the migration branch

| Component | File | Protection |
|---|---|---|
| Financial DB atomic engine | `supabase/sql/saraf_atomic_finance_staged.sql` | Fixed-point NUMERIC rates, expiring quotes, one-time consume, unique idempotency, KYC/daily cap and audit |
| Remittance engine | `supabase/sql/saraf_atomic_remittance_staged.sql` | Quotes, verified deposit wallets, owner-scoped request/TxID, double-spend block and minimum chain proof |
| Dual-control payout queue | `supabase/sql/saraf_payout_dual_control_staged.sql` | Two different enabled operators, independent proofs, self-review denied, chain proof frozen, **completed status blocked** |
| Per-identity rate limits | `supabase/sql/saraf_finance_rate_limit_staged.sql` | Atomic five-minute per-action quotas shared across Edge instances |
| Customer finance API | `supabase/functions/saraf-finance/index.ts` | Signed original Telegram user; money writes OFF unless secret switch set |
| Chain receipt verifier | `supabase/functions/saraf-chain-verifier/` | Verified EVM chain ID, token contract, recipient address, exact value and canonical confirmations; cron secret and feature switch OFF |
| Operator review API | `supabase/functions/saraf-operator-review/index.ts` | Signed original Telegram identity, >=2 secret allowlisted operators, DB operator ACL and additional OFF switch |
| React financial adapter | `webapp/src/lib/financeBridge.js` | Browser feature switch OFF; no client-side service-role secrets |
| CI | `.github/workflows/saraf-finance-safety.yml` | PostgreSQL isolated tests of quote races, owner isolation, KYC, duplicate remittance claims, payout locks, 2-person signoff, rate limit, EVM receipts and Deno checks |

## Conservative activation sequence (no clone required)

1. **Document and back up** historical Supabase tables and all private KYC,
   receipts and card storage. Audit remittance #9 and reconcile it with
   blockchain evidence and the actual banking/cash ledger. Do not mark it
   completed to quiet a security alert.
2. Test **all four** staged SQL scripts in an **isolated** Supabase project
   populated with synthetic data, in this order:
   `saraf_atomic_finance_staged.sql` →
   `saraf_atomic_remittance_staged.sql` →
   `saraf_payout_dual_control_staged.sql` →
   `saraf_finance_rate_limit_staged.sql`.
   GitHub CI already uses isolated PostgreSQL 16 but this does not substitute
   for live Supabase integration and external provider testing.
3. Verify treasury-owned deposit addresses **per asset + chain**, actual
   supported token contracts and decimals, trusted JSON-RPC sources,
   independent confirmations and legitimate supplier exchange rates.
   Never reuse test wallet addresses or invent prices. Non-EVM networks
   remain disabled for deposits until proper chain verifiers exist.
4. Enroll **two separate** operator Telegram numeric IDs in
   `saraf_finance_operators`, disabled by default, and **independently**
   verify each operator's right to manage funds. Never onboard the
   customer as their own reviewer. Place these same operator IDs as a
   **Supabase secret** `SARAF_OPERATOR_IDS`. Do not commit bot/DB/API
   credentials, RPC vendor keys or private wallet keys to GitHub.
5. Deploy the three Edge Functions with **all activation flags FALSE**:
   `SARAF_FINANCIAL_WRITES_ENABLED`,
   `SARAF_BLOCKCHAIN_WATCH_ENABLED`,
   `SARAF_OPERATOR_REVIEW_ENABLED`.
   They require server-side authentication and the original bot's token.
   Deploying is NOT permission to enable or start processing customer funds.
6. On isolated testnet/sandbox accounts, test a genuinely
   HMAC-authenticated Telegram original-bot session; expired/forged auth,
   duplicate submissions, quote expiry, race conditions, wrong chain,
   wrong wallet, malicious decimals/amounts, operator revocation, proof
   mutation after approval, rollback and missing bank payment confirmation.
7. **Do not enable live financial actions** until actual bank payment provider
   verification, audit evidence, treasury wallet operational procedures,
   compliant KYC handling, incident response, and independently confirmed
   settlement have been integrated and reviewed.
8. A verified blockchain deposit and two authorized operators can only put
   a remittance into `payout_ready` for **manual payout review**. This is
   **NOT** proof that cash was given or the bank settled. The SQL gate
   deliberately forbids new transitions to `completed` until a separate
   settlement proof system exists.

### Manual controls are not cosmetic
- Access to original Telegram bot is NOT the same as access to the customer's
  money; each operator must be approved in BOTH the server-side configuration
  and the database ACL.
- Never use the browser's user ID, wallet address, price, proof-of-payment
  screenshots or claimed TX hash as sufficient authorization for a payout.
- A TX hash is merely a user claim until the independent on-chain verifier has
  checked the canonical block, token transfer, recipient and amount.
- Without real verified rates and verified wallets, quote/order issuance fails
  closed.
- Previous customer records are preserved in their original Supabase tables.
  There is no double ledger in Telegram SQLite.

## Release/verification evidence

GitHub PR #41 remains **Draft**. Its CI is allowed to use only synthetic
Postgres fixtures; no production write, bank transfer or actual customer
transaction occurs in those test suites.

**Release blockers**: actual bank/cash disbursement provider with
independent settlement receipts, operational KYC workflow, treasury
approval/enrollment, verified production FX sources and wallets, safe
backup/restore drill and real end-to-end financial integration tests.
