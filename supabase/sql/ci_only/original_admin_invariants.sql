-- Synthetic checks for original main:handlers/admin.py.
-- Must execute ONLY AFTER original_usdt_order_invariants.sql.
DO $$
DECLARE
 r jsonb; v_id bigint; blocked boolean; audit_before integer; audit_after integer;
BEGIN
 SELECT id INTO v_id FROM public.usdt_orders ORDER BY id LIMIT 1;
 IF v_id IS NULL THEN RAISE EXCEPTION 'NO_SYNTHETIC_ORDER_FOR_ADMIN_TEST';END IF;
 SELECT count(*) INTO audit_before FROM public.audit_log;
 r:=public.saraf_original_admin_confirm(997,v_id);
 IF r->>'status'<>'confirmed' OR (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_ADMIN_CONFIRM_FAILED: %',r;END IF;
 IF (SELECT status FROM public.usdt_orders WHERE id=v_id)<>'confirmed'
 OR (SELECT confirmed_at FROM public.usdt_orders WHERE id=v_id) IS NULL
 THEN RAISE EXCEPTION 'ORIGINAL_CONFIRM_NOT_PERSISTED'; END IF;
 IF (SELECT count(*) FROM public.usdt_order_status_history WHERE order_id=v_id
   AND to_status='confirmed' AND changed_by=997)<>1 THEN
   RAISE EXCEPTION 'ORIGINAL_CONFIRM_MISSING_ATTRIBUTION';END IF;
 r:=public.saraf_original_admin_confirm(997,v_id);
 IF NOT (r->>'duplicate')::boolean THEN
   RAISE EXCEPTION 'ORIGINAL_ADMIN_CONFIRM_RETRY_NOT_IDEMPOTENT';END IF;
 SELECT count(*) INTO audit_after FROM public.audit_log;
 IF audit_after<>audit_before+1 THEN
   RAISE EXCEPTION 'CONFIRMATION_AUDIT_DUPLICATED';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_confirm(997,999999999);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='ORDER_NOT_FOUND';END;
 IF NOT blocked THEN RAISE EXCEPTION 'INVALID_ORDER_CONFIRMED';END IF;

 INSERT INTO public.usdt_orders(chat_id,order_type,asset,usdt_amount,usd_rate,
  total_afn,total_usd,status)
 VALUES(101,'sell','USDT',20,65,1300,20,'completed') RETURNING id INTO v_id;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_confirm(997,v_id);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='INVALID_ORDER_TRANSITION';END;
 IF NOT blocked THEN RAISE EXCEPTION 'COMPLETED_ORDER_RECONFIRMED';END IF;

 r:=public.saraf_original_admin_set_spread(997,'usd',0.8);
 IF r->>'currency'<>'usd' OR (r->>'spread_percent')::numeric<>0.8 THEN
   RAISE EXCEPTION 'ORIGINAL_SPREAD_SET_FAILED';END IF;
 IF (SELECT spread_percent FROM public.spread_settings WHERE currency='usd')<>0.8
 THEN RAISE EXCEPTION 'ORIGINAL_SPREAD_NOT_SAVED';END IF;
 r:=public.saraf_original_admin_set_spread(997,'usd',0.8);
 IF NOT (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_SPREAD_RETRY_NOT_IDEMPOTENT';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_set_spread(997,'usd',22);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='INVALID_SPREAD_INPUT';END;
 IF NOT blocked THEN RAISE EXCEPTION 'UNSAFE_SPREAD_ACCEPTED';END IF;
 IF has_function_privilege('anon','public.saraf_original_admin_confirm(bigint,bigint)','EXECUTE')
 OR has_function_privilege('authenticated',
   'public.saraf_original_admin_confirm(bigint,bigint)','EXECUTE')
 OR has_function_privilege('anon',
   'public.saraf_original_admin_set_spread(bigint,text,numeric)','EXECUTE')
 THEN RAISE EXCEPTION 'ADMIN_RPC_PUBLIC';END IF;
 RAISE NOTICE 'Original Saraf admin command invariants PASSED';
END $$;
