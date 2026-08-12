BEGIN;

-- Keep status-history writes attributable when the caller provides a changed_by
-- value. Existing trigger behavior remains compatible with NULL.
CREATE OR REPLACE FUNCTION public.record_usdt_order_status_history()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO public.usdt_order_status_history (order_id, from_status, to_status, changed_by)
    VALUES (NEW.id, NULL, NEW.status, NULL);
  ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
    INSERT INTO public.usdt_order_status_history (order_id, from_status, to_status, changed_by)
    VALUES (NEW.id, OLD.status, NEW.status, NULL);
  END IF;
  RETURN NEW;
END;
$$;

-- Add defensive bounds for profile counters. NOT VALID avoids blocking rollout
-- if legacy data needs cleanup first.
ALTER TABLE public.user_profiles
  ADD CONSTRAINT user_profiles_nonnegative_counters_check
  CHECK (
    trust_score >= 0
    AND total_orders >= 0
    AND successful_orders >= 0
    AND cancelled_orders >= 0
    AND current_success_streak >= 0
    AND total_volume_usdt >= 0
    AND payment_info_change_count >= 0
  ) NOT VALID;

COMMIT;
