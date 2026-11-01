-- Canonical Saraf order card delivery outbox. The order and all financial
-- values remain in the ORIGINAL usdt_orders table; there is no shadow ledger.
-- Sending states: claiming a recipient BEFORE an external Telegram call prevents
-- simultaneous or blindly repeated sends if the network response is uncertain.
create table if not exists public.saraf_original_order_card_deliveries (
  order_id bigint not null references public.usdt_orders(id) on delete cascade,
  chat_id bigint not null check (chat_id > 0),
  recipient text not null check (recipient in ('customer','admin')),
  state text not null default 'sending'
    check (state in ('sending','sent','failed','uncertain')),
  attempt_count integer not null default 1 check (attempt_count between 1 and 5),
  telegram_message_id bigint,
  sent_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (order_id,recipient,chat_id)
);
alter table public.saraf_original_order_card_deliveries enable row level security;
revoke all on public.saraf_original_order_card_deliveries from public, anon, authenticated;
grant select, insert, update on public.saraf_original_order_card_deliveries to service_role;
comment on table public.saraf_original_order_card_deliveries is
 'Service-role only, order-scoped idempotent Telegram photo delivery. No financial writes.';
