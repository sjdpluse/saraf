-- STAGED, NOT LIVE: atomic abuse limits for verified Telegram identities.
-- Run AFTER saraf_atomic_finance_staged.sql. Unlike in-memory throttles,
-- counters are shared across all Supabase Edge Function instances.
BEGIN;
SET LOCAL lock_timeout='5s';
CREATE TABLE IF NOT EXISTS public.saraf_finance_api_limits(
  chat_id bigint NOT NULL CHECK(chat_id>0),
  action text NOT NULL CHECK(action IN
    ('quote.issue','order.submit','remittance.quote','remittance.submit',
     'remittance.claimTx','payout.approve','payout.queue')),
  window_started timestamptz NOT NULL DEFAULT now(),
  attempt_count integer NOT NULL DEFAULT 0 CHECK(attempt_count>=0),
  PRIMARY KEY(chat_id,action)
);
ALTER TABLE public.saraf_finance_api_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_finance_api_limits FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.saraf_finance_api_limits TO service_role;

CREATE OR REPLACE FUNCTION public.saraf_limit_finance_api(
 p_chat_id bigint,p_action text
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
 v_limit integer;
 v_row public.saraf_finance_api_limits%ROWTYPE;
BEGIN
 IF p_chat_id IS NULL OR p_chat_id<=0 THEN
   RAISE EXCEPTION 'RATE_LIMIT_DENIED' USING ERRCODE='P0001';
 END IF;
 v_limit:=CASE p_action
   WHEN 'quote.issue' THEN 20
   WHEN 'order.submit' THEN 8
   WHEN 'remittance.quote' THEN 15
   WHEN 'remittance.submit' THEN 8
   WHEN 'remittance.claimTx' THEN 8
   WHEN 'payout.approve' THEN 12
   WHEN 'payout.queue' THEN 8
   ELSE NULL END;
 IF v_limit IS NULL THEN
   RAISE EXCEPTION 'RATE_LIMIT_DENIED' USING ERRCODE='P0001';
 END IF;
 INSERT INTO public.saraf_finance_api_limits(chat_id,action,window_started,attempt_count)
 VALUES(p_chat_id,p_action,now(),1)
 ON CONFLICT(chat_id,action) DO UPDATE SET
  attempt_count=CASE
    WHEN public.saraf_finance_api_limits.window_started<=now()-interval '5 minutes'
      THEN 1 ELSE public.saraf_finance_api_limits.attempt_count+1 END,
  window_started=CASE
    WHEN public.saraf_finance_api_limits.window_started<=now()-interval '5 minutes'
      THEN now() ELSE public.saraf_finance_api_limits.window_started END
 RETURNING * INTO v_row;
 IF v_row.attempt_count>v_limit THEN
   -- Raise inside transaction means attempts beyond limit are rolled back,
   -- preserving the fixed window rather than resetting it on retries.
   RAISE EXCEPTION 'FINANCIAL_RATE_LIMIT_EXCEEDED' USING ERRCODE='P0001';
 END IF;
 RETURN jsonb_build_object(
   'remaining',v_limit-v_row.attempt_count,
   'resets_at',v_row.window_started+interval '5 minutes');
END;
$$;
REVOKE ALL ON FUNCTION public.saraf_limit_finance_api(bigint,text)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_limit_finance_api(bigint,text)
 TO service_role;
COMMIT;
