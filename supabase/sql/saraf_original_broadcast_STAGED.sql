-- Original Saraf /broadcast on the EXISTING users table.
-- This is delivery infrastructure, NOT a new financial feature.
-- STAGED ONLY, NEVER run directly on production without signed-admin E2E.
BEGIN;
SET LOCAL lock_timeout='5s';
CREATE TABLE IF NOT EXISTS public.saraf_original_broadcasts(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 admin_chat_id bigint NOT NULL,
 idempotency_key text NOT NULL,
 message text NOT NULL CHECK(length(message) BETWEEN 1 AND 4096),
 status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','completed')),
 audience_size integer NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT now(),
 completed_at timestamptz,
 UNIQUE(admin_chat_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS public.saraf_original_broadcast_deliveries(
 broadcast_id bigint NOT NULL REFERENCES public.saraf_original_broadcasts(id),
 chat_id bigint NOT NULL,
 state text NOT NULL DEFAULT 'pending'
   CHECK(state IN ('pending','leased','sent','failed','uncertain','skipped')),
 leased_until timestamptz,
 delivered_at timestamptz,
 last_error text,
 PRIMARY KEY(broadcast_id,chat_id)
);
CREATE INDEX IF NOT EXISTS saraf_original_broadcast_pending_idx
 ON public.saraf_original_broadcast_deliveries(state,leased_until,broadcast_id);
ALTER TABLE public.saraf_original_broadcasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saraf_original_broadcast_deliveries ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_original_broadcasts FROM PUBLIC,anon,authenticated;
REVOKE ALL ON public.saraf_original_broadcast_deliveries FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.saraf_original_broadcasts TO service_role;
GRANT SELECT,INSERT,UPDATE ON public.saraf_original_broadcast_deliveries TO service_role;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

CREATE OR REPLACE FUNCTION public.saraf_original_broadcast_create(
 p_admin bigint,p_message text,p_key text)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE v_id bigint;v_message text;v_recipients integer;
BEGIN
 v_message:=btrim(coalesce(p_message,''));
 IF p_admin IS NULL OR p_admin<=0 OR
  length(v_message) NOT BETWEEN 1 AND 4096 OR
  length(coalesce(p_key,'')) NOT BETWEEN 16 AND 120
 THEN RAISE EXCEPTION 'INVALID_BROADCAST' USING ERRCODE='P0001';END IF;
 PERFORM pg_catalog.pg_advisory_xact_lock(
  pg_catalog.hashtextextended('saraf-original-broadcast:'||p_admin||':'||p_key,0));
 SELECT id INTO v_id FROM public.saraf_original_broadcasts
  WHERE admin_chat_id=p_admin AND idempotency_key=p_key;
 IF FOUND THEN
  IF (SELECT message FROM public.saraf_original_broadcasts WHERE id=v_id)
    IS DISTINCT FROM v_message
  THEN RAISE EXCEPTION 'BROADCAST_IDEMPOTENCY_CONFLICT' USING ERRCODE='P0001';END IF;
  RETURN jsonb_build_object('broadcast_id',v_id,'duplicate',true,
   'audience_size',(SELECT audience_size FROM public.saraf_original_broadcasts WHERE id=v_id));
 END IF;
 INSERT INTO public.saraf_original_broadcasts(
   admin_chat_id,idempotency_key,message)
 VALUES(p_admin,p_key,v_message) RETURNING id INTO v_id;
 INSERT INTO public.saraf_original_broadcast_deliveries(broadcast_id,chat_id)
 SELECT v_id,u.chat_id FROM public.users u
 WHERE u.is_active IS TRUE AND u.chat_id>0
 ON CONFLICT DO NOTHING;
 GET DIAGNOSTICS v_recipients = ROW_COUNT;
 UPDATE public.saraf_original_broadcasts
 SET audience_size=v_recipients WHERE id=v_id;
 RETURN jsonb_build_object('broadcast_id',v_id,
  'duplicate',false,'audience_size',v_recipients);
END $$;

-- The worker only claims pending deliveries ONCE. Expired leases are
-- marked 'uncertain' (not retried) because a Telegram timeout can mean that
-- sendMessage succeeded but the HTTP response was lost.
CREATE OR REPLACE FUNCTION public.saraf_original_broadcast_claim(p_limit int)
RETURNS TABLE(broadcast_id bigint,chat_id bigint,message text)
LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
BEGIN
 IF p_limit IS NULL OR p_limit<1 OR p_limit>25
 THEN RAISE EXCEPTION 'INVALID_BATCH_LIMIT' USING ERRCODE='P0001'; END IF;
 UPDATE public.saraf_original_broadcast_deliveries d
 SET state='uncertain',last_error='DELIVERY_LEASE_EXPIRED',leased_until=NULL
 WHERE d.state='leased' AND d.leased_until<now();
 -- Skip opted-out users. Subscribing after broadcast does not retroactively
 -- enroll them, exactly as the original snapshot of active users.
 UPDATE public.saraf_original_broadcast_deliveries d
 SET state='skipped'
 WHERE d.state='pending' AND NOT EXISTS(
  SELECT 1 FROM public.users u WHERE u.chat_id=d.chat_id AND u.is_active IS TRUE);
 RETURN QUERY
 WITH picked AS (
  SELECT d.broadcast_id,d.chat_id
  FROM public.saraf_original_broadcast_deliveries d
  WHERE d.state='pending'
  ORDER BY d.broadcast_id,d.chat_id
  FOR UPDATE SKIP LOCKED LIMIT p_limit
 ), marked AS (
  UPDATE public.saraf_original_broadcast_deliveries d
  SET state='leased',leased_until=now()+interval '90 seconds'
  FROM picked p WHERE d.broadcast_id=p.broadcast_id AND d.chat_id=p.chat_id
  RETURNING d.broadcast_id,d.chat_id
 )
 SELECT m.broadcast_id,m.chat_id,b.message
 FROM marked m JOIN public.saraf_original_broadcasts b ON b.id=m.broadcast_id;
END $$;

CREATE OR REPLACE FUNCTION public.saraf_original_broadcast_finish(
 p_broadcast_id bigint,p_chat_id bigint,p_result text,p_error text DEFAULT NULL)
RETURNS boolean LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE v_count integer;
BEGIN
 IF p_broadcast_id IS NULL OR p_chat_id IS NULL
 OR p_result NOT IN ('sent','failed','uncertain','skipped')
 THEN RETURN false;END IF;
 UPDATE public.saraf_original_broadcast_deliveries d
 SET state=p_result,leased_until=NULL,
     delivered_at=CASE WHEN p_result='sent' THEN now() ELSE NULL END,
     last_error=CASE WHEN p_result='sent' THEN NULL
      ELSE left(coalesce(p_error,'DELIVERY_FAILED'),120) END
 WHERE d.broadcast_id=p_broadcast_id AND d.chat_id=p_chat_id
  AND d.state='leased'
 RETURNING 1 INTO v_count;
 IF v_count IS NULL THEN RETURN false;END IF;
 UPDATE public.saraf_original_broadcasts b
 SET status='completed',completed_at=now()
 WHERE b.id=p_broadcast_id
 AND NOT EXISTS(
  SELECT 1 FROM public.saraf_original_broadcast_deliveries d
  WHERE d.broadcast_id=b.id AND d.state IN ('pending','leased'));
 RETURN true;
END $$;

REVOKE ALL ON FUNCTION public.saraf_original_broadcast_create(bigint,text,text)
 FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.saraf_original_broadcast_claim(integer)
 FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.saraf_original_broadcast_finish(bigint,bigint,text,text)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_original_broadcast_create(bigint,text,text)
 TO service_role;
GRANT EXECUTE ON FUNCTION public.saraf_original_broadcast_claim(integer)
 TO service_role;
GRANT EXECUTE ON FUNCTION public.saraf_original_broadcast_finish(bigint,bigint,text,text)
 TO service_role;
COMMIT;
