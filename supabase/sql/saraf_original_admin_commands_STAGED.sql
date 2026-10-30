-- ORIGINAL Saraf admin command persistence — STAGED, never production.
-- main:handlers/admin.py (/setspread and /usdtconfirm), existing tables only.
-- Edge must first verify original Telegram Mini App initData signature AND
-- membership in a server-only SARAF_ADMIN_CHAT_IDS allowlist.
BEGIN;
SET LOCAL lock_timeout='5s';

CREATE OR REPLACE FUNCTION public.saraf_original_admin_confirm(
 p_admin bigint,p_order_id bigint
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
 v_order public.usdt_orders%ROWTYPE;
 v_history_id bigint;
 v_before text;
BEGIN
 IF p_admin IS NULL OR p_admin<=0 OR p_order_id IS NULL OR p_order_id<=0
 THEN RAISE EXCEPTION 'INVALID_ADMIN_INPUT' USING ERRCODE='P0001';END IF;

 SELECT * INTO v_order FROM public.usdt_orders
 WHERE id=p_order_id FOR UPDATE;
 IF NOT FOUND THEN
  RAISE EXCEPTION 'ORDER_NOT_FOUND' USING ERRCODE='P0001';
 END IF;
 v_before:=v_order.status;
 IF v_before='confirmed' THEN
  RETURN jsonb_build_object('order_id',v_order.id,
   'chat_id',v_order.chat_id,'status','confirmed','duplicate',true);
 END IF;

 -- Matches original services/order_state_machine.py for to=confirmed.
 IF v_before NOT IN ('pending','payment_submitted','under_review') THEN
  RAISE EXCEPTION 'INVALID_ORDER_TRANSITION' USING ERRCODE='P0001';
 END IF;
 UPDATE public.usdt_orders
 SET status='confirmed',confirmed_at=now()
 WHERE id=p_order_id AND status=v_before;

 -- Existing canonical database trigger writes the transition history.
 -- On synthetic old schemas without that trigger, add one row.
 UPDATE public.usdt_order_status_history
 SET changed_by=p_admin,reason='تایید از طریق دستور /usdtconfirm'
 WHERE id=(
   SELECT h.id FROM public.usdt_order_status_history h
   WHERE h.order_id=p_order_id AND h.to_status='confirmed'
     AND h.changed_by IS NULL
   ORDER BY h.id DESC LIMIT 1 FOR UPDATE
 ) RETURNING id INTO v_history_id;
 IF v_history_id IS NULL THEN
   INSERT INTO public.usdt_order_status_history(
    order_id,from_status,to_status,changed_by,reason)
   VALUES(p_order_id,v_before,'confirmed',p_admin,
     'تایید از طریق دستور /usdtconfirm');
 END IF;
 INSERT INTO public.audit_log(actor,action,entity,entity_id,before,after,reason)
 VALUES(p_admin,'order_confirmed','usdt_order',p_order_id::text,
  jsonb_build_object('status',v_before),
  jsonb_build_object('status','confirmed'),
  'تایید از طریق دستور /usdtconfirm');
 RETURN jsonb_build_object('order_id',v_order.id,
  'chat_id',v_order.chat_id,'status','confirmed','duplicate',false);
END $$;

CREATE OR REPLACE FUNCTION public.saraf_original_admin_set_spread(
 p_admin bigint,p_currency text,p_percent numeric
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE v_code text;v_previous numeric;v_present boolean;
BEGIN
 v_code:=lower(trim(coalesce(p_currency,'')));
 IF p_admin IS NULL OR p_admin<=0 OR
 v_code NOT IN ('usd','eur','gbp','pkr','irr','aed','inr','sar',
  'try','cny','aud','cad','chf','sek') OR
 p_percent IS NULL OR p_percent<0 OR p_percent>20 THEN
  RAISE EXCEPTION 'INVALID_SPREAD_INPUT' USING ERRCODE='P0001';
 END IF;
 SELECT spread_percent INTO v_previous
 FROM public.spread_settings WHERE currency=v_code FOR UPDATE;
 v_present:=FOUND;
 IF v_present AND v_previous=p_percent THEN
   RETURN jsonb_build_object('currency',v_code,
    'spread_percent',p_percent,'duplicate',true);
 END IF;
 INSERT INTO public.spread_settings(currency,spread_percent,updated_at)
 VALUES(v_code,p_percent,now())
 ON CONFLICT (currency) DO UPDATE
 SET spread_percent=excluded.spread_percent,updated_at=excluded.updated_at;

 INSERT INTO public.audit_log(actor,action,entity,entity_id,before,after,reason)
 VALUES(p_admin,'spread_changed','spread_setting',v_code,
  CASE WHEN v_present THEN jsonb_build_object('spread_percent',v_previous)
  ELSE NULL END,
  jsonb_build_object('spread_percent',p_percent),
  'تنظیم از طریق /setspread');
 RETURN jsonb_build_object('currency',v_code,
  'spread_percent',p_percent,'duplicate',false);
END $$;

-- Existing original admin_bot.py callback names:
-- admin_kyc_verify:<chat_id> / admin_kyc_reject:<chat_id>.
-- Atomic update + audit, original user_profiles only, no new KYC ledger.
CREATE OR REPLACE FUNCTION public.saraf_original_admin_review_kyc(
 p_admin bigint,p_chat_id bigint,p_status text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
 v_profile public.user_profiles%ROWTYPE;
 v_reason text;
BEGIN
 IF p_admin IS NULL OR p_admin<=0 OR p_chat_id IS NULL OR p_chat_id<=0
   OR p_status NOT IN ('verified','restricted') THEN
   RAISE EXCEPTION 'INVALID_KYC_REVIEW' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO v_profile FROM public.user_profiles
 WHERE chat_id=p_chat_id FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'KYC_PROFILE_NOT_FOUND' USING ERRCODE='P0001';END IF;
 -- Old inline buttons must not re-approve an already rejected customer.
 IF v_profile.kyc_status=p_status THEN
  RETURN jsonb_build_object('chat_id',p_chat_id,'status',p_status,'duplicate',true);
 END IF;
 IF v_profile.kyc_status<>'pending' THEN
  RAISE EXCEPTION 'KYC_NOT_PENDING' USING ERRCODE='P0001';
 END IF;
 IF nullif(trim(coalesce(v_profile.id_document_path,'')),'') IS NULL
  OR nullif(trim(coalesce(v_profile.selfie_path,'')),'') IS NULL THEN
   RAISE EXCEPTION 'KYC_DOCUMENTS_MISSING' USING ERRCODE='P0001';
 END IF;
 v_reason:=CASE WHEN p_status='restricted'
  THEN 'رد شده در بررسی اولیهٔ هویت' ELSE NULL END;
 UPDATE public.user_profiles SET kyc_status=p_status,
   verified_by=CASE WHEN p_status='verified' THEN p_admin ELSE verified_by END,
   verified_at=CASE WHEN p_status='verified' THEN now() ELSE verified_at END,
   restricted_reason=v_reason
 WHERE chat_id=p_chat_id;
 INSERT INTO public.audit_log(actor,action,entity,entity_id,before,after,reason)
 VALUES(p_admin,'kyc_'||p_status,'user_profile',p_chat_id::text,
  jsonb_build_object('kyc_status','pending'),
  jsonb_build_object('kyc_status',p_status),v_reason);
 RETURN jsonb_build_object('chat_id',p_chat_id,'status',p_status,'duplicate',false);
END $$;

REVOKE ALL ON FUNCTION public.saraf_original_admin_confirm(bigint,bigint)
 FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.saraf_original_admin_set_spread(bigint,text,numeric)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_original_admin_confirm(bigint,bigint)
 TO service_role;
GRANT EXECUTE ON FUNCTION public.saraf_original_admin_set_spread(bigint,text,numeric)
 TO service_role;
REVOKE ALL ON FUNCTION public.saraf_original_admin_review_kyc(bigint,bigint,text)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_original_admin_review_kyc(bigint,bigint,text)
 TO service_role;
COMMIT;
