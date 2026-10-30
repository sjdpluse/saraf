-- Synthetic existing customer profiles + original quotes. Never prod data.
INSERT INTO public.user_profiles(chat_id,first_name,last_name,phone,kyc_status,
  id_document_path,selfie_path)
VALUES
 (101,'Example','Verified','0700000001','verified','101_id.jpg','101_selfie.jpg'),
 (202,'Example','Pending','0700000002','pending',null,null);
INSERT INTO public.usdt_quotes(chat_id,order_type,asset,usdt_amount,usd_rate,
 fee_percent,total_afn,total_usd,expires_at,pricing_model)
VALUES
 (101,'buy','USDT',100,66.1,0,6742.2,102,now()+interval '10 minutes',
  'local_margin_share_50_30_20'),
 (101,'sell','USDC',50,65,0,3250,50,now()+interval '10 minutes',null),
 (202,'buy','USDC',300,66.1,0,20226.6,306,now()+interval '10 minutes',
  'local_margin_share_50_30_20'),
 (101,'buy','USDT',40,66.1,0,2730.93,41.2,now()-interval '5 minutes',
  'local_margin_share_50_30_20'),
 (101,'buy','USDC',10,66.1,0,766.8,11.6,now()+interval '10 minutes',
  'local_margin_share_50_30_20');

DO $$
DECLARE
 r jsonb; v_id bigint; bad boolean; n integer;
 payload jsonb:='{"network":"ERC20","method":"in_person",
    "exchange_name":"Original Exchanger","wallet_address":"0x1111111111111111111111111111111111111111",
    "in_person_code":"4312","telegram_username":"sample"}';
BEGIN
 r:=public.saraf_original_submit_usdt_order(
  101,1,'buy','USDT',100,'order-example-000001',payload);
 v_id:=(r->>'order_id')::bigint;
 IF r->>'order_code'<>'USDT-00001' OR r->>'status'<>'pending' THEN
  RAISE EXCEPTION 'ORIGINAL_ORDER_RESPONSE_MISMATCH: %',r;
 END IF;
 IF (SELECT quote_id FROM public.usdt_orders WHERE id=v_id)<>1
  OR (SELECT status FROM public.usdt_quotes WHERE id=1)<>'consumed'
  THEN RAISE EXCEPTION 'QUOTE_NOT_CONSUMED_ATOMICALLY';END IF;
 IF (SELECT total_afn FROM public.usdt_orders WHERE id=v_id)<>6742.2
  OR (SELECT pricing_model FROM public.usdt_orders WHERE id=v_id)
    <>'local_margin_share_50_30_20'
  THEN RAISE EXCEPTION 'ORIGINAL_QUOTE_PRICING_CORRUPTED';END IF;
 r:=public.saraf_original_submit_usdt_order(
  101,1,'buy','USDT',100,'order-example-000001',payload);
 IF (r->>'order_id')::bigint<>v_id OR NOT (r->>'duplicate')::boolean
  THEN RAISE EXCEPTION 'IDEMPOTENT_RETRY_CREATED_MORE_ORDERS';END IF;
 bad:=false;
 BEGIN
  PERFORM public.saraf_original_submit_usdt_order(
   101,1,'buy','USDT',100,'order-example-000002',payload);
 EXCEPTION WHEN raise_exception THEN bad:=SQLERRM='QUOTE_EXPIRED_OR_CONSUMED';END;
 IF NOT bad THEN RAISE EXCEPTION 'DIFFERENT_IDEMPOTENCY_KEY_REUSED_QUOTE';END IF;
 bad:=false;
 BEGIN
  PERFORM public.saraf_original_submit_usdt_order(
   202,2,'sell','USDC',50,'order-example-000003',payload);
 EXCEPTION WHEN raise_exception THEN bad:=SQLERRM='QUOTE_MISMATCH';END;
 IF NOT bad THEN RAISE EXCEPTION 'CUSTOMER_STOLE_OTHER_QUOTE';END IF;
 bad:=false;
 BEGIN
  PERFORM public.saraf_original_submit_usdt_order(
   202,3,'buy','USDC',300,'order-example-000004',payload);
 EXCEPTION WHEN raise_exception THEN bad:=SQLERRM='IDENTITY_VERIFICATION_REQUIRED';END;
 IF NOT bad THEN RAISE EXCEPTION 'KYC_BYPASS_FOR_300_USD';END IF;
 bad:=false;
 BEGIN
  PERFORM public.saraf_original_submit_usdt_order(
   101,4,'buy','USDT',40,'order-example-000005',payload);
 EXCEPTION WHEN raise_exception THEN bad:=SQLERRM='QUOTE_EXPIRED_OR_CONSUMED';END;
 IF NOT bad THEN RAISE EXCEPTION 'EXPIRED_QUOTE_ACCEPTED';END IF;
 bad:=false;
 BEGIN
  PERFORM public.saraf_original_submit_usdt_order(
   101,5,'buy','USDC',10,'order-example-000006',
   payload||'{"network":"TRC20"}'::jsonb);
 EXCEPTION WHEN raise_exception THEN bad:=SQLERRM='NETWORK_UNSUPPORTED';END;
 IF NOT bad THEN RAISE EXCEPTION 'WRONG_NETWORK_ASSET_ACCEPTED';END IF;
 IF has_function_privilege('anon',
   'public.saraf_original_submit_usdt_order(bigint,bigint,text,text,numeric,text,jsonb)','EXECUTE')
 OR has_function_privilege('authenticated',
   'public.saraf_original_submit_usdt_order(bigint,bigint,text,text,numeric,text,jsonb)','EXECUTE')
 THEN RAISE EXCEPTION 'PUBLIC_MONEY_RPC_EXPOSED';END IF;
 SELECT count(*) INTO n FROM public.usdt_orders;
 IF n<>1 THEN RAISE EXCEPTION 'DUPLICATE_ORDERS_WRITTEN';END IF;
 IF (SELECT count(*) FROM public.audit_log WHERE entity='usdt_order')<>1 THEN
  RAISE EXCEPTION 'AUDIT_NOT_RECORDED';END IF;
 RAISE NOTICE 'All original Saraf quote/order assertions passed';
END $$;
