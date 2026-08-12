BEGIN;

-- ---------------------------------------------------------------------------
-- Saraf 2.0 — USDT order safety foundation
-- Backward compatible with the current pending/confirmed/completed/cancelled flow.
-- ---------------------------------------------------------------------------

-- 1) Idempotency: allows the API/client to safely retry a submission without
-- creating a second order. NULL remains allowed during the rollout.
ALTER TABLE public.usdt_orders
  ADD COLUMN IF NOT EXISTS idempotency_key text;

CREATE UNIQUE INDEX IF NOT EXISTS usdt_orders_chat_id_idempotency_key_uidx
  ON public.usdt_orders (chat_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- 2) Quote entity: a server-issued quote can be bound to an order later.
CREATE TABLE IF NOT EXISTS public.usdt_quotes (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  chat_id bigint NOT NULL,
  order_type text NOT NULL CHECK (order_type IN ('buy', 'sell')),
  usdt_amount numeric NOT NULL CHECK (usdt_amount > 0),
  usd_rate numeric NOT NULL CHECK (usd_rate > 0),
  fee_percent numeric NOT NULL DEFAULT 0 CHECK (fee_percent >= 0 AND fee_percent <= 100),
  total_afn numeric NOT NULL CHECK (total_afn >= 0),
  total_usd numeric NOT NULL CHECK (total_usd >= 0),
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'consumed', 'expired', 'cancelled')),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  expires_at timestamp with time zone NOT NULL,
  consumed_at timestamp with time zone
);

CREATE INDEX IF NOT EXISTS usdt_quotes_chat_id_created_at_idx
  ON public.usdt_quotes (chat_id, created_at DESC);

CREATE INDEX IF NOT EXISTS usdt_quotes_active_expiry_idx
  ON public.usdt_quotes (status, expires_at);

ALTER TABLE public.usdt_orders
  ADD COLUMN IF NOT EXISTS quote_id bigint;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'usdt_orders_quote_id_fkey'
  ) THEN
    ALTER TABLE public.usdt_orders
      ADD CONSTRAINT usdt_orders_quote_id_fkey
      FOREIGN KEY (quote_id) REFERENCES public.usdt_quotes(id);
  END IF;
END $$;

-- 3) Expand the order vocabulary without changing the meaning of existing
-- states. The application can adopt the new states incrementally.
ALTER TABLE public.usdt_orders
  DROP CONSTRAINT IF EXISTS usdt_orders_status_check;

ALTER TABLE public.usdt_orders
  ADD CONSTRAINT usdt_orders_status_check
  CHECK (
    status IN (
      'pending',
      'payment_pending',
      'payment_submitted',
      'under_review',
      'confirmed',
      'approved',
      'processing',
      'completed',
      'cancelled',
      'rejected',
      'expired',
      'failed'
    )
  );

-- 4) Immutable-ish status history. Rows are created by the database trigger
-- below, so application code cannot silently forget to record a transition.
CREATE TABLE IF NOT EXISTS public.usdt_order_status_history (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id bigint NOT NULL REFERENCES public.usdt_orders(id) ON DELETE CASCADE,
  from_status text,
  to_status text NOT NULL,
  changed_at timestamp with time zone NOT NULL DEFAULT now(),
  changed_by bigint,
  reason text
);

CREATE INDEX IF NOT EXISTS usdt_order_status_history_order_idx
  ON public.usdt_order_status_history (order_id, changed_at ASC);

-- 5) Server-side transition guard. This protects the order lifecycle even if
-- a future admin/API path accidentally tries an invalid status jump.
CREATE OR REPLACE FUNCTION public.validate_usdt_order_status_transition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'pending' THEN
      RAISE EXCEPTION 'New USDT orders must start in pending status';
    END IF;
    RETURN NEW;
  END IF;

  IF NEW.status = OLD.status THEN
    RETURN NEW;
  END IF;

  IF NOT (
    (OLD.status = 'pending' AND NEW.status IN ('payment_pending', 'payment_submitted', 'under_review', 'confirmed', 'cancelled', 'rejected', 'expired', 'failed'))
    OR (OLD.status = 'payment_pending' AND NEW.status IN ('payment_submitted', 'under_review', 'cancelled', 'expired', 'failed'))
    OR (OLD.status = 'payment_submitted' AND NEW.status IN ('under_review', 'confirmed', 'approved', 'cancelled', 'rejected', 'failed'))
    OR (OLD.status = 'under_review' AND NEW.status IN ('approved', 'confirmed', 'cancelled', 'rejected', 'failed'))
    OR (OLD.status = 'confirmed' AND NEW.status IN ('processing', 'completed', 'cancelled', 'failed'))
    OR (OLD.status = 'approved' AND NEW.status IN ('processing', 'cancelled', 'failed'))
    OR (OLD.status = 'processing' AND NEW.status IN ('completed', 'failed', 'cancelled'))
  ) THEN
    RAISE EXCEPTION 'Invalid USDT order status transition: % -> %', OLD.status, NEW.status;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_usdt_order_status ON public.usdt_orders;
CREATE TRIGGER trg_validate_usdt_order_status
BEFORE INSERT OR UPDATE OF status ON public.usdt_orders
FOR EACH ROW
EXECUTE FUNCTION public.validate_usdt_order_status_transition();

CREATE OR REPLACE FUNCTION public.record_usdt_order_status_history()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO public.usdt_order_status_history (order_id, from_status, to_status)
    VALUES (NEW.id, NULL, NEW.status);
  ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
    INSERT INTO public.usdt_order_status_history (order_id, from_status, to_status)
    VALUES (NEW.id, OLD.status, NEW.status);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_record_usdt_order_status_history ON public.usdt_orders;
CREATE TRIGGER trg_record_usdt_order_status_history
AFTER INSERT OR UPDATE OF status ON public.usdt_orders
FOR EACH ROW
EXECUTE FUNCTION public.record_usdt_order_status_history();

-- 6) Basic invariants for new writes. NOT VALID keeps the migration safe for
-- existing production rows; they can be validated after a data-quality review.
--
-- ADD CONSTRAINT has no IF NOT EXISTS in Postgres, so on a re-run (e.g. this
-- migration was already applied once) it errors with "constraint already
-- exists" and rolls back the whole transaction. DROP...IF EXISTS + ADD makes
-- this block safely re-runnable, matching the pattern already used above for
-- usdt_orders_status_check.
ALTER TABLE public.usdt_orders
  DROP CONSTRAINT IF EXISTS usdt_orders_positive_amounts_check;

ALTER TABLE public.usdt_orders
  ADD CONSTRAINT usdt_orders_positive_amounts_check
  CHECK (
    usdt_amount > 0
    AND usd_rate > 0
    AND total_afn >= 0
    AND total_usd >= 0
  ) NOT VALID;

ALTER TABLE public.usdt_orders
  DROP CONSTRAINT IF EXISTS usdt_orders_fee_percent_check;

ALTER TABLE public.usdt_orders
  ADD CONSTRAINT usdt_orders_fee_percent_check
  CHECK (fee_percent IS NULL OR (fee_percent >= 0 AND fee_percent <= 100)) NOT VALID;

COMMIT;
