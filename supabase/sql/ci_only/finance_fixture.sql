-- GitHub CI ONLY, ephemeral PostgreSQL fixture for the real Saraf schemas.
-- NEVER execute this file against the actual Supabase project.
CREATE ROLE service_role NOLOGIN BYPASSRLS;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE TABLE public.user_profiles(
  chat_id bigint PRIMARY KEY,first_name text,last_name text,phone text,
  kyc_status text NOT NULL DEFAULT 'pending',
  id_document_path text,selfie_path text
);
CREATE TABLE public.usdt_quotes(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  chat_id bigint NOT NULL,order_type text NOT NULL,asset text NOT NULL,
  usdt_amount numeric NOT NULL,usd_rate numeric NOT NULL,
  fee_percent numeric NOT NULL DEFAULT 0,total_afn numeric NOT NULL,
  total_usd numeric NOT NULL,status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),expires_at timestamptz NOT NULL,
  consumed_at timestamptz,pricing_model text,market_margin_usd numeric,
  supplier_profit_usd numeric,saraf_profit_usd numeric,customer_discount_usd numeric,
  supplier_payout_usd numeric,market_price_usd numeric,
  supplier_profit_afn numeric,saraf_profit_afn numeric,customer_discount_afn numeric,
  supplier_payout_afn numeric,market_price_afn numeric
);
CREATE TABLE public.usdt_orders(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,chat_id bigint NOT NULL,
  username text,full_name text,phone text,order_type text NOT NULL,
  asset text NOT NULL,usdt_amount numeric NOT NULL,usd_rate numeric NOT NULL,
  fee_percent numeric,total_afn numeric NOT NULL,total_usd numeric NOT NULL,
  payment_method text,receive_method text,network text,wallet_address text,
  exchange_name text,status text NOT NULL DEFAULT 'pending',
  source text,risk_level text,idempotency_key text,quote_id bigint,
  created_at timestamptz NOT NULL DEFAULT now(),pricing_model text,
  market_margin_usd numeric,supplier_profit_usd numeric,saraf_profit_usd numeric,
  customer_discount_usd numeric,supplier_payout_usd numeric,market_price_usd numeric,
  supplier_profit_afn numeric,saraf_profit_afn numeric,customer_discount_afn numeric,
  supplier_payout_afn numeric,market_price_afn numeric
);
CREATE UNIQUE INDEX usdt_orders_chat_id_idempotency_key_uidx
 ON public.usdt_orders(chat_id,idempotency_key) WHERE idempotency_key IS NOT NULL;
GRANT USAGE ON SCHEMA public TO service_role,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.usdt_quotes,public.usdt_orders TO service_role;
GRANT SELECT ON public.user_profiles TO service_role;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
ALTER TABLE public.usdt_quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usdt_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Remittance fixture mirrors the CURRENT original Supabase table fields.
CREATE TABLE public.remittance_orders (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  chat_id bigint NOT NULL,
  idempotency_key text NOT NULL,
  sender_country text NOT NULL,sender_name text,
  beneficiary_full_name text NOT NULL,beneficiary_phone text NOT NULL,
  beneficiary_province text NOT NULL,beneficiary_city text NOT NULL,
  beneficiary_address text,asset text NOT NULL,network text NOT NULL,
  crypto_amount numeric NOT NULL,usd_rate numeric NOT NULL,
  gross_afn numeric NOT NULL,fee_percent numeric NOT NULL DEFAULT 0,
  fee_afn numeric NOT NULL DEFAULT 0,payout_afn numeric NOT NULL,
  deposit_wallet text NOT NULL,tx_hash text,status text NOT NULL
    DEFAULT 'awaiting_transfer',
  verification_status text NOT NULL DEFAULT 'not_submitted',
  chain_confirmations integer NOT NULL DEFAULT 0,
  chain_verified_at timestamptz,chain_verified_asset text,
  chain_verified_network text,chain_verified_amount numeric,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(chat_id,idempotency_key)
);
ALTER TABLE public.remittance_orders ENABLE ROW LEVEL SECURITY;
GRANT SELECT,INSERT,UPDATE ON public.remittance_orders TO service_role;
GRANT USAGE,SELECT ON SEQUENCE public.remittance_orders_id_seq TO service_role;
