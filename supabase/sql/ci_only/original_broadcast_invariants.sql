-- Synthetic broadcast safety tests only; never send real Telegram messages.
INSERT INTO public.users(chat_id,is_active)
VALUES(101,true),(202,true),(303,false);
DO $$
DECLARE first_id bigint; second_id bigint;
 receipt record; n int; ok boolean; blocked boolean;
BEGIN
 SELECT (public.saraf_original_broadcast_create(
 997,'Original broadcast test','synthetic-broadcast-key-00001')->>'broadcast_id')::bigint
 INTO first_id;
 IF first_id IS NULL THEN RAISE EXCEPTION 'BROADCAST_NOT_CREATED';END IF;
 IF (SELECT audience_size FROM public.saraf_original_broadcasts WHERE id=first_id)<>2
 THEN RAISE EXCEPTION 'ORIGINAL_OPTED_OUT_USER_ENQUEUED';END IF;
 IF NOT (public.saraf_original_broadcast_create(
  997,'Original broadcast test','synthetic-broadcast-key-00001')->>'duplicate')::boolean
 THEN RAISE EXCEPTION 'BROADCAST_RETRY_NOT_IDEMPOTENT';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_broadcast_create(
    997,'Other message','synthetic-broadcast-key-00001');
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='BROADCAST_IDEMPOTENCY_CONFLICT';END;
 IF NOT blocked THEN RAISE EXCEPTION 'BROADCAST_IDEMPOTENCY_CONFLICT_ALLOWED';END IF;
 SELECT count(*) INTO n FROM public.saraf_original_broadcast_deliveries;
 IF n<>2 THEN RAISE EXCEPTION 'DUPLICATE_BROADCAST_DELIVERY';END IF;
 -- Opt out after queue snapshot, before send: original /stop must win.
 UPDATE public.users SET is_active=false WHERE chat_id=202;
 SELECT * INTO receipt FROM public.saraf_original_broadcast_claim(2);
 IF receipt.chat_id<>101 THEN
  RAISE EXCEPTION 'OPTED_OUT_RECIPIENT_WAS_SENT';
 END IF;
 IF (SELECT state FROM public.saraf_original_broadcast_deliveries
    WHERE chat_id=202 AND broadcast_id=first_id)<>'skipped'
 THEN RAISE EXCEPTION 'OPTED_OUT_RECIPIENT_NOT_SKIPPED';END IF;
 ok:=public.saraf_original_broadcast_finish(first_id,101,'sent',null);
 IF NOT ok THEN RAISE EXCEPTION 'BROADCAST_SEND_NOT_FINALIZED';END IF;
 IF public.saraf_original_broadcast_finish(first_id,101,'sent',null)
 THEN RAISE EXCEPTION 'BROADCAST_DELIVERY_FINALIZED_TWICE';END IF;
 IF (SELECT status FROM public.saraf_original_broadcasts WHERE id=first_id)
 <>'completed' THEN RAISE EXCEPTION 'BROADCAST_NOT_COMPLETED';END IF;
 SELECT count(*) INTO n FROM public.saraf_original_broadcast_claim(25);
 IF n<>0 THEN RAISE EXCEPTION 'BROADCAST_RECLAIMED_DELIVERED_MESSAGES';END IF;
 blocked:=false;
 BEGIN PERFORM public.saraf_original_broadcast_claim(50);
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='INVALID_BATCH_LIMIT';END;
 IF NOT blocked THEN RAISE EXCEPTION 'UNSAFE_BATCH_LIMIT_ACCEPTED';END IF;
 IF has_table_privilege('anon','public.saraf_original_broadcasts','SELECT') OR
    has_table_privilege('authenticated','public.saraf_original_broadcast_deliveries','SELECT')
 THEN RAISE EXCEPTION 'BROADCAST_CONTENT_PUBLIC';END IF;
 IF has_function_privilege('anon',
 'public.saraf_original_broadcast_create(bigint,text,text)','EXECUTE') OR
 has_function_privilege('authenticated',
 'public.saraf_original_broadcast_claim(integer)','EXECUTE')
 THEN RAISE EXCEPTION 'PUBLIC_BROADCAST_RPC';END IF;
 RAISE NOTICE 'Original broadcast /stop privacy, one-time, idempotence PASSED';
END $$;
