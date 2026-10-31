# Original Saraf — remaining external Meta account cutover (no Railway)

**Verified on 2026-10-31:** Original Telegram `@sarafiaf_bot` webhook is
`https://cloud.telegram.org/app8533795882/webhook`; original React and
admin-only menu deployed (release run **41231680604**, **89/89** regression
checks). Original financial production HMAC preflight succeeded
(**41231820027**). Supabase original market snapshots have resumed.

## Why Meta live posting cannot be marked complete yet

The **read-only** GitHub Actions environment audit **41230998564**
confirmed all eight of these **GITHUB SECRETS ARE MISSING** in the
`saraf-original-production` job environment. The assistant cannot obtain
private Meta/Railway credentials or add GitHub Secrets with its available
connector. Never paste token values into GitHub source, ChatGPT or this guide.

| Source original Railway or Meta configuration | Required GitHub Action Secret |
| --- | --- |
| `SUPABASE_KEY` original service-role | `SARAF_ORIGINAL_SUPABASE_KEY` |
| `FACEBOOK_PAGE_ID` | `SARAF_ORIGINAL_FACEBOOK_PAGE_ID` |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | `SARAF_ORIGINAL_FACEBOOK_PAGE_ACCESS_TOKEN` |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | `SARAF_ORIGINAL_INSTAGRAM_BUSINESS_ACCOUNT_ID` |
| `INSTAGRAM_USER_ACCESS_TOKEN` (IG comments/DMs) | `SARAF_ORIGINAL_INSTAGRAM_USER_ACCESS_TOKEN` |
| `FACEBOOK_APP_SECRET` | `SARAF_ORIGINAL_FACEBOOK_APP_SECRET` |
| `INSTAGRAM_APP_SECRET` | `SARAF_ORIGINAL_INSTAGRAM_APP_SECRET` |
| `OPENROUTER_API_KEY` (original AI reply) | `SARAF_ORIGINAL_OPENROUTER_API_KEY` |

Secret destination: GitHub repository
**Settings → Secrets and variables → Actions**, in repository secrets or the
`saraf-original-production` protected environment's secrets. These are
**GitHub** secrets, *not* Supabase secrets.

## Existing original systems already implemented

- GitHub schedule: `.github/workflows/saraf-original-social-railway-free.yml`
  runs the original Python automatic USD-change-triggered Facebook and
  Instagram posting logic (force=True only after the existing threshold).
  The v19.0 **expired** Meta Graph transport was updated to v26.0 without
  changing original captions, images, prices, or USD trigger semantics.
- Original manual admin `/post` or native Mini App → Menu → Management →
  Facebook/Instagram uses a **signed Telegram admin-only** request, queued
  with an idempotency key in `saraf_original_manual_social_requests`.
  The worker runs `handlers/admin.py`'s exact two Python posting services.
  On an uncertain Graph result no automatic retry or duplicate posting.
- Original Instagram/Facebook comments, DM, keyword and AI handlers remain
  in `services/instagram_automation_v2.py` and
  `services/facebook_comment_automation.py`, consumed from
  `saraf_meta_delivery_queue` by
  `.github/workflows/saraf-original-meta-worker.yml`.
- Signed receiver:
  `https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-meta-webhook?platform=facebook`
  and
  `https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-meta-webhook?platform=instagram`.
  Add these as the appropriate app's webhook callbacks inside Meta
  for Developers and use the same platform-specific verification tokens.

## Activation order — never bypass these gates

1. Copy all **eight** original GitHub Secrets above from original private
   Railway/Meta configuration, preserving exact values.
2. In **Supabase → Edge Functions → Secrets**, ensure
   `FACEBOOK_APP_SECRET`, `FACEBOOK_WEBHOOK_VERIFY_TOKEN`,
   `INSTAGRAM_APP_SECRET`,
   `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` have their **original correct**
   values. No copies of them should be committed or sent in chat.
3. Run `saraf-original-social-railway-free.yml` via **Run workflow →
   task=audit**. Only names of missing Secrets/disabled flags are printed;
   this performs no Meta request, no payment changes, and no queue claim.
4. Once Meta app webhook verification succeeds and the original Meta
   account permissions/Graph tokens work, set Supabase secrets:
   `SARAF_ORIGINAL_META_WEBHOOKS_ENABLED=true` and
   `SARAF_ORIGINAL_SOCIAL_POST_ENABLED=true`.
5. Explicitly authorize **GitHub** booleans:
   `SARAF_ORIGINAL_CUTOVER_APPROVED=true`,
   `SARAF_ORIGINAL_SOCIAL_PUBLISH_ENABLED=true`,
   `SARAF_ORIGINAL_SOCIAL_AUTOMATION_ENABLED=true`, and
   `SARAF_ORIGINAL_META_WORKER_ENABLED=true`.
   Note: `SARAF_ORIGINAL_CUTOVER_APPROVED` is a SHARED gate for
   broadcast and other workers; review those separately before enabling.
6. For one confirmed original admin, send `/post` to
   `@sarafiaf_bot`; enter the protected Mini App and request one
   **real** test post. Confirm Facebook AND Instagram publication,
   compare image, caption and financial rates with the historical version,
   and inspect `social.post.status`. Then verify one incoming signed
   Facebook comment and Instagram comment/DM event reaches the correct
   original automated reply exactly once.
7. Only after the original customer buy/sell/KYC/remittance and admin
   controls are verified with fresh real signed Mini App sessions,
   originals Meta callbacks have moved, original histories are fresh, and
   all required delivery queues are processing, decommission Railway.
   No scripted workflow automatically deletes Railway.

**Never use `tgcloud push --force`, reset the original Supabase data, or
enable external posting before those private permissions are validated.**
