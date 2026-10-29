-- Isolated PostgreSQL; all users, TX hashes and money are synthetic.
DO $$
DECLARE
  v_id bigint;
  v_result jsonb;
  v_forbidden boolean;
  v_proof jsonb;
BEGIN
  SELECT id INTO v_id FROM public.remittance_orders
    WHERE chat_id=101 AND status='transfer_submitted' LIMIT 1;
  IF v_id IS NULL THEN RAISE EXCEPTION 'No synthetic remittance to test'; END IF;

  -- A valid chain proof CANNOT by itself authorize money movement.
  UPDATE public.remittance_orders SET
    verification_status='verified',
    chain_confirmations=15,
    chain_verified_at=now()-interval '1 minute',
    chain_verified_amount=crypto_amount,
    chain_verified_asset=asset,
    chain_verified_network=network,
    chain_block_number=1000,
    chain_verification_meta=jsonb_build_object('blockHash','0x'||repeat('f',64))
  WHERE id=v_id;
  v_forbidden:=false;
  BEGIN
    UPDATE public.remittance_orders SET status='payout_ready' WHERE id=v_id;
  EXCEPTION WHEN raise_exception THEN
    v_forbidden := SQLERRM='TWO_INDEPENDENT_APPROVALS_REQUIRED';
  END;
  IF NOT v_forbidden THEN RAISE EXCEPTION 'Dual-control bypass via verified TX'; END IF;

  INSERT INTO public.saraf_finance_operators(telegram_id,role,enabled)
    VALUES(9001,'finance_approver',true),(9002,'finance_approver',true),
      (9003,'finance_approver',false),(101,'finance_approver',true);

  v_forbidden:=false;
  BEGIN
    PERFORM public.saraf_approve_verified_payout(v_id,9003);
  EXCEPTION WHEN raise_exception THEN
    v_forbidden := SQLERRM='OPERATOR_NOT_AUTHORIZED';
  END;
  IF NOT v_forbidden THEN RAISE EXCEPTION 'Disabled operator approved money'; END IF;
  v_forbidden:=false;
  BEGIN
    PERFORM public.saraf_approve_verified_payout(v_id,101);
  EXCEPTION WHEN raise_exception THEN
    v_forbidden := SQLERRM='INDEPENDENT_CHAIN_PROOF_REQUIRED';
  END;
  IF NOT v_forbidden THEN RAISE EXCEPTION 'Sender self-approved their payout'; END IF;

  v_result:=public.saraf_approve_verified_payout(v_id,9001);
  IF (v_result->>'valid_approvals')::integer<>1
     OR (v_result->>'ready_for_review')::boolean THEN
    RAISE EXCEPTION 'First approval not counted correctly';
  END IF;
  v_result:=public.saraf_approve_verified_payout(v_id,9001);
  IF (v_result->>'valid_approvals')::integer<>1 THEN
    RAISE EXCEPTION 'Replay allowed one operator to vote twice';
  END IF;
  v_forbidden:=false;
  BEGIN
    UPDATE public.remittance_orders SET status='payout_ready' WHERE id=v_id;
  EXCEPTION WHEN raise_exception THEN
    v_forbidden := SQLERRM='TWO_INDEPENDENT_APPROVALS_REQUIRED';
  END;
  IF NOT v_forbidden THEN RAISE EXCEPTION 'One-operator payout readiness bypass'; END IF;

  v_result:=public.saraf_approve_verified_payout(v_id,9002);
  IF (v_result->>'valid_approvals')::integer<>2
     OR NOT (v_result->>'ready_for_review')::boolean THEN
    RAISE EXCEPTION 'Two independent approvals were not recognized';
  END IF;
  v_forbidden:=false;
  BEGIN
    PERFORM public.saraf_prepare_payout_after_dual_approval(v_id,101);
  EXCEPTION WHEN raise_exception THEN
    v_forbidden:=SQLERRM='OPERATOR_NOT_AUTHORIZED' OR SQLERRM='SELF_APPROVAL_FORBIDDEN';
  END;
  IF NOT v_forbidden THEN RAISE EXCEPTION 'Customer could queue own payout'; END IF;
  v_result:=public.saraf_prepare_payout_after_dual_approval(v_id,9002);
  IF v_result->>'status'<>'payout_ready'
    OR (v_result->>'funds_paid')::boolean THEN
    RAISE EXCEPTION 'Queue-only status is not safe';
  END IF;

  v_forbidden:=false;
  BEGIN
    UPDATE public.remittance_orders SET
      chain_verified_amount=chain_verified_amount+1 WHERE id=v_id;
  EXCEPTION WHEN raise_exception THEN
    v_forbidden := SQLERRM='PAYOUT_PROOF_IMMUTABLE';
  END;
  IF NOT v_forbidden THEN RAISE EXCEPTION 'Verified proof altered after approval'; END IF;

  v_forbidden:=false;
  BEGIN
    UPDATE public.remittance_orders SET status='completed' WHERE id=v_id;
  EXCEPTION WHEN raise_exception THEN
    v_forbidden := SQLERRM='PAYOUT_COMPLETION_INTEGRATION_REQUIRED';
  END;
  IF NOT v_forbidden THEN RAISE EXCEPTION 'Completed without bank/cash receipt'; END IF;

  IF has_function_privilege('anon',
    'public.saraf_prepare_payout_after_dual_approval(bigint,bigint)','EXECUTE') OR
     has_function_privilege('authenticated',
    'public.saraf_prepare_payout_after_dual_approval(bigint,bigint)','EXECUTE') OR
     has_function_privilege('anon',
    'public.saraf_approve_verified_payout(bigint,bigint)','EXECUTE') OR
     has_function_privilege('authenticated',
    'public.saraf_approve_verified_payout(bigint,bigint)','EXECUTE') THEN
    RAISE EXCEPTION 'Public can approve customer payout'; END IF;
  RAISE NOTICE 'Dual-control payout safety checks passed';
END $$;
