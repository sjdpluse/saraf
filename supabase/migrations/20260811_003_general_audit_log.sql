BEGIN;

-- ---------------------------------------------------------------------------
-- Saraf 2.0 — General audit log (spec §6)
-- Covers events not already captured by usdt_order_status_history: quote
-- lifecycle, KYC decisions, payment-info changes, receipt uploads, admin
-- actions. Append-only by convention (no UPDATE/DELETE path in application
-- code); nothing here is a hard DB-level immutability guarantee yet, since
-- Saraf runs on the Supabase service_role key for all server-side writes.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.audit_log (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor bigint,                 -- Telegram chat_id of the user/admin who performed the action; NULL = system
  action text NOT NULL,         -- e.g. 'quote_created', 'quote_consumed', 'kyc_verified', 'order_confirmed'
  entity text NOT NULL,         -- e.g. 'usdt_order', 'usdt_quote', 'user_profile', 'kyc_document'
  entity_id text,               -- stringified id of the affected row (bigint ids, string chat_ids, etc.)
  before jsonb,                 -- state before the change (masked for sensitive fields by the app layer)
  after jsonb,                  -- state after the change
  reason text,
  request_id text,              -- optional correlation id (not yet wired end-to-end; reserved for future use)
  created_at timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_log_entity_idx ON public.audit_log (entity, entity_id);
CREATE INDEX IF NOT EXISTS audit_log_actor_idx ON public.audit_log (actor);
CREATE INDEX IF NOT EXISTS audit_log_created_at_idx ON public.audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS audit_log_action_idx ON public.audit_log (action);

-- ---------------------------------------------------------------------------
-- Attribute order-status-history rows to an actor/reason after the fact.
-- The existing trigger (record_usdt_order_status_history) always inserts
-- changed_by = NULL because a single PostgREST call is one transaction and
-- application code cannot set a session variable that would survive to a
-- later request. Instead, application code performs a best-effort follow-up
-- UPDATE on the just-inserted (changed_by IS NULL) row for that order+status.
-- This index makes that follow-up UPDATE cheap and precise.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS usdt_order_status_history_unattributed_idx
  ON public.usdt_order_status_history (order_id, to_status)
  WHERE changed_by IS NULL;

COMMIT;
