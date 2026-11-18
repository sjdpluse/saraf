# Saraf production runtime contract

**The original @sarafiaf_bot runs on Telegram Serverless (BotFather app8533795882).**
The operational source is `migration/telegram-native-serverless-poc`, primarily
`serverless-poc/tgcloud/`. The original React Mini App is shipped as static
assets to the same Telegram Serverless app. Original signed financial and
history operations use the separately deployed Supabase Edge functions.

## Rules for future fixes

1. For runtime bot menus, callback logic, currency quotations and formatting,
   edit `serverless-poc/tgcloud/` first. The Railway-era `bot.py`,
   `handlers/*.py` and `services/*.py` on `main` are **not** the production
   Telegram bot. A fix solely to those Python files cannot resolve a live
   @sarafiaf_bot bug.
2. If related logic exists in signed Supabase Edge functions or snapshots,
   update those paths consistently, with tests. Do not use a second
   authoritative backend or an independent Telegram SQLite ledger.
3. Validate by running `node --test serverless-poc/tests/*.test.js`,
   syntax checks and the release manifest's exact module allowlist.
4. Production updates are **never** published on an ordinary push or PR.
   Use a reviewed, guarded **targeted** Telegram CLI push against
   `app8533795882` after fetching the live revision. Do **not** change
   webhooks, replace the full Mini App, reset Telegram remote modules, or
   invoke `--force` as part of a quote-format fix.
5. Use the original manual deploy workflows and production environment
   protections. A passing PR or CI build does not mean the live bot has been
   updated. Verify after publishing without executing real financial orders.

## Currency quote unit contract

The `sarafi.af` table uses `1K` for PKR, INR and **toman** (although the
row's code is `IRR`). The parser normalizes once into AFN per *one unit*.
The display shows PKR/INR per 1,000 and Iranian toman per 1,000,000.
International API `IRR` is **rial**: multiply by 10 to obtain the value of
one toman. Preserve sufficient decimals for one toman and never multiply a
previously scaled quote a second time.

Historical data recorded before this unit correction may still contain wrong
units. Keep finance tables immutable and do not rewrite historical prices
without a separate reviewed data-migration plan.
