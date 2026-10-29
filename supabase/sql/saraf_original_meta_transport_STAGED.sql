-- STAGED FOR RAILWAY EXIT ONLY: durable ingestion of ORIGINAL Meta webhooks.
-- Existing Python Instagram/Facebook automations still implement behavior;
-- this adds just a transport queue (no new product or financial tables).
BEGIN;
SET LOCAL lock_timeout='5s';
CREATE TABLE IF NOT EXISTS public.saraf_meta_delivery_queue (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 platform text NOT NULL CHECK(platform IN ('instagram','facebook')),
 sha256_hex text NOT NULL CHECK(sha256_hex ~ '^[0-9a-f]{64}$'),
 payload jsonb NOT NULL,
 state text NOT NULL DEFAULT 'queued'
  CHECK(state IN ('queued','processing','done','failed')),
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 10),
 leased_until timestamptz,
 last_error text,
 created_at timestamptz NOT NULL DEFAULT now(),
 processed_at timestamptz,
 UNIQUE(platform,sha256_hex)
);
CREATE INDEX IF NOT EXISTS saraf_meta_delivery_queue_ready_idx
 ON public.saraf_meta_delivery_queue(state,leased_until,created_at);
ALTER TABLE public.saraf_meta_delivery_queue ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_meta_delivery_queue FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.saraf_meta_delivery_queue TO service_role;

-- One work item at a time per runner. Claims are row-locked and expire
-- after 3m if the ephemeral Python runner exits unexpectedly.
CREATE OR REPLACE FUNCTION public.saraf_claim_original_meta_delivery()
RETURNS TABLE(delivery_id bigint,platform text,payload jsonb)
LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE v_id bigint;
BEGIN
 WITH candidate AS (
  SELECT d.id FROM public.saraf_meta_delivery_queue d
  WHERE d.attempts<10 AND (
    d.state='queued' OR
    (d.state='processing' AND d.leased_until<now())
  )
  ORDER BY d.created_at ASC
  FOR UPDATE SKIP LOCKED LIMIT 1
 )
 UPDATE public.saraf_meta_delivery_queue d
 SET state='processing',attempts=d.attempts+1,
     leased_until=now()+interval '3 minutes'
 FROM candidate WHERE d.id=candidate.id
 RETURNING d.id INTO v_id;
 IF v_id IS NULL THEN RETURN; END IF;
 RETURN QUERY
 SELECT d.id,d.platform,d.payload
 FROM public.saraf_meta_delivery_queue d WHERE d.id=v_id;
END $$;
CREATE OR REPLACE FUNCTION public.saraf_finish_original_meta_delivery(
 p_id bigint,p_success boolean,p_error text DEFAULT NULL)
RETURNS boolean LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE v_count integer;
BEGIN
 IF p_id IS NULL OR p_id<=0 OR p_success IS NULL THEN RETURN false;END IF;
 UPDATE public.saraf_meta_delivery_queue
 SET state=CASE WHEN p_success THEN 'done'
  WHEN attempts>=10 THEN 'failed' ELSE 'queued' END,
 leased_until=NULL,
 processed_at=CASE WHEN p_success THEN now() ELSE NULL END,
 last_error=CASE WHEN p_success THEN NULL ELSE left(coalesce(p_error,'failed'),150) END
 WHERE id=p_id AND state='processing'
 RETURNING 1 INTO v_count;
 RETURN v_count=1;
END $$;
REVOKE ALL ON FUNCTION public.saraf_claim_original_meta_delivery()
 FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.saraf_finish_original_meta_delivery(bigint,boolean,text)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_claim_original_meta_delivery() TO service_role;
GRANT EXECUTE ON FUNCTION public.saraf_finish_original_meta_delivery(bigint,boolean,text) TO service_role;
COMMIT;
