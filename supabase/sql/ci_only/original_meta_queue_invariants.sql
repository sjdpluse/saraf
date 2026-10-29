-- Isolated synthetic Meta webhook transport tests; NEVER production.
INSERT INTO public.saraf_meta_delivery_queue(platform,sha256_hex,payload)
VALUES('instagram',repeat('a',64),'{"object":"instagram","entry":[{"id":"synthetic-1"}]}');
INSERT INTO public.saraf_meta_delivery_queue(platform,sha256_hex,payload)
VALUES('facebook',repeat('b',64),'{"object":"page","entry":[{"id":"synthetic-2"}]}');
INSERT INTO public.saraf_meta_delivery_queue(platform,sha256_hex,payload)
VALUES('instagram',repeat('a',64),'{"object":"instagram","entry":[{"id":"synthetic-1"}]}')
ON CONFLICT(platform,sha256_hex) DO NOTHING;

DO $$
DECLARE id_1 bigint; id_2 bigint; first_platform text; n integer;
BEGIN
 SELECT count(*) INTO n FROM public.saraf_meta_delivery_queue;
 IF n<>2 THEN RAISE EXCEPTION 'DUPLICATE_META_DELIVERY_CREATED';END IF;
 SELECT delivery_id,platform INTO id_1,first_platform
 FROM public.saraf_claim_original_meta_delivery();
 IF id_1 IS NULL OR first_platform<>'instagram'
 THEN RAISE EXCEPTION 'FIRST_META_LEASE_FAILED';END IF;
 SELECT delivery_id INTO id_2 FROM public.saraf_claim_original_meta_delivery();
 IF id_2 IS NULL OR id_2=id_1
 THEN RAISE EXCEPTION 'META_CLAIM_LOCK_NOT_RESPECTED';END IF;
 IF NOT public.saraf_finish_original_meta_delivery(id_1,true,null)
 THEN RAISE EXCEPTION 'META_COMPLETE_FAILED';END IF;
 IF (SELECT state FROM public.saraf_meta_delivery_queue WHERE id=id_1)<>'done'
 THEN RAISE EXCEPTION 'META_DELIVERY_NOT_DONE';END IF;
 IF NOT public.saraf_finish_original_meta_delivery(id_2,false,'synthetic')
 THEN RAISE EXCEPTION 'META_FAILURE_NOT_RECORDED';END IF;
 SELECT delivery_id INTO id_2 FROM public.saraf_claim_original_meta_delivery();
 IF id_2 IS NULL THEN RAISE EXCEPTION 'RETRYABLE_META_EVENT_NOT_AVAILABLE';END IF;
 IF has_table_privilege('anon','public.saraf_meta_delivery_queue','SELECT')
   OR has_table_privilege('authenticated',
       'public.saraf_meta_delivery_queue','SELECT')
 THEN RAISE EXCEPTION 'META_PERSONAL_MESSAGES_EXPOSED';END IF;
 IF has_function_privilege('anon',
   'public.saraf_claim_original_meta_delivery()','EXECUTE')
 THEN RAISE EXCEPTION 'ANON_COULD_CLAIM_META_EVENTS';END IF;
 RAISE NOTICE 'Original Meta webhook delivery invariants passed';
END $$;
