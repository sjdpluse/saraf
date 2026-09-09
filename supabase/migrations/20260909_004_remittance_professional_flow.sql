-- Professional staged remittance flow.
-- Keep legacy relationship/purpose columns for old rows, but new orders no longer use them.

alter table public.remittance_orders
  add column if not exists beneficiary_id_document_path text;

alter table public.remittance_orders
  alter column relationship drop not null,
  alter column purpose drop not null;

create index if not exists remittance_orders_beneficiary_phone_idx
  on public.remittance_orders (beneficiary_phone);
