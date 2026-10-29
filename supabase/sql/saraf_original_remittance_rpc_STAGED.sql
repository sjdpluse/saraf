-- STAGED ONLY: original main:services/remittance_service.py
-- Uses EXISTING public.remittance_orders/remittance_status_history/audit_log.
-- No new table, no payout transition, no settlement, no new asset registry.
-- Caller is an authenticated Telegram original-bot Supabase Edge Function.
BEGIN;
SET LOCAL lock_timeout='5s';

CREATE OR REPLACE FUNCTION public.saraf_original_create_remittance(
  p_chat_id bigint,p_idempotency_key text,p_asset text,p_network text,
  p_amount numeric,p_usd_rate numeric,p_gross_afn numeric,
  p_fee_percent numeric,p_fee_afn numeric,p_payout_afn numeric,
  p_deposit_wallet text,p_sender_name text,p_sender_country text,
  p_sender_phone text,p_beneficiary_name text,p_beneficiary_phone text,
  p_province text,p_city text,p_address text,p_beneficiary_document text,
  p_asset_price_usd numeric,p_usd_value numeric
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
 r public.remittance_orders%ROWTYPE;
 v_path text;
 v_code text;
BEGIN
 IF p_chat_id IS NULL OR p_chat_id<=0
   OR length(coalesce(p_idempotency_key,'')) NOT BETWEEN 1 AND 120
   OR p_asset NOT IN ('USDT','USDC')
   OR (p_asset='USDT' AND p_network NOT IN ('TRC20','BEP20','ERC20'))
   OR (p_asset='USDC' AND p_network NOT IN ('BEP20','ERC20'))
   OR p_amount IS NULL OR p_amount<=0
   OR p_asset_price_usd IS NULL OR p_asset_price_usd<=0
   OR p_usd_value IS NULL OR p_usd_value<10 OR p_usd_value>10000
   OR p_usd_rate IS NULL OR p_usd_rate<=0
   OR p_gross_afn IS NULL OR p_gross_afn<=0
   OR p_fee_percent IS NULL OR p_fee_percent<0 OR p_fee_percent>25
   OR p_fee_afn IS NULL OR p_fee_afn<0
   OR p_payout_afn IS NULL OR p_payout_afn<=0
   OR p_deposit_wallet IS NULL OR length(trim(p_deposit_wallet))<8
   OR length(trim(coalesce(p_sender_name,''))) NOT BETWEEN 3 AND 160
   OR length(trim(coalesce(p_sender_country,''))) NOT BETWEEN 2 AND 120
   OR length(trim(coalesce(p_beneficiary_name,''))) NOT BETWEEN 3 AND 160
   OR length(trim(coalesce(p_beneficiary_phone,''))) NOT BETWEEN 7 AND 40
   OR length(trim(coalesce(p_province,''))) NOT BETWEEN 2 AND 120
   OR length(trim(coalesce(p_city,''))) NOT BETWEEN 2 AND 120
   OR length(trim(coalesce(p_address,''))) NOT BETWEEN 3 AND 300
 THEN
   RAISE EXCEPTION 'INVALID_ORIGINAL_REMITTANCE' USING ERRCODE='P0001';
 END IF;
 v_path:=trim(coalesce(p_beneficiary_document,''));
 IF position('remittances/'||p_chat_id||'/' IN v_path)<>1
 OR position('..' IN v_path)>0 OR length(v_path)>500
 THEN RAISE EXCEPTION 'OWN_BENEFICIARY_ID_REQUIRED' USING ERRCODE='P0001';
 END IF;
 PERFORM pg_catalog.pg_advisory_xact_lock(
  pg_catalog.hashtextextended('saraf-remittance:'||p_chat_id||':'||p_idempotency_key,0));
 SELECT * INTO r FROM public.remittance_orders
 WHERE chat_id=p_chat_id AND idempotency_key=p_idempotency_key LIMIT 1;
 IF FOUND THEN
  IF r.asset IS DISTINCT FROM p_asset OR r.network IS DISTINCT FROM p_network
   OR r.crypto_amount IS DISTINCT FROM p_amount OR
      r.beneficiary_id_document_path IS DISTINCT FROM v_path THEN
   RAISE EXCEPTION 'REMITTANCE_IDEMPOTENCY_CONFLICT' USING ERRCODE='P0001';
  END IF;
  RETURN jsonb_build_object('id',r.id,'order_code','REM-'||lpad(r.id::text,6,'0'),
   'status',r.status,'duplicate',true,'deposit_wallet',r.deposit_wallet);
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.user_profiles
  WHERE chat_id=p_chat_id AND first_name IS NOT NULL
  AND last_name IS NOT NULL AND phone IS NOT NULL)
 THEN RAISE EXCEPTION 'BASIC_PROFILE_REQUIRED' USING ERRCODE='P0001';
 END IF;
 IF p_usd_value>250 AND NOT EXISTS(SELECT 1 FROM public.user_profiles
  WHERE chat_id=p_chat_id AND kyc_status IN ('verified','trusted')
  AND id_document_path IS NOT NULL AND selfie_path IS NOT NULL)
 THEN RAISE EXCEPTION 'IDENTITY_VERIFICATION_REQUIRED' USING ERRCODE='P0001';
 END IF;
 v_code:=(100000+floor(random()*900000))::int::text;
 INSERT INTO public.remittance_orders(
  chat_id,idempotency_key,sender_country,sender_name,sender_phone,
  beneficiary_full_name,beneficiary_phone,beneficiary_province,
  beneficiary_city,beneficiary_address,beneficiary_id_document_path,
  relationship,purpose,asset,network,crypto_amount,usd_rate,
  gross_afn,fee_percent,fee_afn,payout_afn,deposit_wallet,pickup_code,
  status,verification_status,asset_price_usd,usd_value
 ) VALUES(
  p_chat_id,p_idempotency_key,trim(p_sender_country),trim(p_sender_name),
  nullif(trim(coalesce(p_sender_phone,'')),''),
  trim(p_beneficiary_name),trim(p_beneficiary_phone),trim(p_province),
  trim(p_city),trim(p_address),v_path,
  NULL,NULL,p_asset,p_network,p_amount,p_usd_rate,
  p_gross_afn,p_fee_percent,p_fee_afn,p_payout_afn,
  trim(p_deposit_wallet),v_code,'awaiting_transfer','not_submitted',
  p_asset_price_usd,p_usd_value
 ) RETURNING * INTO r;
 INSERT INTO public.remittance_status_history(
  order_id,from_status,to_status,changed_by,note)
 VALUES(r.id,NULL,'awaiting_transfer',p_chat_id,
 'Order created; waiting for blockchain transfer');
 INSERT INTO public.audit_log(actor,action,entity,entity_id,after)
 VALUES(p_chat_id,'remittance_created','remittance',r.id::text,
  jsonb_build_object('asset',p_asset,'network',p_network));
 RETURN jsonb_build_object('id',r.id,'order_code',
  'REM-'||lpad(r.id::text,6,'0'),
  'status',r.status,'duplicate',false,'deposit_wallet',r.deposit_wallet);
END;
$$;

CREATE OR REPLACE FUNCTION public.saraf_original_claim_remittance_tx(
 p_chat_id bigint,p_order_id bigint,p_tx_hash text
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
 r public.remittance_orders%ROWTYPE;
 previous_status text;
BEGIN
 IF p_chat_id IS NULL OR p_chat_id<=0
   OR p_order_id IS NULL OR p_order_id<=0
   OR length(trim(coalesce(p_tx_hash,'')))<12
   OR length(trim(coalesce(p_tx_hash,'')))>200
 THEN RAISE EXCEPTION 'INVALID_TX_HASH' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO r FROM public.remittance_orders
 WHERE id=p_order_id AND chat_id=p_chat_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'REMITTANCE_NOT_FOUND' USING ERRCODE='P0001'; END IF;
 IF r.status NOT IN ('awaiting_transfer','transfer_submitted') OR
   r.verification_status='verified' THEN
   RAISE EXCEPTION 'REMITTANCE_TX_LOCKED' USING ERRCODE='P0001';
 END IF;
 previous_status:=r.status;
 UPDATE public.remittance_orders SET
  tx_hash=trim(p_tx_hash),status='transfer_submitted',
  verification_status='pending',updated_at=now()
 WHERE id=p_order_id RETURNING * INTO r;
 INSERT INTO public.remittance_status_history(
  order_id,from_status,to_status,changed_by,note)
 VALUES(p_order_id,previous_status,'transfer_submitted',p_chat_id,
  'Tx Hash submitted by sender; sent to admin and blockchain watcher');
 INSERT INTO public.audit_log(actor,action,entity,entity_id,after)
 VALUES(p_chat_id,'remittance_tx_submitted','remittance',p_order_id::text,
  jsonb_build_object('status','transfer_submitted'));
 RETURN jsonb_build_object('id',r.id,'order_code',
  'REM-'||lpad(r.id::text,6,'0'),'status',r.status,
  'verification_status',r.verification_status);
END;
$$;
REVOKE ALL ON FUNCTION public.saraf_original_create_remittance(
 bigint,text,text,text,numeric,numeric,numeric,numeric,numeric,numeric,
 text,text,text,text,text,text,text,text,text,text,numeric,numeric)
 FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.saraf_original_claim_remittance_tx(bigint,bigint,text)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_original_create_remittance(
 bigint,text,text,text,numeric,numeric,numeric,numeric,numeric,numeric,
 text,text,text,text,text,text,text,text,text,text,numeric,numeric) TO service_role;
GRANT EXECUTE ON FUNCTION public.saraf_original_claim_remittance_tx(bigint,bigint,text)
 TO service_role;
COMMIT;
