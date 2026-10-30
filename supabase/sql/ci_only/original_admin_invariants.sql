-- Synthetic checks for original main:handlers/admin.py.
-- Must execute ONLY AFTER original_usdt_order_invariants.sql.
DO $$
DECLARE
 r jsonb; v_id bigint; blocked boolean; audit_before integer; audit_after integer;
BEGIN
 SELECT id INTO v_id FROM public.usdt_orders ORDER BY id LIMIT 1;
 IF v_id IS NULL THEN RAISE EXCEPTION 'NO_SYNTHETIC_ORDER_FOR_ADMIN_TEST';END IF;
 SELECT count(*) INTO audit_before FROM public.audit_log;
 r:=public.saraf_original_admin_confirm(997,v_id);
 IF r->>'status'<>'confirmed' OR (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_ADMIN_CONFIRM_FAILED: %',r;END IF;
 IF (SELECT status FROM public.usdt_orders WHERE id=v_id)<>'confirmed'
 OR (SELECT confirmed_at FROM public.usdt_orders WHERE id=v_id) IS NULL
 THEN RAISE EXCEPTION 'ORIGINAL_CONFIRM_NOT_PERSISTED'; END IF;
 IF (SELECT count(*) FROM public.usdt_order_status_history WHERE order_id=v_id
   AND to_status='confirmed' AND changed_by=997)<>1 THEN
   RAISE EXCEPTION 'ORIGINAL_CONFIRM_MISSING_ATTRIBUTION';END IF;
 r:=public.saraf_original_admin_confirm(997,v_id);
 IF NOT (r->>'duplicate')::boolean THEN
   RAISE EXCEPTION 'ORIGINAL_ADMIN_CONFIRM_RETRY_NOT_IDEMPOTENT';END IF;
 SELECT count(*) INTO audit_after FROM public.audit_log;
 IF audit_after<>audit_before+1 THEN
   RAISE EXCEPTION 'CONFIRMATION_AUDIT_DUPLICATED';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_confirm(997,999999999);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='ORDER_NOT_FOUND';END;
 IF NOT blocked THEN RAISE EXCEPTION 'INVALID_ORDER_CONFIRMED';END IF;

 INSERT INTO public.usdt_orders(chat_id,order_type,asset,usdt_amount,usd_rate,
  total_afn,total_usd,status)
 VALUES(101,'sell','USDT',20,65,1300,20,'completed') RETURNING id INTO v_id;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_confirm(997,v_id);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='INVALID_ORDER_TRANSITION';END;
 IF NOT blocked THEN RAISE EXCEPTION 'COMPLETED_ORDER_RECONFIRMED';END IF;

 r:=public.saraf_original_admin_set_spread(997,'usd',0.8);
 IF r->>'currency'<>'usd' OR (r->>'spread_percent')::numeric<>0.8 THEN
   RAISE EXCEPTION 'ORIGINAL_SPREAD_SET_FAILED';END IF;
 IF (SELECT spread_percent FROM public.spread_settings WHERE currency='usd')<>0.8
 THEN RAISE EXCEPTION 'ORIGINAL_SPREAD_NOT_SAVED';END IF;
 r:=public.saraf_original_admin_set_spread(997,'usd',0.8);
 IF NOT (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_SPREAD_RETRY_NOT_IDEMPOTENT';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_set_spread(997,'usd',22);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='INVALID_SPREAD_INPUT';END;
 IF NOT blocked THEN RAISE EXCEPTION 'UNSAFE_SPREAD_ACCEPTED';END IF;
 IF has_function_privilege('anon','public.saraf_original_admin_confirm(bigint,bigint)','EXECUTE')
 OR has_function_privilege('authenticated',
   'public.saraf_original_admin_confirm(bigint,bigint)','EXECUTE')
 OR has_function_privilege('anon',
   'public.saraf_original_admin_set_spread(bigint,text,numeric)','EXECUTE')
 THEN RAISE EXCEPTION 'ADMIN_RPC_PUBLIC';END IF;
 RAISE NOTICE 'Original Saraf admin command invariants PASSED';
END $$;


-- Original admin_bot.py KYC review transitions: isolated/synthetic ONLY.
DO $$
DECLARE
 r jsonb; blocked boolean;
BEGIN
 INSERT INTO public.user_profiles(
  chat_id,first_name,last_name,phone,kyc_status,id_document_path,selfie_path)
 VALUES
  (303,'Synthetic','KycApprove','0790000303','pending','303_id.jpg','303_selfie.jpg'),
  (404,'Synthetic','KycReject','0790000404','pending','404_id.jpg','404_selfie.jpg');
 r:=public.saraf_original_admin_review_kyc(997,303,'verified');
 IF r->>'status'<>'verified' OR (r->>'duplicate')::boolean THEN
   RAISE EXCEPTION 'ORIGINAL_KYC_APPROVAL_FAILED';
 END IF;
 IF (SELECT verified_by=997 AND verified_at IS NOT NULL
      FROM public.user_profiles WHERE chat_id=303) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'ORIGINAL_KYC_VERIFIER_MISSING'; END IF;
 r:=public.saraf_original_admin_review_kyc(997,303,'verified');
 IF NOT (r->>'duplicate')::boolean THEN
   RAISE EXCEPTION 'ORIGINAL_KYC_IDEMPOTENCY_FAILED';
 END IF;
 IF (SELECT count(*) FROM public.audit_log
     WHERE entity='user_profile' AND entity_id='303')<>1
 THEN RAISE EXCEPTION 'ORIGINAL_KYC_DUPLICATE_AUDIT'; END IF;
 r:=public.saraf_original_admin_review_kyc(997,404,'restricted');
 IF r->>'status'<>'restricted' OR
   (SELECT restricted_reason FROM public.user_profiles
      WHERE chat_id=404)<>'رد شده در بررسی اولیهٔ هویت'
 THEN RAISE EXCEPTION 'ORIGINAL_KYC_REJECTION_FAILED'; END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_review_kyc(997,404,'verified');
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='KYC_NOT_PENDING'; END;
 IF NOT blocked THEN RAISE EXCEPTION 'REJECTED_KYC_REAPPROVED'; END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_review_kyc(997,202,'verified');
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='KYC_DOCUMENTS_MISSING'; END;
 IF NOT blocked THEN RAISE EXCEPTION 'KYC_APPROVED_WITHOUT_DOCUMENTS'; END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_review_kyc(997,303,'trusted');
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='INVALID_KYC_REVIEW'; END;
 IF NOT blocked THEN RAISE EXCEPTION 'UNEXPECTED_KYC_STATUS_ALLOWED'; END IF;
 IF has_function_privilege('anon',
  'public.saraf_original_admin_review_kyc(bigint,bigint,text)','EXECUTE')
  OR has_function_privilege('authenticated',
  'public.saraf_original_admin_review_kyc(bigint,bigint,text)','EXECUTE')
 THEN RAISE EXCEPTION 'ORIGINAL_KYC_ADMIN_RPC_PUBLIC'; END IF;
 RAISE NOTICE 'Original KYC admin approval/rejection invariants passed';
END $$;


-- ORIGINAL admin_bot.py admin_reject/admin_complete; evidence is mandatory.
DO $$
DECLARE
 r jsonb;
 v_complete bigint;
 v_reject bigint;
 blocked boolean;
 before_audit integer;
BEGIN
 SELECT id INTO v_complete FROM public.usdt_orders
 WHERE status='confirmed' ORDER BY id LIMIT 1;
 IF v_complete IS NULL THEN RAISE EXCEPTION 'NO_CONFIRMED_ORDER_FOR_COMPLETION';END IF;
 INSERT INTO public.usdt_orders(
  chat_id,order_type,asset,usdt_amount,usd_rate,total_afn,total_usd,status)
 VALUES(101,'sell','USDC',80,65,5200,80,'pending')
 RETURNING id INTO v_reject;
 -- Confirmed orders NEVER complete without actual Tx Hash / details.
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_finalize_order(997,v_complete,'complete','');
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='COMPLETION_PROOF_REQUIRED';END;
 IF NOT blocked THEN RAISE EXCEPTION 'ORIGINAL_COMPLETION_WITHOUT_PROOF';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_finalize_order(997,v_reject,'complete','0x12345');
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='INVALID_ORDER_TRANSITION';END;
 IF NOT blocked THEN RAISE EXCEPTION 'ORIGINAL_PENDING_ORDER_COMPLETED';END IF;
 SELECT count(*) INTO before_audit FROM public.audit_log;
 r:=public.saraf_original_admin_finalize_order(997,v_complete,'complete',
  '0xsynthetic_actual_proof_hash_for_transfer_12345');
 IF r->>'status'<>'completed' OR (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_ADMIN_COMPLETION_FAILED';
 END IF;
 IF (SELECT completed_at IS NOT NULL AND completion_tx_details=
     '0xsynthetic_actual_proof_hash_for_transfer_12345'
     FROM public.usdt_orders WHERE id=v_complete) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'ORIGINAL_COMPLETION_NOT_ATOMICALLY_SAVED'; END IF;
 r:=public.saraf_original_admin_finalize_order(997,v_complete,'complete',
  '0xsynthetic_actual_proof_hash_for_transfer_12345');
 IF NOT (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_COMPLETION_NOT_IDEMPOTENT';END IF;
 IF (SELECT successful_orders FROM public.user_profiles WHERE chat_id=101)<>1
 OR (SELECT current_success_streak FROM public.user_profiles WHERE chat_id=101)<>1
 OR (SELECT total_volume_usdt FROM public.user_profiles WHERE chat_id=101)<>100
 THEN RAISE EXCEPTION 'ORIGINAL_TRUST_PROFILE_SUCCESS_DIVERGED';END IF;
 r:=public.saraf_original_admin_finalize_order(997,v_reject,'reject',NULL);
 IF r->>'status'<>'cancelled' OR (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_REJECTION_FAILED';END IF;
 r:=public.saraf_original_admin_finalize_order(997,v_reject,'reject',NULL);
 IF NOT (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_REJECTION_NOT_IDEMPOTENT';END IF;
 IF (SELECT cancelled_orders FROM public.user_profiles WHERE chat_id=101)<>1
 OR (SELECT current_success_streak FROM public.user_profiles WHERE chat_id=101)<>0
 OR (SELECT total_orders FROM public.user_profiles WHERE chat_id=101)<>2
 OR (SELECT trust_score FROM public.user_profiles WHERE chat_id=101)<>42
 THEN RAISE EXCEPTION 'ORIGINAL_TRUST_PROFILE_REJECTION_DIVERGED';END IF;
 IF (SELECT count(*) FROM public.audit_log)<>before_audit+2
 THEN RAISE EXCEPTION 'ORIGINAL_ADMIN_AUDIT_COUNT_DIVERGED';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_finalize_order(997,v_reject,'complete',
   '0xsynthetic_actual_proof_hash_for_transfer_12345');
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='INVALID_ORDER_TRANSITION';END;
 IF NOT blocked THEN RAISE EXCEPTION 'ORIGINAL_CANCELLED_ORDER_COMPLETED';END IF;
 IF has_function_privilege('anon',
  'public.saraf_original_admin_finalize_order(bigint,bigint,text,text,text,text,text)','EXECUTE')
 OR has_function_privilege('authenticated',
  'public.saraf_original_admin_finalize_order(bigint,bigint,text,text,text,text,text)','EXECUTE')
 THEN RAISE EXCEPTION 'ORIGINAL_ADMIN_FINALIZE_RPC_PUBLIC';END IF;
 RAISE NOTICE 'Original admin rejection/completion/trust invariants passed';
END $$;


-- Original /remitpay pickup-code payout and ready/hold/cancel controls.
-- Synthetic database ONLY; never use real pickup codes or real money.
DO $$
DECLARE
 r jsonb; v_id bigint; v_code text; v_cancel_id bigint; blocked boolean;
BEGIN
 SELECT id,pickup_code INTO v_id,v_code
 FROM public.remittance_orders WHERE chat_id=101 AND status='transfer_submitted'
 ORDER BY id ASC LIMIT 1;
 IF v_id IS NULL OR length(v_code)<>6 THEN
  RAISE EXCEPTION 'NO_SYNTHETIC_REMITTANCE_FOR_ADMIN_TEST';
 END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_remittance(997,v_id,'pay',v_code);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='INVALID_REMITTANCE_TRANSITION';
 END;
 IF NOT blocked THEN RAISE EXCEPTION 'PAYOUT_COMPLETED_BEFORE_READY';END IF;
 r:=public.saraf_original_admin_remittance(997,v_id,'ready',NULL);
 IF r->>'status'<>'payout_ready' OR (r->>'pickup_code')<>v_code THEN
  RAISE EXCEPTION 'ORIGINAL_REMITTANCE_READY_FAILED';
 END IF;
 IF (SELECT crypto_confirmed_by=997 AND crypto_confirmed_at IS NOT NULL
    FROM public.remittance_orders WHERE id=v_id) IS DISTINCT FROM true THEN
  RAISE EXCEPTION 'ORIGINAL_CRYPTO_CONFIRMATION_NOT_ATTRIBUTED';
 END IF;
 r:=public.saraf_original_admin_remittance(997,v_id,'ready',NULL);
 IF NOT (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_REMITTANCE_READY_NOT_IDEMPOTENT';
 END IF;
 r:=public.saraf_original_admin_remittance(997,v_id,'hold',NULL);
 IF r->>'status'<>'on_hold' THEN RAISE EXCEPTION 'ORIGINAL_REMITTANCE_HOLD_FAILED';END IF;
 r:=public.saraf_original_admin_remittance(997,v_id,'ready',NULL);
 IF r->>'status'<>'payout_ready' THEN
  RAISE EXCEPTION 'ORIGINAL_REMITTANCE_RELEASE_HOLD_FAILED';
 END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_remittance(997,v_id,'pay','000000');
 EXCEPTION WHEN raise_exception THEN blocked:=SQLERRM='INVALID_PICKUP_CODE';END;
 IF NOT blocked OR
   (SELECT status FROM public.remittance_orders WHERE id=v_id)<>'payout_ready'
 THEN RAISE EXCEPTION 'WRONG_PICKUP_CODE_PAID';END IF;
 r:=public.saraf_original_admin_remittance(997,v_id,'pay',v_code);
 IF r->>'status'<>'completed' OR (r->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_REMITTANCE_PAY_FAILED';
 END IF;
 IF (SELECT paid_by=997 AND paid_at IS NOT NULL
  FROM public.remittance_orders WHERE id=v_id) IS DISTINCT FROM true THEN
  RAISE EXCEPTION 'ORIGINAL_REMITTANCE_PAYMENT_NOT_ATTRIBUTED';
 END IF;
 r:=public.saraf_original_admin_remittance(997,v_id,'pay',v_code);
 IF NOT (r->>'duplicate')::boolean THEN RAISE EXCEPTION 'DUPLICATE_REMITTANCE_PAID';END IF;
 blocked:=false;
 BEGIN
  PERFORM public.saraf_original_admin_remittance(997,v_id,'cancel',NULL);
 EXCEPTION WHEN raise_exception THEN
  blocked:=SQLERRM='INVALID_REMITTANCE_TRANSITION';END;
 IF NOT blocked THEN RAISE EXCEPTION 'COMPLETED_REMITTANCE_CANCELLED';END IF;
 INSERT INTO public.remittance_orders(
 chat_id,idempotency_key,sender_country,sender_name,beneficiary_full_name,
 beneficiary_phone,beneficiary_province,beneficiary_city,asset,network,
 crypto_amount,usd_rate,gross_afn,fee_percent,fee_afn,payout_afn,
 deposit_wallet,pickup_code,status)
 VALUES(101,'remit-admin-cancel-test','Afghanistan','Synthetic Sender',
 'Synthetic Beneficiary','0790000000','Kabul','Kabul','USDT','ERC20',
 40,65,2600,0,0,2600,'0x1111111111111111111111111111111111111111',
 '654321','transfer_submitted') RETURNING id INTO v_cancel_id;
 r:=public.saraf_original_admin_remittance(997,v_cancel_id,'cancel',NULL);
 IF r->>'status'<>'cancelled' THEN RAISE EXCEPTION 'ORIGINAL_REMITTANCE_CANCEL_FAILED';END IF;
 IF has_function_privilege('anon',
 'public.saraf_original_admin_remittance(bigint,bigint,text,text)','EXECUTE')
 OR has_function_privilege('authenticated',
 'public.saraf_original_admin_remittance(bigint,bigint,text,text)','EXECUTE')
 THEN RAISE EXCEPTION 'PUBLIC_REMITTANCE_PAYOUT_RPC';END IF;
 RAISE NOTICE 'Original remittance admin and six-digit pickup invariants passed';
END $$;


-- A REAL TELEGRAM FILE-ID can serve as completion proof without a text hash,
-- but missing/invalid proof MUST NEVER produce a paid order.
DO $$
DECLARE
 n bigint; v jsonb; denied boolean;
BEGIN
 INSERT INTO public.usdt_orders(
  chat_id,order_type,asset,usdt_amount,usd_rate,total_afn,total_usd,status)
 VALUES(101,'buy','USDT',5,70,350,5,'confirmed') RETURNING id INTO n;
 denied:=false;
 BEGIN
  PERFORM public.saraf_original_admin_finalize_order(
   997,n,'complete',NULL,NULL,NULL,NULL);
 EXCEPTION WHEN raise_exception THEN
  denied:=SQLERRM='COMPLETION_PROOF_REQUIRED';
 END;
 IF NOT denied THEN RAISE EXCEPTION 'ORIGINAL_MEDIA_EMPTY_PROOF_ACCEPTED';END IF;
 denied:=false;
 BEGIN
  PERFORM public.saraf_original_admin_finalize_order(
   997,n,'complete',NULL,'https://evil.example','photo','passport.png');
 EXCEPTION WHEN raise_exception THEN
  denied:=SQLERRM='COMPLETION_PROOF_REQUIRED';
 END;
 IF NOT denied THEN RAISE EXCEPTION 'ORIGINAL_MEDIA_INVALID_PROOF_ACCEPTED';END IF;
 v:=public.saraf_original_admin_finalize_order(
  997,n,'complete',NULL,'AgACAgQAAxkBsyntheticFile001','photo','transaction-details.jpg');
 IF v->>'status'<>'completed' OR
  (SELECT completion_proof_file_id='AgACAgQAAxkBsyntheticFile001' AND
          completion_proof_file_type='photo' AND
          completion_proof_file_name='transaction-details.jpg'
   FROM public.usdt_orders WHERE id=n) IS DISTINCT FROM true THEN
  RAISE EXCEPTION 'ORIGINAL_MEDIA_ONLY_PROOF_NOT_STORED';
 END IF;
 v:=public.saraf_original_admin_finalize_order(
  997,n,'complete',NULL,'AgACAgQAAxkBsyntheticFile001','photo','transaction-details.jpg');
 IF NOT (v->>'duplicate')::boolean THEN
  RAISE EXCEPTION 'ORIGINAL_MEDIA_FINALIZE_REPLAY_NOT_IDEMPOTENT';END IF;
 RAISE NOTICE 'Original Telegram completion media proof PG invariants passed';
END $$;
