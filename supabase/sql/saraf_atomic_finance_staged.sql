-- Saraf original Supabase financial hardening (STAGED, NOT YET APPLIED).
-- All existing orders, remittances, quotes and private storage are preserved.
-- Run in a maintenance window after passing CI database tests and reviewing
-- old clients; the application feature flag must remain OFF meanwhile.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

CREATE TABLE IF NOT EXISTS public.saraf_finance_rates (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  asset text NOT NULL CHECK (asset IN ('USDT','USDC')),
  afn_usd_buy numeric(14,4) NOT NULL CHECK (afn_usd_buy BETWEEN 20 AND 200),
  afn_usd_sell numeric(14,4) NOT NULL CHECK (afn_usd_sell BETWEEN 20 AND 200),
  source text NOT NULL CHECK (length(source) BETWEEN 3 AND 160),
  verified_by bigint NOT NULL CHECK (verified_by > 0),
  verified_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  CHECK (expires_at > verified_at AND expires_at <= verified_at + interval '2 minutes'),
  CHECK (afn_usd_sell >= afn_usd_buy)
);
CREATE INDEX IF NOT EXISTS saraf_finance_rates_active_idx
  ON public.saraf_finance_rates (asset, expires_at DESC);
ALTER TABLE public.saraf_finance_rates ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_finance_rates FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.saraf_finance_rates TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.saraf_finance_rates_id_seq TO service_role;

CREATE TABLE IF NOT EXISTS public.saraf_finance_wallets (
  asset text NOT NULL CHECK (asset IN ('USDT','USDC')),
  network text NOT NULL,
  address text NOT NULL CHECK (length(address) BETWEEN 30 AND 150),
  verified_by bigint NOT NULL CHECK (verified_by > 0),
  verified_at timestamptz NOT NULL DEFAULT now(),
  enabled boolean NOT NULL DEFAULT false,
  PRIMARY KEY (asset, network)
);
ALTER TABLE public.saraf_finance_wallets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_finance_wallets FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.saraf_finance_wallets TO service_role;

CREATE TABLE IF NOT EXISTS public.saraf_finance_attempts (
  chat_id bigint NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint jsonb NOT NULL,
  quote_id bigint NOT NULL REFERENCES public.usdt_quotes(id),
  order_id bigint UNIQUE REFERENCES public.usdt_orders(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (chat_id,idempotency_key),
  CHECK (length(idempotency_key) BETWEEN 16 AND 128)
);
ALTER TABLE public.saraf_finance_attempts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_finance_attempts FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.saraf_finance_attempts TO service_role;

CREATE TABLE IF NOT EXISTS public.saraf_finance_audit (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event text NOT NULL CHECK (length(event) BETWEEN 3 AND 80),
  actor_id bigint NOT NULL,
  quote_id bigint REFERENCES public.usdt_quotes(id),
  order_id bigint REFERENCES public.usdt_orders(id),
  info jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.saraf_finance_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_finance_audit FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON public.saraf_finance_audit TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.saraf_finance_audit_id_seq TO service_role;

-- Source-of-truth defense against two concurrent orders consuming one quote.
CREATE UNIQUE INDEX IF NOT EXISTS saraf_usdt_orders_one_quote_idx
  ON public.usdt_orders (quote_id) WHERE quote_id IS NOT NULL;

-- Row-level locking and immutable quote economics; all values are computed in
-- Postgres NUMERIC, not passed by an untrusted browser or rounded using floats.
CREATE OR REPLACE FUNCTION public.saraf_issue_quote_atomic(
  p_chat_id bigint, p_asset text, p_action text, p_amount numeric
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $$
DECLARE
  r public.saraf_finance_rates%ROWTYPE;
  q public.usdt_quotes%ROWTYPE;
  v_rate numeric;
  v_margin numeric;
  v_supplier numeric;
  v_saraf numeric;
  v_discount numeric;
  v_total_usd numeric;
  v_total_afn numeric;
BEGIN
  IF p_chat_id IS NULL OR p_chat_id <= 0 OR
     p_asset NOT IN ('USDT','USDC') OR
     p_action NOT IN ('buy','sell') OR
     p_amount IS NULL OR p_amount < 10 OR p_amount > 1000 OR
     p_amount <> round(p_amount,2) THEN
    RAISE EXCEPTION 'INVALID_QUOTE_INPUT' USING ERRCODE='P0001';
  END IF;

  SELECT * INTO r FROM public.saraf_finance_rates
    WHERE asset=p_asset AND expires_at > now()
    ORDER BY verified_at DESC, id DESC LIMIT 1;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'FRESH_VERIFIED_RATE_REQUIRED' USING ERRCODE='P0001';
  END IF;

  v_rate := CASE WHEN p_action='buy' THEN r.afn_usd_sell ELSE r.afn_usd_buy END;
  v_margin := CASE WHEN p_action='buy' THEN round(greatest(2::numeric,p_amount*.025),2) ELSE 0 END;
  v_supplier := round(v_margin*.50,2);
  v_saraf := round(v_margin*.30,2);
  v_discount := v_margin - v_supplier - v_saraf;
  v_total_usd := CASE WHEN p_action='buy'
    THEN p_amount + v_supplier + v_saraf ELSE p_amount END;
  v_total_afn := round(v_total_usd*v_rate,1);
  INSERT INTO public.usdt_quotes (
    chat_id,order_type,asset,usdt_amount,usd_rate,fee_percent,
    total_usd,total_afn,status,expires_at,pricing_model,
    market_margin_usd,supplier_profit_usd,saraf_profit_usd,
    customer_discount_usd,supplier_payout_usd,market_price_usd,
    supplier_profit_afn,saraf_profit_afn,customer_discount_afn,
    supplier_payout_afn,market_price_afn
  ) VALUES (
    p_chat_id,p_action,p_asset,p_amount,v_rate,0,
    v_total_usd,v_total_afn,'active',now()+interval '5 minutes',
    CASE WHEN p_action='buy' THEN 'local_margin_share_50_30_20' ELSE 'local_sell' END,
    v_margin,v_supplier,v_saraf,v_discount,p_amount+v_supplier,
    p_amount+v_margin,round(v_supplier*v_rate,1),round(v_saraf*v_rate,1),
    round(v_discount*v_rate,1),round((p_amount+v_supplier)*v_rate,1),
    round((p_amount+v_margin)*v_rate,1)
  ) RETURNING * INTO q;
  INSERT INTO public.saraf_finance_audit (event,actor_id,quote_id,info)
    VALUES ('quote_issued',p_chat_id,q.id,
      jsonb_build_object('asset',p_asset,'action',p_action,'rate_id',r.id));
  RETURN jsonb_build_object(
    'quote_id',q.id,'asset',q.asset,'action',q.order_type,'amount',q.usdt_amount,
    'usd_rate',q.usd_rate,'total_usd',q.total_usd,'total_afn',q.total_afn,
    'expires_at',q.expires_at,'source',r.source,
    'pricing_model',q.pricing_model,'supplier_profit_usd',q.supplier_profit_usd,
    'saraf_profit_usd',q.saraf_profit_usd,'customer_discount_usd',q.customer_discount_usd
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.saraf_submit_order_atomic(
  p_chat_id bigint, p_quote_id bigint, p_idempotency_key text, p_payload jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $$
DECLARE
  a public.saraf_finance_attempts%ROWTYPE;
  q public.usdt_quotes%ROWTYPE;
  p public.user_profiles%ROWTYPE;
  o public.usdt_orders%ROWTYPE;
  v_asset text;
  v_action text;
  v_network text;
  v_method text;
  v_exchange text;
  v_wallet text;
  v_dest text;
  v_payload jsonb;
BEGIN
  IF p_chat_id IS NULL OR p_chat_id<=0 OR p_quote_id IS NULL OR p_quote_id<=0
    OR p_idempotency_key !~ '^[A-Za-z0-9_.:-]{16,128}$'
    OR p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object'
    OR octet_length(p_payload::text)>5000 THEN
    RAISE EXCEPTION 'INVALID_ORDER_INPUT' USING ERRCODE='P0001';
  END IF;
  v_asset := upper(trim(p_payload->>'asset'));
  v_action := trim(p_payload->>'action');
  v_network := upper(trim(p_payload->>'network'));
  v_method := trim(p_payload->>'payment_method');
  v_exchange := trim(p_payload->>'exchange_name');
  v_wallet := trim(p_payload->>'wallet_address');
  IF v_asset NOT IN ('USDT','USDC') OR v_action NOT IN ('buy','sell')
    OR v_method <> 'in_person' OR
    length(v_exchange) NOT BETWEEN 2 AND 120 OR
    v_network NOT IN ('TRC20','ERC20','BEP20','ARBITRUM','BASE',
                      'POLYGON','SOLANA','AVALANCHE','OPTIMISM')
    OR (v_asset='USDT' AND v_network NOT IN ('TRC20','ERC20','BEP20'))
    OR (v_action='buy' AND (
       (v_network='TRC20' AND v_wallet !~ '^T[1-9A-HJ-NP-Za-km-z]{33}$')
       OR (v_network='SOLANA' AND v_wallet !~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$')
       OR (v_network NOT IN ('TRC20','SOLANA') AND v_wallet !~ '^0x[0-9a-fA-F]{40}$')
    )) THEN
    RAISE EXCEPTION 'INVALID_ORDER_DETAILS' USING ERRCODE='P0001';
  END IF;
  -- Only canonical, verified receiving wallets; never trust browser addresses.
  IF v_action='sell' THEN
    SELECT address INTO v_dest FROM public.saraf_finance_wallets
      WHERE asset=v_asset AND network=v_network AND enabled=true;
    IF v_dest IS NULL THEN
      RAISE EXCEPTION 'UNVERIFIED_DEPOSIT_WALLET' USING ERRCODE='P0001';
    END IF;
  END IF;

  -- Unique key, row lock, and exact canonical input equality make retries
  -- idempotent but prevent reusing the key for a different money request.
  v_payload := jsonb_build_object(
    'asset',v_asset,'action',v_action,'network',v_network,
    'payment_method',v_method,'exchange_name',v_exchange,
    'wallet_address',CASE WHEN v_action='buy' THEN v_wallet ELSE NULL END,
    'quote_id',p_quote_id
  );
  INSERT INTO public.saraf_finance_attempts (chat_id,idempotency_key,quote_id,fingerprint)
    VALUES (p_chat_id,p_idempotency_key,p_quote_id,v_payload)
    ON CONFLICT DO NOTHING;
  SELECT * INTO a FROM public.saraf_finance_attempts
    WHERE chat_id=p_chat_id AND idempotency_key=p_idempotency_key FOR UPDATE;
  IF NOT FOUND OR a.fingerprint <> v_payload OR a.quote_id <> p_quote_id THEN
    RAISE EXCEPTION 'IDEMPOTENCY_CONFLICT' USING ERRCODE='P0001';
  END IF;
  IF a.order_id IS NOT NULL THEN
    RETURN jsonb_build_object('order_id',a.order_id,'duplicate',true);
  END IF;
  SELECT * INTO q FROM public.usdt_quotes WHERE id=p_quote_id FOR UPDATE;
  IF NOT FOUND OR q.chat_id <> p_chat_id OR q.asset<>v_asset
    OR q.order_type<>v_action OR q.status<>'active' OR q.expires_at<=now() THEN
    RAISE EXCEPTION 'QUOTE_INVALID_OR_CONSUMED' USING ERRCODE='P0001';
  END IF;
  SELECT * INTO p FROM public.user_profiles WHERE chat_id=p_chat_id FOR UPDATE;
  IF NOT FOUND OR length(coalesce(trim(p.phone),''))<7
    OR length(coalesce(trim(p.first_name),''))<2 OR
    length(coalesce(trim(p.last_name),''))<2 OR p.kyc_status='restricted' THEN
    RAISE EXCEPTION 'PROFILE_REQUIRED_OR_RESTRICTED' USING ERRCODE='P0001';
  END IF;
  IF q.usdt_amount>250 AND (
    p.kyc_status NOT IN ('verified','trusted') OR
    p.id_document_path IS NULL OR p.selfie_path IS NULL
  ) THEN
    RAISE EXCEPTION 'VERIFIED_IDENTITY_REQUIRED' USING ERRCODE='P0001';
  END IF;
  -- Daily anti-abuse cap: aggregate by owner, not client supplied user ID.
  IF (SELECT coalesce(sum(usdt_amount),0) FROM public.usdt_orders
       WHERE chat_id=p_chat_id AND created_at >= now()-interval '24 hours'
         AND status NOT IN ('cancelled','rejected','expired','failed')) + q.usdt_amount > 2000 THEN
    RAISE EXCEPTION 'DAILY_LIMIT_EXCEEDED' USING ERRCODE='P0001';
  END IF;

  INSERT INTO public.usdt_orders (
    chat_id,username,full_name,phone,order_type,asset,usdt_amount,
    usd_rate,fee_percent,total_afn,total_usd,payment_method,receive_method,
    network,wallet_address,exchange_name,status,source,risk_level,
    idempotency_key,quote_id,pricing_model,market_margin_usd,
    supplier_profit_usd,saraf_profit_usd,customer_discount_usd,
    supplier_payout_usd,market_price_usd,supplier_profit_afn,
    saraf_profit_afn,customer_discount_afn,supplier_payout_afn,market_price_afn
  ) VALUES (
    p_chat_id,NULL,p.first_name||' '||p.last_name,p.phone,
    v_action,v_asset,q.usdt_amount,q.usd_rate,q.fee_percent,
    q.total_afn,q.total_usd,
    CASE WHEN v_action='buy' THEN v_method ELSE NULL END,
    CASE WHEN v_action='sell' THEN v_method ELSE NULL END,
    v_network,CASE WHEN v_action='buy' THEN v_wallet ELSE NULL END,
    v_exchange,'pending','miniapp_serverless',
    CASE WHEN q.usdt_amount>=500 THEN 'high'
         WHEN q.usdt_amount>250 THEN 'medium' ELSE 'low' END,
    p_idempotency_key,q.id,q.pricing_model,q.market_margin_usd,
    q.supplier_profit_usd,q.saraf_profit_usd,q.customer_discount_usd,
    q.supplier_payout_usd,q.market_price_usd,q.supplier_profit_afn,
    q.saraf_profit_afn,q.customer_discount_afn,q.supplier_payout_afn,q.market_price_afn
  ) RETURNING * INTO o;

  UPDATE public.usdt_quotes SET status='consumed',consumed_at=now()
    WHERE id=p_quote_id AND status='active';
  IF NOT FOUND THEN
    RAISE EXCEPTION 'QUOTE_CONCURRENTLY_CONSUMED' USING ERRCODE='P0001';
  END IF;
  UPDATE public.saraf_finance_attempts SET order_id=o.id
    WHERE chat_id=p_chat_id AND idempotency_key=p_idempotency_key;
  INSERT INTO public.saraf_finance_audit (event,actor_id,quote_id,order_id,info)
    VALUES ('order_created',p_chat_id,p_quote_id,o.id,
      jsonb_build_object('asset',v_asset,'network',v_network,'action',v_action));
  RETURN jsonb_build_object('order_id',o.id,'duplicate',false,'asset',o.asset,
    'amount',o.usdt_amount,'status',o.status,'total_afn',o.total_afn);
END;
$$;

-- PostgreSQL grants EXECUTE on new functions to PUBLIC by default.
-- This is a strict server-only API even though functions are in exposed public.
REVOKE ALL ON FUNCTION public.saraf_issue_quote_atomic(bigint,text,text,numeric)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.saraf_submit_order_atomic(bigint,bigint,text,jsonb)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_issue_quote_atomic(bigint,text,text,numeric)
  TO service_role;
GRANT EXECUTE ON FUNCTION public.saraf_submit_order_atomic(bigint,bigint,text,jsonb)
  TO service_role;
COMMIT;
