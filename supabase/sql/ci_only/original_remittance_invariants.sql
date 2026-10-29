-- Original main:services/remittance_service.py in isolated synthetic DB.
DO $$
DECLARE
 r jsonb; v_id bigint; blocked boolean;
BEGIN
 r:=public.saraf_original_create_remittance(
 101,'remit-example-key-001','USDT','ERC20',
 75,65.25,4893.8,0,0,4893.8,
 '0x1111111111111111111111111111111111111111',
 'Synthetic Sender','Afghanistan','0700000001',
 'Synthetic Beneficiary','0790000000','Kabul','Kabul','Example address',
 'remittances/101/synthetic_id.jpg',1,75
 );
 v_id:=(r->>'id')::bigint;
 IF (r->>'order_code')<>'REM-000001' OR
    (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_REMITTANCE_RESPONSE_FAILED';
 END IF;
 IF (SELECT pickup_code IS NOT NULL AND length(pickup_code)=6
   FROM public.remittance_orders WHERE id=v_id) IS DISTINCT FROM true THEN
  RAISE EXCEPTION 'ORIGINAL_PICKUP_CODE_MISSING_IN_DATABASE';
 END IF;
 IF r ? 'pickup_code' THEN
   RAISE EXCEPTION 'PICKUP_CODE_LEAKED_BEFORE_PAYOUT';
 END IF;
 r:=public.saraf_original_create_remittance(
 101,'remit-example-key-001','USDT','ERC20',
 75,65.25,4893.8,0,0,4893.8,
 '0x1111111111111111111111111111111111111111',
 'Synthetic Sender','Afghanistan','0700000001',
 'Synthetic Beneficiary','0790000000','Kabul','Kabul','Example address',
 'remittances/101/synthetic_id.jpg',1,75
 );
 IF (r->>'id')::bigint<>v_id OR NOT (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_REMITTANCE_RETRY_NOT_IDEMPOTENT';
 END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_create_remittance(
   101,'remit-example-key-001','USDC','ERC20',75,65.25,4893.8,0,0,4893.8,
   '0x1111111111111111111111111111111111111111',
   'Synthetic Sender','Afghanistan','0700000001',
   'Synthetic Beneficiary','0790000000','Kabul','Kabul','Example address',
   'remittances/101/synthetic_id.jpg',1,75);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='REMITTANCE_IDEMPOTENCY_CONFLICT';
 END;
 IF NOT blocked THEN RAISE EXCEPTION 'IDEMPOTENCY_REUSED_FOR_DIFFERENT_ASSET';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_claim_remittance_tx(
   202,v_id,'hash-that-user-does-not-own');
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='REMITTANCE_NOT_FOUND';
 END;
 IF NOT blocked THEN RAISE EXCEPTION 'TX_HASH_OWNER_IS_NOT_ENFORCED';END IF;
 r:=public.saraf_original_claim_remittance_tx(
  101,v_id,'0x123456789012345678901234567890abcdef');
 IF r->>'status'<>'transfer_submitted' OR
   r->>'verification_status'<>'pending' OR r ? 'pickup_code' THEN
  RAISE EXCEPTION 'ORIGINAL_TX_STATE_MACHINE_MISMATCH: %',r;
 END IF;
 IF (SELECT status FROM public.remittance_orders WHERE id=v_id)
  <>'transfer_submitted' THEN
  RAISE EXCEPTION 'ORIGINAL_TX_NOT_SAVED';
 END IF;
 IF (SELECT count(*) FROM public.remittance_status_history WHERE order_id=v_id)<>2 THEN
  RAISE EXCEPTION 'ORIGINAL_STATUS_HISTORY_MISSING';
 END IF;
 IF (SELECT count(*) FROM public.audit_log WHERE entity='remittance')<>2 THEN
  RAISE EXCEPTION 'ORIGINAL_REMITTANCE_AUDIT_MISSING';
 END IF;
 IF has_function_privilege('anon',
  'public.saraf_original_claim_remittance_tx(bigint,bigint,text)','EXECUTE')
  OR has_function_privilege('authenticated',
  'public.saraf_original_claim_remittance_tx(bigint,bigint,text)','EXECUTE')
 THEN RAISE EXCEPTION 'PUBLIC_TX_RPC_AVAILABLE';END IF;
 RAISE NOTICE 'Original remittance persistence and TX invariants passed';
END $$;
