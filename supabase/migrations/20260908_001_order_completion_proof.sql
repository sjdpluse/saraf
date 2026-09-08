BEGIN;

-- Admin must attach transaction evidence before an order can be completed.
-- Text is used for Tx Hash / Transaction Details; Telegram file metadata is
-- retained for audit when the admin supplies an image/document instead.
ALTER TABLE public.usdt_orders
  ADD COLUMN IF NOT EXISTS completion_tx_details text,
  ADD COLUMN IF NOT EXISTS completion_proof_file_id text,
  ADD COLUMN IF NOT EXISTS completion_proof_file_type text,
  ADD COLUMN IF NOT EXISTS completion_proof_file_name text;

COMMIT;
