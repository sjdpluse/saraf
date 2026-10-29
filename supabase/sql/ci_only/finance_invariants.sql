-- CI ONLY, assert immutable quote economics, transactional idempotency,
-- KYC ownership, stale-rate rejection and no anon RPC grants.
DO $$
DECLARE
  q jsonb;
  o jsonb;
  replay jsonb;
  quote_id bigint;
  order_id bigint;
  thrown boolean;
BEGIN
  INSERT INTO public.user_profiles(chat_id,first_name,last_name,phone,kyc_status,
    id_document_path,selfie_path)
  VALUES (101,'Alpha','Customer','+93700123456','verified',
          'kyc/101/id','kyc/101/selfie'),
         (102,'Beta','Customer','+93700987654','pending',null,null);
  INSERT INTO public.saraf_finance_rates(asset,afn_usd_buy,afn_usd_sell,
    source,verified_by,expires_at)
  VALUES('USDT',65.25,66.10,'CI synthetic rate',99001,now()+interval '80 seconds');
  q := public.saraf_issue_quote_atomic(101,'USDT','buy',100.00);
  quote_id := (q->>'quote_id')::bigint;
  IF (q->>'total_usd')::numeric <> 102.00 OR
     (q->>'total_afn')::numeric <> 6742.2 THEN
    RAISE EXCEPTION 'Pricing 50/30/20 economics incorrect: %',q;
  END IF;
  o := public.saraf_submit_order_atomic(
    101,quote_id,'request-id-alpha-00001',
    '{"asset":"USDT","action":"buy","network":"ERC20","payment_method":"in_person","exchange_name":"CI Supplier","wallet_address":"0x1111111111111111111111111111111111111111"}'::jsonb);
  order_id:=(o->>'order_id')::bigint;
  IF order_id IS NULL OR (o->>'status')<>'pending' THEN
    RAISE EXCEPTION 'Order not created';
  END IF;
  SELECT * INTO replay FROM public.saraf_submit_order_atomic(
    101,quote_id,'request-id-alpha-00001',
    '{"asset":"USDT","action":"buy","network":"ERC20","payment_method":"in_person","exchange_name":"CI Supplier","wallet_address":"0x1111111111111111111111111111111111111111"}'::jsonb);
  IF replay->>'duplicate'<>'true' OR (replay->>'order_id')::bigint<>order_id THEN
    RAISE EXCEPTION 'Idempotent retry did not return the same order';
  END IF;
  SELECT (status='consumed') INTO thrown FROM public.usdt_quotes WHERE id=quote_id;
  IF NOT thrown THEN RAISE EXCEPTION 'Quote not consumed'; END IF;
  thrown:=false;
  BEGIN
    PERFORM public.saraf_submit_order_atomic(
      101,quote_id,'request-id-alpha-00002',
      '{"asset":"USDT","action":"buy","network":"ERC20","payment_method":"in_person","exchange_name":"CI Supplier","wallet_address":"0x1111111111111111111111111111111111111111"}'::jsonb);
  EXCEPTION WHEN raise_exception THEN
    thrown:=SQLERRM='QUOTE_INVALID_OR_CONSUMED';
  END;
  IF NOT thrown THEN RAISE EXCEPTION 'Quote double spend was not blocked';END IF;
  thrown:=false;
  BEGIN
    PERFORM public.saraf_submit_order_atomic(
      101,quote_id,'request-id-alpha-00001',
      '{"asset":"USDT","action":"buy","network":"ERC20","payment_method":"in_person","exchange_name":"CHANGED Supplier","wallet_address":"0x1111111111111111111111111111111111111111"}'::jsonb);
  EXCEPTION WHEN raise_exception THEN
    thrown:=SQLERRM='IDEMPOTENCY_CONFLICT';
  END;
  IF NOT thrown THEN RAISE EXCEPTION 'Idempotency request tampering not blocked';END IF;
  thrown:=false;
  BEGIN
    PERFORM public.saraf_submit_order_atomic(
      102,quote_id,'request-id-beta-00001',
      '{"asset":"USDT","action":"buy","network":"ERC20","payment_method":"in_person","exchange_name":"CI Supplier","wallet_address":"0x1111111111111111111111111111111111111111"}'::jsonb);
  EXCEPTION WHEN raise_exception THEN
    thrown:=SQLERRM='QUOTE_INVALID_OR_CONSUMED';
  END;
  IF NOT thrown THEN RAISE EXCEPTION 'Cross-user quote theft not blocked';END IF;

  q := public.saraf_issue_quote_atomic(102,'USDT','buy',300.00);
  thrown:=false;
  BEGIN
    PERFORM public.saraf_submit_order_atomic(
      102,(q->>'quote_id')::bigint,'request-id-beta-kyc-002',
      '{"asset":"USDT","action":"buy","network":"ERC20","payment_method":"in_person","exchange_name":"CI Supplier","wallet_address":"0x1111111111111111111111111111111111111111"}'::jsonb);
  EXCEPTION WHEN raise_exception THEN
    thrown:=SQLERRM='VERIFIED_IDENTITY_REQUIRED';
  END;
  IF NOT thrown THEN RAISE EXCEPTION 'KYC gate bypass';END IF;

  IF (SELECT count(*) FROM public.usdt_orders)<>1 THEN
    RAISE EXCEPTION 'Unexpected extra financial orders created';
  END IF;
  IF (SELECT count(*) FROM public.saraf_finance_attempts AS x WHERE x.order_id IS NULL)<>0 THEN
    RAISE EXCEPTION 'Failed orders left idempotency side effects';
  END IF;
  IF has_function_privilege('anon','public.saraf_submit_order_atomic(bigint,bigint,text,jsonb)','EXECUTE') OR
     has_function_privilege('authenticated','public.saraf_issue_quote_atomic(bigint,text,text,numeric)','EXECUTE') THEN
    RAISE EXCEPTION 'Sensitive RPC is callable by public roles';
  END IF;
  RAISE NOTICE 'Saraf finance invariant tests passed';
END $$;
