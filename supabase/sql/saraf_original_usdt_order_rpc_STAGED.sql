-- STAGED ONLY. The ORIGINAL USDT/USDC order columns; no new ledger/table.
-- Port of main:services/{quote_service,usdt_order_service,usdt_api_guard}.py.
-- Caller MUST validate signed Telegram initData and server-side payment receipt.
-- Apply only after isolated DB parity tests + customer/admin notification checks.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';

CREATE OR REPLACE FUNCTION public.saraf_original_submit_usdt_order(
 p_chat_id bigint,
 p_quote_id bigint,
 p_action text,
 p_asset text,
 p_amount numeric,
 p_idempotency_key text,
 p_payload jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
 q public.usdt_quotes%ROWTYPE;
 profile public.user_profiles%ROWTYPE;
 saved public.usdt_orders%ROWTYPE;
 order_id bigint;
 v_risk text := 'low';
 v_reasons text[] := '{}'::text[];
 v_method text;
 v_network text;
 v_provider text;
 v_username text;
 v_full_name text;
 v_exchange text;
BEGIN
 IF p_chat_id IS NULL OR p_chat_id<=0 OR p_quote_id IS NULL OR p_quote_id<=0
 OR p_action NOT IN ('buy','sell') OR p_asset NOT IN ('USDT','USDC')
 OR p_amount IS NULL OR p_amount<10 OR p_amount>10000
 OR length(coalesce(p_idempotency_key,''))<16
 OR length(coalesce(p_idempotency_key,''))>200
 OR jsonb_typeof(p_payload) IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'INVALID_ORIGINAL_ORDER_INPUT' USING ERRCODE='P0001';
 END IF;
 -- One actor/key at a time, including retries in separate Edge instances.
 PERFORM pg_catalog.pg_advisory_xact_lock(
   pg_catalog.hashtextextended('saraf-usdt:'||p_chat_id||':'||p_idempotency_key,0));
 SELECT * INTO saved FROM public.usdt_orders WHERE
 chat_id=p_chat_id AND idempotency_key=p_idempotency_key LIMIT 1;
 IF FOUND THEN
   IF saved.quote_id IS DISTINCT FROM p_quote_id
      OR saved.order_type IS DISTINCT FROM p_action
      OR saved.asset IS DISTINCT FROM p_asset
      OR saved.usdt_amount IS DISTINCT FROM p_amount THEN
      RAISE EXCEPTION 'IDEMPOTENCY_PAYLOAD_CONFLICT' USING ERRCODE='P0001';
   END IF;
   RETURN jsonb_build_object('order_id',saved.id,
      'order_code',p_asset||'-'||lpad(saved.id::text,5,'0'),
      'duplicate',true);
 END IF;
 -- This single row lock serializes a reused quote with DIFFERENT retry keys.
 SELECT * INTO q FROM public.usdt_quotes
 WHERE id=p_quote_id AND chat_id=p_chat_id FOR UPDATE;
 IF NOT FOUND OR q.asset<>p_asset OR q.order_type<>p_action
     OR q.usdt_amount<>p_amount THEN
   RAISE EXCEPTION 'QUOTE_MISMATCH' USING ERRCODE='P0001';
 END IF;
 IF q.status<>'active' OR q.expires_at<=now() THEN
   RAISE EXCEPTION 'QUOTE_EXPIRED_OR_CONSUMED' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO profile FROM public.user_profiles
 WHERE chat_id=p_chat_id FOR SHARE;
 IF NOT FOUND OR coalesce(profile.first_name,'')=''
     OR coalesce(profile.last_name,'')='' OR coalesce(profile.phone,'')='' THEN
   RAISE EXCEPTION 'BASIC_PROFILE_REQUIRED' USING ERRCODE='P0001';
 END IF;
 IF p_amount>250 AND
   (profile.kyc_status NOT IN ('verified','trusted')
    OR profile.id_document_path IS NULL OR profile.selfie_path IS NULL) THEN
   RAISE EXCEPTION 'IDENTITY_VERIFICATION_REQUIRED' USING ERRCODE='P0001';
 END IF;
 v_method:=trim(coalesce(p_payload->>'method',''));
 v_network:=upper(trim(coalesce(p_payload->>'network','')));
 v_provider:=lower(trim(coalesce(p_payload->>'provider','')));
 v_exchange:=trim(coalesce(p_payload->>'exchange_name',''));
 v_username:=left(trim(coalesce(p_payload->>'telegram_username','')),80);
 v_full_name:=left(trim(coalesce(p_payload->>'telegram_full_name','')),160);
 IF length(v_exchange)<1 OR length(v_exchange)>200
     OR length(v_network)=0 OR v_method NOT IN ('online','in_person') THEN
   RAISE EXCEPTION 'ORIGINAL_ORDER_VALIDATION_FAILED' USING ERRCODE='P0001';
 END IF;
 IF v_method='in_person' AND coalesce(p_payload->>'in_person_code','') !~ '^[0-9]{4}$' THEN
   RAISE EXCEPTION 'IN_PERSON_CODE_INVALID' USING ERRCODE='P0001';
 END IF;
 IF v_method='online' AND (
     v_provider NOT IN ('hesabpay','azizi') OR
     (v_provider='azizi' AND p_amount<=500)) THEN
   RAISE EXCEPTION 'ONLINE_PROVIDER_INVALID' USING ERRCODE='P0001';
 END IF;
 IF p_action='buy' THEN
   IF (p_asset='USDT' AND v_network NOT IN ('TRC20','ERC20','BEP20')) OR
      (p_asset='USDC' AND v_network NOT IN
       ('BEP20','ERC20','ARBITRUM','BASE','POLYGON','SOLANA',
        'AVALANCHE','OPTIMISM')) THEN
     RAISE EXCEPTION 'NETWORK_UNSUPPORTED' USING ERRCODE='P0001';
   END IF;
   IF length(coalesce(p_payload->>'wallet_address',''))<8
     OR length(coalesce(p_payload->>'wallet_address',''))>128 THEN
     RAISE EXCEPTION 'WALLET_INVALID' USING ERRCODE='P0001';
   END IF;
   IF v_method='online' AND length(coalesce(p_payload->>'receipt_file_id',''))<16 THEN
     RAISE EXCEPTION 'OWN_RECEIPT_REQUIRED' USING ERRCODE='P0001';
   END IF;
 ELSE
   IF length(coalesce(p_payload->>'tx_proof',''))<8
     OR length(coalesce(p_payload->>'tx_proof',''))>1500 THEN
     RAISE EXCEPTION 'TX_PROOF_REQUIRED' USING ERRCODE='P0001';
   END IF;
   IF v_method='online' AND length(trim(coalesce(p_payload->>'bank_info','')))<4 THEN
     RAISE EXCEPTION 'BANK_INFO_REQUIRED' USING ERRCODE='P0001';
   END IF;
 END IF;
 -- Original main:services/risk_engine.py. Same defaults, same output flags.
 IF profile.kyc_status='restricted' THEN
   v_risk:='high';
   v_reasons:=array[coalesce(profile.restricted_reason,'کاربر محدودشده')];
 ELSIF coalesce(profile.cancelled_orders,0)>=3 OR
       coalesce(profile.payment_info_change_count,0)>=3 THEN
   v_risk:='high';
   IF coalesce(profile.cancelled_orders,0)>=3 THEN
     v_reasons:=array_append(v_reasons,
       profile.cancelled_orders||' معاملهٔ لغوشده/مشکوک در سابقه');
   END IF;
   IF coalesce(profile.payment_info_change_count,0)>=3 THEN
     v_reasons:=array_append(v_reasons,
       profile.payment_info_change_count||' بار تغییر اطلاعات پرداخت');
   END IF;
 ELSIF profile.kyc_status='pending' OR
    (coalesce(profile.successful_orders,0)<3 AND p_amount>=1000) THEN
   v_risk:='medium';
   IF profile.kyc_status='pending' THEN
     v_reasons:=array_append(v_reasons,'هویت هنوز توسط ادمین تایید نشده');
   END IF;
   IF coalesce(profile.successful_orders,0)<3 AND p_amount>=1000 THEN
     v_reasons:=array_append(v_reasons,'کاربر تازه + مبلغ بالا');
   END IF;
 END IF;
 INSERT INTO public.usdt_orders(
   chat_id,username,full_name,phone,order_type,asset,
   usdt_amount,usd_rate,fee_percent,total_afn,total_usd,
   payment_method,receive_method,exchange_name,network,wallet_address,
   receipt_file_id,tx_proof,bank_info,status,source,risk_level,risk_reasons,
   idempotency_key,quote_id,in_person_code,
   pricing_model,market_margin_usd,supplier_profit_usd,saraf_profit_usd,
   customer_discount_usd,supplier_payout_usd,market_price_usd,
   supplier_profit_afn,saraf_profit_afn,customer_discount_afn,
   supplier_payout_afn,market_price_afn
 ) VALUES(
   p_chat_id,nullif(v_username,''),nullif(v_full_name,''),profile.phone,
   p_action,p_asset,p_amount,q.usd_rate,q.fee_percent,q.total_afn,q.total_usd,
   CASE WHEN p_action='buy' THEN v_method ELSE NULL END,
   CASE WHEN p_action='sell' THEN v_method ELSE NULL END,
   v_exchange,v_network,
   CASE WHEN p_action='buy' THEN p_payload->>'wallet_address' ELSE NULL END,
   CASE WHEN p_action='buy' THEN p_payload->>'receipt_file_id' ELSE NULL END,
   CASE WHEN p_action='sell' THEN p_payload->>'tx_proof' ELSE NULL END,
   CASE WHEN p_action='sell' THEN p_payload->>'bank_info' ELSE NULL END,
   'pending','miniapp',v_risk,nullif(array_to_string(v_reasons,'؛ '),''),
   p_idempotency_key,p_quote_id,
   CASE WHEN v_method='in_person' THEN p_payload->>'in_person_code' ELSE NULL END,
   q.pricing_model,q.market_margin_usd,q.supplier_profit_usd,q.saraf_profit_usd,
   q.customer_discount_usd,q.supplier_payout_usd,q.market_price_usd,
   q.supplier_profit_afn,q.saraf_profit_afn,q.customer_discount_afn,
   q.supplier_payout_afn,q.market_price_afn
 ) RETURNING id INTO order_id;
 UPDATE public.usdt_quotes SET status='consumed',consumed_at=now()
   WHERE id=p_quote_id;
 INSERT INTO public.usdt_order_status_history(order_id,to_status,changed_by,reason)
 VALUES(order_id,'pending',p_chat_id,'Original Mini App order submitted');
 INSERT INTO public.audit_log(actor,action,entity,entity_id,after)
 VALUES(p_chat_id,'order_created','usdt_order',order_id::text,
   jsonb_build_object('asset',p_asset,'type',p_action,'quote_id',p_quote_id));
 RETURN jsonb_build_object('order_id',order_id,
   'order_code',p_asset||'-'||lpad(order_id::text,5,'0'),
   'duplicate',false,'status','pending','risk_level',v_risk);
END $$;
REVOKE ALL ON FUNCTION public.saraf_original_submit_usdt_order(
 bigint,bigint,text,text,numeric,text,jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_original_submit_usdt_order(
 bigint,bigint,text,text,numeric,text,jsonb) TO service_role;
COMMIT;
