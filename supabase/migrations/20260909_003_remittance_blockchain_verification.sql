alter table public.remittance_orders
  add column if not exists verification_status text not null default 'not_submitted',
  add column if not exists chain_confirmations integer not null default 0,
  add column if not exists chain_block_number bigint,
  add column if not exists chain_verified_amount numeric(38,18),
  add column if not exists chain_verified_asset text,
  add column if not exists chain_verified_network text,
  add column if not exists chain_verified_at timestamptz,
  add column if not exists chain_last_checked_at timestamptz,
  add column if not exists chain_verification_error text,
  add column if not exists chain_verification_meta jsonb not null default '{}'::jsonb;

alter table public.remittance_orders drop constraint if exists remittance_orders_verification_status_check;
alter table public.remittance_orders add constraint remittance_orders_verification_status_check
  check (verification_status in ('not_submitted','pending','confirming','verified','mismatch','failed','unsupported'));

alter table public.remittance_orders drop constraint if exists remittance_orders_chain_confirmations_check;
alter table public.remittance_orders add constraint remittance_orders_chain_confirmations_check
  check (chain_confirmations >= 0);

create index if not exists remittance_orders_chain_watch_idx
  on public.remittance_orders (status, verification_status, chain_last_checked_at)
  where status = 'transfer_submitted';

update public.remittance_orders
set verification_status = case when tx_hash is null then 'not_submitted' else 'pending' end
where verification_status = 'not_submitted';
