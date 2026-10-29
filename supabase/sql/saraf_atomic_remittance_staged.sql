-- Saraf staged remittance safety layer, existing legacy data untouched.
-- Do NOT apply automatically until blockchain/treasury integration and audits pass.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';

CREATE TABLE IF NOT EXISTS public.saraf_remittance_quotes(
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  chat_id bigint NOT NULL,
  asset text NOT NULL CHECK(asset IN('USDT','USDC')),
  network text NOT NULL,
  amount numeric(18,2) NOT NULL CHECK(amount BETWEEN 10 AND 1000),
  usd_rate numeric(14,4) NOT NULL CHECK(usd_rate BETWEEN 20 AND 200),
  payout_afn numeric(18,1) NOT NULL CHECK(payout_afn>0),
  deposit_wallet text NOT NULL,
  source_rate_id bigint NOT NULL REFERENCES public.saraf_finance_rates(id),
  status text NOT NULL DEFAULT 'active' CHECK(status IN('active','consumed','expired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  remittance_id bigint UNIQUE REFERENCES public.remittance_orders(id),
  CHECK(expires_at>created_at AND expires_at<=created_at+interval '5 minutes')
);
CREATE TABLE IF NOT EXISTS public.saraf_remittance_attempts(
  chat_id bigint NOT NULL,
  idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 16 AND 128),
  quote_id bigint NOT NULL REFERENCES public.saraf_remittance_quotes(id),
  request jsonb NOT NULL,
  remittance_id bigint UNIQUE REFERENCES public.remittance_orders(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(chat_id,idempotency_key)
);
CREATE UNIQUE INDEX IF NOT EXISTS saraf_remittance_network_tx_uniqueness_idx
 ON public.remittance_orders(network,lower(tx_hash)) WHERE tx_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS saraf_remittance_quotes_owner_idx
 ON public.saraf_remittance_quotes(chat_id,created_at DESC);
ALTER TABLE public.saraf_remittance_quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saraf_remittance_attempts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_remittance_quotes, public.saraf_remittance_attempts
 FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.saraf_remittance_quotes,
 public.saraf_remittance_attempts TO service_role;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- New and legacy remittance payout states are protected by an unconditional
-- database trigger. Existing rows are not rewritten. Any FUTURE transition
-- to payout_ready/completed requires a successful independently verified chain
-- transfer with at least twelve block confirmations and matching asset/network.
CREATE OR REPLACE FUNCTION public.saraf_remittance_payout_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
BEGIN
  IF NEW.status IN ('payout_ready','completed') AND
      NEW.status IS DISTINCT FROM OLD.status AND
     (NEW.verification_status<>'verified'
       OR NEW.chain_confirmations<12
       OR NEW.chain_verified_at IS NULL
       OR NEW.chain_verified_asset IS DISTINCT FROM NEW.asset
       OR NEW.chain_verified_network IS DISTINCT FROM NEW.network
       OR NEW.chain_verified_amount IS NULL
       OR NEW.chain_verified_amount < NEW.crypto_amount) THEN
    RAISE EXCEPTION 'CHAIN_PROOF_REQUIRED_FOR_PAYOUT' USING ERRCODE='P0001';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS saraf_guard_remittance_payout ON public.remittance_orders;
CREATE TRIGGER saraf_guard_remittance_payout
 BEFORE UPDATE OF status ON public.remittance_orders
 FOR EACH ROW EXECUTE FUNCTION public.saraf_remittance_payout_guard();

CREATE OR REPLACE FUNCTION public.saraf_issue_remittance_quote(
 p_chat_id bigint,p_asset text,p_network text,p_amount numeric
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
  r public.saraf_finance_rates%ROWTYPE;
  w public.saraf_finance_wallets%ROWTYPE;
  q public.saraf_remittance_quotes%ROWTYPE;
BEGIN
  IF p_chat_id IS NULL OR p_chat_id<=0 OR p_asset NOT IN('USDT','USDC') OR
     p_network NOT IN ('ERC20','BEP20','ARBITRUM','BASE','POLYGON',
                       'AVALANCHE','OPTIMISM') OR
     (p_asset='USDT' AND p_network NOT IN ('ERC20','BEP20')) OR
     p_amount IS NULL OR p_amount<10 OR p_amount>1000 OR
     p_amount<>round(p_amount,2) THEN
     RAISE EXCEPTION 'INVALID_REMITTANCE_QUOTE' USING ERRCODE='P0001';
  END IF;
  SELECT * INTO w FROM public.saraf_finance_wallets
    WHERE asset=p_asset AND network=p_network AND enabled=true;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'VERIFIED_WALLET_REQUIRED' USING ERRCODE='P0001';
  END IF;
  SELECT * INTO r FROM public.saraf_finance_rates
    WHERE asset=p_asset AND expires_at>now()
    ORDER BY verified_at DESC,id DESC LIMIT 1;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'FRESH_VERIFIED_RATE_REQUIRED' USING ERRCODE='P0001';
  END IF;
  INSERT INTO public.saraf_remittance_quotes(chat_id,asset,network,amount,
    usd_rate,payout_afn,deposit_wallet,source_rate_id,expires_at)
  VALUES (p_chat_id,p_asset,p_network,p_amount,r.afn_usd_buy,
    round(p_amount*r.afn_usd_buy,1),w.address,r.id,
    now()+interval '5 minutes') RETURNING * INTO q;
  RETURN jsonb_build_object('quote_id',q.id,'asset',q.asset,'network',q.network,
     'amount',q.amount,'payout_afn',q.payout_afn,'usd_rate',q.usd_rate,
     'deposit_wallet',q.deposit_wallet,'expires_at',q.expires_at);
END;
$$;

CREATE OR REPLACE FUNCTION public.saraf_submit_remittance_atomic(
 p_chat_id bigint,p_quote_id bigint,p_idempotency_key text,p_details jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
  q public.saraf_remittance_quotes%ROWTYPE;
  p public.user_profiles%ROWTYPE;
  r public.remittance_orders%ROWTYPE;
  a public.saraf_remittance_attempts%ROWTYPE;
  v_sender text;
  v_country text;
  v_name text;
  v_phone text;
  v_province text;
  v_city text;
  v_address text;
  v_request jsonb;
BEGIN
  IF p_chat_id IS NULL OR p_chat_id<=0 OR p_quote_id IS NULL OR p_quote_id<=0
    OR coalesce(p_idempotency_key,'') !~ '^[A-Za-z0-9_.:-]{16,128}$'
    OR p_details IS NULL OR jsonb_typeof(p_details)<>'object'
    OR octet_length(p_details::text)>3000 THEN
    RAISE EXCEPTION 'INVALID_REMITTANCE_REQUEST' USING ERRCODE='P0001';
  END IF;
  v_sender := trim(coalesce(p_details->>'sender_name',''));
  v_country := trim(coalesce(p_details->>'sender_country',''));
  v_name := trim(coalesce(p_details->>'beneficiary_name',''));
  v_phone := trim(coalesce(p_details->>'beneficiary_phone',''));
  v_province := trim(coalesce(p_details->>'beneficiary_province',''));
  v_city := trim(coalesce(p_details->>'beneficiary_city',''));
  v_address := trim(coalesce(p_details->>'beneficiary_address',''));
  IF length(v_sender) NOT BETWEEN 3 AND 160
    OR length(v_country) NOT BETWEEN 2 AND 80
    OR length(v_name) NOT BETWEEN 3 AND 160
    OR length(v_phone) NOT BETWEEN 7 AND 40
    OR length(v_province) NOT BETWEEN 2 AND 80
    OR length(v_city) NOT BETWEEN 2 AND 80
    OR length(v_address) NOT BETWEEN 3 AND 240 THEN
    RAISE EXCEPTION 'INVALID_BENEFICIARY_DETAILS' USING ERRCODE='P0001';
  END IF;
  v_request:=jsonb_build_object('quote_id',p_quote_id,'sender_name',v_sender,
    'sender_country',v_country,'beneficiary_name',v_name,
    'beneficiary_phone',v_phone,'beneficiary_province',v_province,
    'beneficiary_city',v_city,'beneficiary_address',v_address);
  INSERT INTO public.saraf_remittance_attempts(chat_id,idempotency_key,quote_id,request)
    VALUES(p_chat_id,p_idempotency_key,p_quote_id,v_request) ON CONFLICT DO NOTHING;
  SELECT * INTO a FROM public.saraf_remittance_attempts WHERE
    chat_id=p_chat_id AND idempotency_key=p_idempotency_key FOR UPDATE;
  IF NOT FOUND OR a.request<>v_request OR a.quote_id<>p_quote_id THEN
    RAISE EXCEPTION 'REMITTANCE_IDEMPOTENCY_CONFLICT' USING ERRCODE='P0001';
  END IF;
  IF a.remittance_id IS NOT NULL THEN
    RETURN jsonb_build_object('id',a.remittance_id,'duplicate',true);
  END IF;
  SELECT * INTO q FROM public.saraf_remittance_quotes
    WHERE id=p_quote_id FOR UPDATE;
  IF NOT FOUND OR q.chat_id<>p_chat_id OR q.status<>'active'
    OR q.expires_at<=now() THEN
    RAISE EXCEPTION 'REMITTANCE_QUOTE_INVALID' USING ERRCODE='P0001';
  END IF;
  SELECT * INTO p FROM public.user_profiles
    WHERE chat_id=p_chat_id FOR UPDATE;
  IF NOT FOUND OR length(coalesce(trim(p.phone),''))<7
    OR p.kyc_status='restricted' THEN
    RAISE EXCEPTION 'PROFILE_REQUIRED_OR_RESTRICTED' USING ERRCODE='P0001';
  END IF;
  IF q.amount>250 AND (
      p.kyc_status NOT IN ('verified','trusted') OR
      p.id_document_path IS NULL OR p.selfie_path IS NULL) THEN
    RAISE EXCEPTION 'VERIFIED_IDENTITY_REQUIRED' USING ERRCODE='P0001';
  END IF;
  IF (SELECT coalesce(sum(crypto_amount),0) FROM public.remittance_orders
      WHERE chat_id=p_chat_id AND created_at>now()-interval '24 hours'
        AND status NOT IN('cancelled')) + q.amount > 2000 THEN
    RAISE EXCEPTION 'DAILY_LIMIT_EXCEEDED' USING ERRCODE='P0001';
  END IF;
  INSERT INTO public.remittance_orders(
    chat_id,idempotency_key,sender_country,sender_name,
    beneficiary_full_name,beneficiary_phone,beneficiary_province,
    beneficiary_city,beneficiary_address,asset,network,crypto_amount,
    usd_rate,gross_afn,fee_percent,fee_afn,payout_afn,deposit_wallet,
    status,verification_status
  ) VALUES (
    p_chat_id,p_idempotency_key,v_country,v_sender,v_name,v_phone,
    v_province,v_city,v_address,q.asset,q.network,q.amount,q.usd_rate,
    q.payout_afn,0,0,q.payout_afn,q.deposit_wallet,
    'awaiting_transfer','not_submitted'
  ) RETURNING * INTO r;
  UPDATE public.saraf_remittance_quotes SET status='consumed',remittance_id=r.id
    WHERE id=q.id AND status='active';
  IF NOT FOUND THEN
    RAISE EXCEPTION 'REMITTANCE_QUOTE_CONCURRENTLY_CONSUMED' USING ERRCODE='P0001';
  END IF;
  UPDATE public.saraf_remittance_attempts SET remittance_id=r.id
    WHERE chat_id=p_chat_id AND idempotency_key=p_idempotency_key;
  INSERT INTO public.saraf_finance_audit(event,actor_id,info)
    VALUES('remittance_created',p_chat_id,jsonb_build_object('remittance_id',r.id));
  RETURN jsonb_build_object('id',r.id,'duplicate',false,'status',r.status,
    'network',r.network,'asset',r.asset,'amount',r.crypto_amount,
    'payout_afn',r.payout_afn);
END;
$$;

-- TxID is only a CLAIM. It never marks funds verified or enables payout.
CREATE OR REPLACE FUNCTION public.saraf_claim_remittance_tx(
 p_chat_id bigint,p_remittance_id bigint,p_tx_hash text
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
  r public.remittance_orders%ROWTYPE;
  v_hash text;
BEGIN
  v_hash:=lower(trim(coalesce(p_tx_hash,'')));
  IF p_chat_id IS NULL OR p_chat_id<=0 OR p_remittance_id IS NULL
    OR p_remittance_id<=0 OR v_hash !~ '^0x[0-9a-f]{64}$' THEN
    RAISE EXCEPTION 'INVALID_TRANSACTION_HASH' USING ERRCODE='P0001';
  END IF;
  SELECT * INTO r FROM public.remittance_orders
    WHERE id=p_remittance_id AND chat_id=p_chat_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'REMITTANCE_NOT_FOUND' USING ERRCODE='P0001';
  END IF;
  IF r.status='transfer_submitted' AND lower(r.tx_hash)=v_hash THEN
    RETURN jsonb_build_object('id',r.id,'duplicate',true,
      'status',r.status,'verification_status',r.verification_status);
  END IF;
  IF r.status<>'awaiting_transfer' THEN
    RAISE EXCEPTION 'REMITTANCE_TX_LOCKED' USING ERRCODE='P0001';
  END IF;
  IF r.network NOT IN ('ERC20','BEP20','ARBITRUM','BASE','POLYGON',
        'AVALANCHE','OPTIMISM') THEN
    RAISE EXCEPTION 'EVM_VERIFIER_REQUIRED_FOR_NETWORK' USING ERRCODE='P0001';
  END IF;
  UPDATE public.remittance_orders SET tx_hash=v_hash,
    status='transfer_submitted',verification_status='pending',
    chain_confirmations=0,chain_verified_at=NULL,updated_at=now()
    WHERE id=r.id AND status='awaiting_transfer';
  RETURN jsonb_build_object('id',r.id,'duplicate',false,
    'status','transfer_submitted','verification_status','pending');
END;
$$;

REVOKE ALL ON FUNCTION public.saraf_issue_remittance_quote(bigint,text,text,numeric)
 FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.saraf_submit_remittance_atomic(bigint,bigint,text,jsonb)
 FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.saraf_claim_remittance_tx(bigint,bigint,text)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_issue_remittance_quote(bigint,text,text,numeric)
 TO service_role;
GRANT EXECUTE ON FUNCTION public.saraf_submit_remittance_atomic(bigint,bigint,text,jsonb)
 TO service_role;
GRANT EXECUTE ON FUNCTION public.saraf_claim_remittance_tx(bigint,bigint,text)
 TO service_role;
COMMIT;
