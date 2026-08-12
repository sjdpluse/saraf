BEGIN;

-- ---------------------------------------------------------------------------
-- Saraf 2.0 — Ensure sensitive storage buckets are private (spec §11).
--
-- Supabase Storage buckets are just rows in storage.buckets; `public = true`
-- is what makes storage.get_public_url() serve files with no auth check at
-- all. This migration idempotently creates (or flips) the three buckets this
-- app writes to as private. If a bucket already exists (as usdt-kyc-docs and
-- usdt-cards already did, per the original codebase), this only updates its
-- `public` flag — it does not touch existing objects/policies otherwise.
--
-- The app itself never reads these via the public URL anymore (see
-- services/supabase_service.py: upload_private_file + get_signed_url); this
-- migration is the DB-side guarantee that a stale/public bucket flag can't
-- silently defeat that.
-- ---------------------------------------------------------------------------

INSERT INTO storage.buckets (id, name, public)
VALUES
  ('usdt-receipts', 'usdt-receipts', false),
  ('usdt-kyc-docs', 'usdt-kyc-docs', false),
  ('usdt-cards', 'usdt-cards', false)
ON CONFLICT (id) DO UPDATE SET public = false;

-- ---------------------------------------------------------------------------
-- Storage RLS: the application talks to Storage exclusively with the
-- service_role key (server-side only, never exposed to the client/Mini App),
-- which bypasses RLS by design — so the app does not strictly depend on any
-- policy existing here. These policies are a defense-in-depth backstop only,
-- in case a future change ever exposes the anon/authenticated key to a
-- client path: with no policy at all, RLS on storage.objects defaults to
-- deny-all for non-service-role callers, which is already the safe default.
-- Nothing further to add here; documented so this isn't mistaken for an
-- oversight during review.
-- ---------------------------------------------------------------------------

COMMIT;
