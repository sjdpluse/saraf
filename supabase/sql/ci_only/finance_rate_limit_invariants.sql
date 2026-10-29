-- CI only: abuse limits must be atomic, per-identity, per-action and fixed-window.
DO $$
DECLARE
  i integer;
  v_result jsonb;
  v_throttled boolean;
  v_count integer;
BEGIN
  FOR i IN 1..8 LOOP
    v_result:=public.saraf_limit_finance_api(101,'order.submit');
  END LOOP;
  IF (v_result->>'remaining')::integer<>0 THEN
    RAISE EXCEPTION 'Order limit not enforced on eighth call';
  END IF;
  v_throttled:=false;
  BEGIN
    PERFORM public.saraf_limit_finance_api(101,'order.submit');
  EXCEPTION WHEN raise_exception THEN
    v_throttled:=SQLERRM='FINANCIAL_RATE_LIMIT_EXCEEDED';
  END;
  IF NOT v_throttled THEN
    RAISE EXCEPTION 'Ninth order attempt bypassed rate limit';
  END IF;
  SELECT attempt_count INTO v_count FROM public.saraf_finance_api_limits
    WHERE chat_id=101 AND action='order.submit';
  IF v_count<>8 THEN
    RAISE EXCEPTION 'Rate limit erroneously mutated after denial';
  END IF;
  -- Different identity and different financial operation have independent quotas.
  v_result:=public.saraf_limit_finance_api(102,'order.submit');
  IF (v_result->>'remaining')::integer<>7 THEN
    RAISE EXCEPTION 'Cross-user quota shared';
  END IF;
  v_result:=public.saraf_limit_finance_api(101,'quote.issue');
  IF (v_result->>'remaining')::integer<>19 THEN
    RAISE EXCEPTION 'Quote and order quotas not isolated';
  END IF;
  UPDATE public.saraf_finance_api_limits
    SET window_started=now()-interval '6 minutes'
    WHERE chat_id=101 AND action='order.submit';
  v_result:=public.saraf_limit_finance_api(101,'order.submit');
  IF (v_result->>'remaining')::integer<>7 THEN
    RAISE EXCEPTION 'Expired time window did not restart';
  END IF;
  v_throttled:=false;
  BEGIN
    PERFORM public.saraf_limit_finance_api(101,'unknown.security.action');
  EXCEPTION WHEN raise_exception THEN
    v_throttled:=SQLERRM='RATE_LIMIT_DENIED';
  END;
  IF NOT v_throttled THEN RAISE EXCEPTION 'Unlisted API action allowed';END IF;
  IF has_function_privilege('anon','public.saraf_limit_finance_api(bigint,text)','EXECUTE')
    OR has_function_privilege('authenticated',
      'public.saraf_limit_finance_api(bigint,text)','EXECUTE') THEN
    RAISE EXCEPTION 'Public could call/abuse rate-limit accounting';END IF;
  RAISE NOTICE 'Saraf financial rate limiting invariants passed';
END $$;
