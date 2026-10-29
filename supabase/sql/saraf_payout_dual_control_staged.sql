-- STAGED: dual-control of payouts on canonical Supabase; NOT live-deployed.
-- This migration depends on saraf_atomic_finance_staged.sql and
-- saraf_atomic_remittance_staged.sql. No legacy money rows are modified.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='30s';

CREATE TABLE IF NOT EXISTS public.saraf_finance_operators(
  telegram_id bigint PRIMARY KEY CHECK(telegram_id>0),
  role text NOT NULL CHECK(role='finance_approver'),
  enabled boolean NOT NULL DEFAULT false,
  enrolled_at timestamptz NOT NULL DEFAULT now(),
  enrolled_by bigint CHECK(enrolled_by>0)
);
ALTER TABLE public.saraf_finance_operators ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_finance_operators FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE ON public.saraf_finance_operators TO service_role;

CREATE TABLE IF NOT EXISTS public.saraf_payout_approvals(
  remittance_id bigint NOT NULL REFERENCES public.remittance_orders(id),
  operator_id bigint NOT NULL REFERENCES public.saraf_finance_operators(telegram_id),
  proof jsonb NOT NULL,
  approved_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(remittance_id,operator_id)
);
ALTER TABLE public.saraf_payout_approvals ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.saraf_payout_approvals FROM PUBLIC,anon,authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.saraf_payout_approvals TO service_role;

-- Approvals become unusable when the TX, chain, received amount or chain proof
-- changes, even when an older approval row is not proactively deleted.
CREATE OR REPLACE FUNCTION public.saraf_chain_proof_snapshot(
 r public.remittance_orders
) RETURNS jsonb LANGUAGE sql IMMUTABLE SECURITY INVOKER SET search_path=''
AS $$
  SELECT jsonb_build_object(
    'tx_hash',lower(r.tx_hash),'asset',r.asset,'network',r.network,
    'deposit_wallet',lower(r.deposit_wallet),
    'crypto_amount',r.crypto_amount,'chain_verified_amount',r.chain_verified_amount,
    'verified_at',r.chain_verified_at,'chain_verified_asset',r.chain_verified_asset,
    'chain_verified_network',r.chain_verified_network,
    'chain_block_number',r.chain_block_number,
    'chain_block_hash',r.chain_verification_meta->>'blockHash');
$$;

CREATE OR REPLACE FUNCTION public.saraf_approve_verified_payout(
  p_remittance_id bigint,p_operator_id bigint
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
 r public.remittance_orders%ROWTYPE;
 n integer;
BEGIN
 IF p_remittance_id IS NULL OR p_remittance_id<=0 OR p_operator_id IS NULL
   OR p_operator_id<=0 THEN
   RAISE EXCEPTION 'INVALID_APPROVAL_INPUT' USING ERRCODE='P0001';
 END IF;
 SELECT * INTO r FROM public.remittance_orders
   WHERE id=p_remittance_id FOR UPDATE;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'REMITTANCE_NOT_FOUND' USING ERRCODE='P0001';
 END IF;
 IF r.chat_id=p_operator_id OR r.status<>'transfer_submitted'
   OR r.verification_status<>'verified'
   OR r.chain_confirmations<12
   OR r.chain_verified_at IS NULL OR r.tx_hash IS NULL
   OR r.chain_verified_asset IS DISTINCT FROM r.asset
   OR r.chain_verified_network IS DISTINCT FROM r.network
   OR r.chain_verified_amount IS NULL OR r.chain_verified_amount < r.crypto_amount
   OR r.chain_block_number IS NULL
   OR coalesce(r.chain_verification_meta->>'blockHash','')=''
   THEN
   RAISE EXCEPTION 'INDEPENDENT_CHAIN_PROOF_REQUIRED' USING ERRCODE='P0001';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM public.saraf_finance_operators
   WHERE telegram_id=p_operator_id AND role='finance_approver' AND enabled) THEN
   RAISE EXCEPTION 'OPERATOR_NOT_AUTHORIZED' USING ERRCODE='P0001';
 END IF;
 INSERT INTO public.saraf_payout_approvals(remittance_id,operator_id,proof)
 VALUES(p_remittance_id,p_operator_id,public.saraf_chain_proof_snapshot(r))
 ON CONFLICT(remittance_id,operator_id) DO UPDATE
   SET proof=excluded.proof,approved_at=now();
 INSERT INTO public.saraf_finance_audit(event,actor_id,info)
 VALUES('remittance_payout_reviewed',p_operator_id,
   jsonb_build_object('remittance_id',p_remittance_id));
 SELECT count(*) INTO n FROM public.saraf_payout_approvals a
   JOIN public.saraf_finance_operators o ON o.telegram_id=a.operator_id
   WHERE a.remittance_id=p_remittance_id AND o.enabled
     AND a.approved_at>=now()-interval '24 hours'
     AND a.approved_at >= r.chain_verified_at
     AND a.proof=public.saraf_chain_proof_snapshot(r);
 RETURN jsonb_build_object('remittance_id',p_remittance_id,
   'valid_approvals',n,'ready_for_review',n>=2,
   'funds_paid',false,'status',r.status);
END;
$$;

CREATE OR REPLACE FUNCTION public.saraf_payout_dual_control_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=''
AS $$
DECLARE
 n integer;
BEGIN
 -- A 'completed' status is a claim of physical bank/cash disbursement.
 -- No integrated payout provider can attest this yet, so it remains forbidden.
 IF NEW.status='completed' AND NEW.status IS DISTINCT FROM OLD.status THEN
   RAISE EXCEPTION 'PAYOUT_COMPLETION_INTEGRATION_REQUIRED' USING ERRCODE='P0001';
 END IF;
 IF OLD.status IN ('payout_ready','completed')
    AND NEW.status=OLD.status
    AND public.saraf_chain_proof_snapshot(NEW)
        IS DISTINCT FROM public.saraf_chain_proof_snapshot(OLD) THEN
   RAISE EXCEPTION 'PAYOUT_PROOF_IMMUTABLE' USING ERRCODE='P0001';
 END IF;
 IF NEW.status='payout_ready' AND OLD.status IS DISTINCT FROM NEW.status THEN
   IF OLD.status<>'transfer_submitted' OR
     NEW.verification_status<>'verified' OR NEW.chain_confirmations<12 OR
     NEW.chain_verified_at IS NULL OR NEW.chain_verified_asset IS DISTINCT FROM NEW.asset OR
     NEW.chain_verified_network IS DISTINCT FROM NEW.network OR
     NEW.chain_verified_amount IS NULL OR NEW.chain_verified_amount < NEW.crypto_amount OR
     NEW.tx_hash IS NULL OR NEW.chain_block_number IS NULL OR
     coalesce(NEW.chain_verification_meta->>'blockHash','')='' THEN
     RAISE EXCEPTION 'INDEPENDENT_CHAIN_PROOF_REQUIRED' USING ERRCODE='P0001';
   END IF;
   SELECT count(*) INTO n FROM public.saraf_payout_approvals a
    JOIN public.saraf_finance_operators o ON a.operator_id=o.telegram_id
    WHERE a.remittance_id=NEW.id AND o.enabled
      AND a.approved_at>=now()-interval '24 hours'
      AND a.approved_at>=NEW.chain_verified_at
      AND a.proof=public.saraf_chain_proof_snapshot(NEW);
   IF n<2 THEN
     RAISE EXCEPTION 'TWO_INDEPENDENT_APPROVALS_REQUIRED' USING ERRCODE='P0001';
   END IF;
 END IF;
 RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS saraf_dual_control_payout ON public.remittance_orders;
CREATE TRIGGER saraf_dual_control_payout
 BEFORE UPDATE OF status,tx_hash,asset,network,deposit_wallet,
   crypto_amount,verification_status,chain_confirmations,chain_verified_at,
   chain_verified_asset,chain_verified_network,chain_verified_amount,
   chain_block_number,chain_verification_meta
 ON public.remittance_orders
 FOR EACH ROW EXECUTE FUNCTION public.saraf_payout_dual_control_guard();

-- Only a *separate* trusted operator Edge Function may call these RPCs with a
-- server-only service key after proving signed Telegram identity and ACL.
REVOKE ALL ON FUNCTION public.saraf_approve_verified_payout(bigint,bigint)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_approve_verified_payout(bigint,bigint)
 TO service_role;
REVOKE ALL ON FUNCTION public.saraf_chain_proof_snapshot(public.remittance_orders)
 FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.saraf_chain_proof_snapshot(public.remittance_orders)
 TO service_role;
COMMIT;
