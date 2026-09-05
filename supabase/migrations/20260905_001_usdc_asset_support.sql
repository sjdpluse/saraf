BEGIN;

-- Backward-compatible USDC support. Legacy table/column names are intentionally
-- retained because production code and historical records already depend on them.

ALTER TABLE public.usdt_orders
  ADD COLUMN IF NOT EXISTS asset text;

UPDATE public.usdt_orders
SET asset = 'USDT'
WHERE asset IS NULL OR btrim(asset) = '';

ALTER TABLE public.usdt_orders
  ALTER COLUMN asset SET DEFAULT 'USDT',
  ALTER COLUMN asset SET NOT NULL;

ALTER TABLE public.usdt_orders
  DROP CONSTRAINT IF EXISTS usdt_orders_asset_check;

ALTER TABLE public.usdt_orders
  ADD CONSTRAINT usdt_orders_asset_check
  CHECK (asset IN ('USDT', 'USDC'));

CREATE INDEX IF NOT EXISTS usdt_orders_asset_created_at_idx
  ON public.usdt_orders (asset, created_at DESC);

ALTER TABLE public.usdt_quotes
  ADD COLUMN IF NOT EXISTS asset text;

UPDATE public.usdt_quotes
SET asset = 'USDT'
WHERE asset IS NULL OR btrim(asset) = '';

ALTER TABLE public.usdt_quotes
  ALTER COLUMN asset SET DEFAULT 'USDT',
  ALTER COLUMN asset SET NOT NULL;

ALTER TABLE public.usdt_quotes
  DROP CONSTRAINT IF EXISTS usdt_quotes_asset_check;

ALTER TABLE public.usdt_quotes
  ADD CONSTRAINT usdt_quotes_asset_check
  CHECK (asset IN ('USDT', 'USDC'));

CREATE INDEX IF NOT EXISTS usdt_quotes_chat_asset_created_at_idx
  ON public.usdt_quotes (chat_id, asset, created_at DESC);

COMMIT;
