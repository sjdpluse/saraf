BEGIN;

-- Persist the economic breakdown of each BUY quote/order so admin settlement
-- remains reproducible even if FX rates or pricing rules change later.
ALTER TABLE public.usdt_quotes
  ADD COLUMN IF NOT EXISTS pricing_model text,
  ADD COLUMN IF NOT EXISTS market_margin_usd numeric,
  ADD COLUMN IF NOT EXISTS supplier_profit_usd numeric,
  ADD COLUMN IF NOT EXISTS saraf_profit_usd numeric,
  ADD COLUMN IF NOT EXISTS customer_discount_usd numeric,
  ADD COLUMN IF NOT EXISTS supplier_payout_usd numeric,
  ADD COLUMN IF NOT EXISTS market_price_usd numeric,
  ADD COLUMN IF NOT EXISTS supplier_profit_afn numeric,
  ADD COLUMN IF NOT EXISTS saraf_profit_afn numeric,
  ADD COLUMN IF NOT EXISTS customer_discount_afn numeric,
  ADD COLUMN IF NOT EXISTS supplier_payout_afn numeric,
  ADD COLUMN IF NOT EXISTS market_price_afn numeric;

ALTER TABLE public.usdt_orders
  ADD COLUMN IF NOT EXISTS pricing_model text,
  ADD COLUMN IF NOT EXISTS market_margin_usd numeric,
  ADD COLUMN IF NOT EXISTS supplier_profit_usd numeric,
  ADD COLUMN IF NOT EXISTS saraf_profit_usd numeric,
  ADD COLUMN IF NOT EXISTS customer_discount_usd numeric,
  ADD COLUMN IF NOT EXISTS supplier_payout_usd numeric,
  ADD COLUMN IF NOT EXISTS market_price_usd numeric,
  ADD COLUMN IF NOT EXISTS supplier_profit_afn numeric,
  ADD COLUMN IF NOT EXISTS saraf_profit_afn numeric,
  ADD COLUMN IF NOT EXISTS customer_discount_afn numeric,
  ADD COLUMN IF NOT EXISTS supplier_payout_afn numeric,
  ADD COLUMN IF NOT EXISTS market_price_afn numeric;

COMMIT;
