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
