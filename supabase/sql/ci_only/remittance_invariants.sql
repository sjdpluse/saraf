-- All remittance payments in this test are SIMULATED in ephemeral CI PostgreSQL.
DO $$
DECLARE
 q jsonb;
 rem jsonb;
 same jsonb;
 id bigint;
 qid bigint;
 blocked boolean;
BEGIN
 INSERT INTO public.saraf_finance_wallets(
   asset,network,address,verified_by,enabled)
 VALUES('USDT','ERC20','0x2222222222222222222222222222222222222222',99001,true);
 q:=public.saraf_issue_remittance_quote(101,'USDT','ERC20',75);
 qid:=(q->>'quote_id')::bigint;
 IF (q->>'deposit_wallet')<>'0x2222222222222222222222222222222222222222'
    OR (q->>'payout_afn')::numeric<>4893.8 THEN
   RAISE EXCEPTION 'Wrong remittance rate, wallet or payout %',q;
 END IF;
 rem:=public.saraf_submit_remittance_atomic(
   101,qid,'remittance-idem-aaa-0001',
   '{"sender_name":"Alpha Customer","sender_country":"AF",
   "beneficiary_name":"Sample Beneficiary","beneficiary_phone":"0700000000",
   "beneficiary_province":"Kabul","beneficiary_city":"Kabul",
   "beneficiary_address":"CI only test street"}'::jsonb);
 v_remittance_id:=(rem->>'id')::bigint;
 IF id IS NULL OR rem->>'status'<>'awaiting_transfer' THEN
   RAISE EXCEPTION 'Remittance not created';
 END IF;
 same:=public.saraf_submit_remittance_atomic(
   101,qid,'remittance-idem-aaa-0001',
   '{"sender_name":"Alpha Customer","sender_country":"AF",
   "beneficiary_name":"Sample Beneficiary","beneficiary_phone":"0700000000",
   "beneficiary_province":"Kabul","beneficiary_city":"Kabul",
   "beneficiary_address":"CI only test street"}'::jsonb);
 IF same->>'duplicate'<>'true' OR (same->>'id')::bigint<>v_remittance_id THEN
   RAISE EXCEPTION 'Duplicate remittance not idempotent';
 END IF;
 blocked:=false;
 BEGIN
   PERFORM public.saraf_submit_remittance_atomic(
     101,qid,'remittance-idem-aaa-0002',
     '{"sender_name":"Alpha Customer","sender_country":"AF",
     "beneficiary_name":"Sample Beneficiary","beneficiary_phone":"0700000000",
     "beneficiary_province":"Kabul","beneficiary_city":"Kabul",
     "beneficiary_address":"CI only test street"}'::jsonb);
 EXCEPTION WHEN raise_exception THEN
   blocked:=SQLERRM='REMITTANCE_QUOTE_INVALID';
 END;
 IF NOT blocked THEN RAISE EXCEPTION 'Double-spent remittance quote';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_submit_remittance_atomic(
    102,qid,'remittance-idem-aaa-0003',
    '{"sender_name":"Other Person","sender_country":"AF",
    "beneficiary_name":"Sample Beneficiary","beneficiary_phone":"0700000000",
    "beneficiary_province":"Kabul","beneficiary_city":"Kabul",
    "beneficiary_address":"CI only test street"}'::jsonb);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='REMITTANCE_QUOTE_INVALID';
 END;
 IF NOT blocked THEN RAISE EXCEPTION 'Remittance quote theft allowed';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_claim_remittance_tx(102,v_remittance_id,'0x'||repeat('a',64));
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='REMITTANCE_NOT_FOUND';
 END;
 IF NOT blocked THEN RAISE EXCEPTION 'Wrong-user TX claim allowed';END IF;
 rem:=public.saraf_claim_remittance_tx(101,v_remittance_id,'0x'||repeat('a',64));
 IF rem->>'status'<>'transfer_submitted'
   OR rem->>'verification_status'<>'pending' THEN
   RAISE EXCEPTION 'TX claim falsely marked verified';
 END IF;
 same:=public.saraf_claim_remittance_tx(101,v_remittance_id,'0x'||repeat('a',64));
 IF same->>'duplicate'<>'true' THEN RAISE EXCEPTION 'Tx retry not idempotent';END IF;
 blocked:=false;
 BEGIN
   UPDATE public.remittance_orders SET status='payout_ready' WHERE id=v_remittance_id;
 EXCEPTION WHEN raise_exception THEN
   blocked:=SQLERRM='CHAIN_PROOF_REQUIRED_FOR_PAYOUT';
 END;
 IF NOT blocked THEN RAISE EXCEPTION 'Unverified remittance payout was allowed';END IF;
 IF has_function_privilege('anon',
   'public.saraf_claim_remittance_tx(bigint,bigint,text)','EXECUTE') THEN
   RAISE EXCEPTION 'Anon can claim remittance hash';END IF;
 RAISE NOTICE 'Saraf remittance invariants passed';
END $$;
