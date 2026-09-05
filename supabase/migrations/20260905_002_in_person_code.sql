BEGIN;

ALTER TABLE public.usdt_orders
  ADD COLUMN IF NOT EXISTS in_person_code text;

ALTER TABLE public.usdt_orders
  DROP CONSTRAINT IF EXISTS usdt_orders_in_person_code_check;

ALTER TABLE public.usdt_orders
  ADD CONSTRAINT usdt_orders_in_person_code_check
  CHECK (in_person_code IS NULL OR in_person_code ~ '^[0-9]{4}$');

CREATE INDEX IF NOT EXISTS usdt_orders_in_person_code_idx
  ON public.usdt_orders (in_person_code)
  WHERE in_person_code IS NOT NULL;

COMMIT;
