-- International remittance V1
-- Sender is an authenticated Telegram user; beneficiary is stored independently.

create table if not exists public.remittance_orders (
    id bigserial primary key,
    chat_id bigint not null,
    idempotency_key text not null,

    sender_country text not null,
    sender_name text,
    sender_phone text,

    beneficiary_full_name text not null,
    beneficiary_phone text not null,
    beneficiary_province text not null,
    beneficiary_city text not null,
    beneficiary_address text,
    relationship text not null,
    purpose text not null,

    asset text not null check (asset in ('USDT', 'USDC')),
    network text not null,
    crypto_amount numeric(20,8) not null check (crypto_amount > 0),
    usd_rate numeric(20,6) not null check (usd_rate > 0),
    gross_afn numeric(20,2) not null check (gross_afn >= 0),
    fee_percent numeric(10,4) not null default 0 check (fee_percent >= 0),
    fee_afn numeric(20,2) not null default 0 check (fee_afn >= 0),
    payout_afn numeric(20,2) not null check (payout_afn >= 0),

    deposit_wallet text not null,
    tx_hash text,
    pickup_code text,

    status text not null default 'awaiting_transfer' check (
        status in (
            'awaiting_transfer',
            'transfer_submitted',
            'payout_ready',
            'completed',
            'cancelled',
            'on_hold'
        )
    ),
    admin_note text,
    crypto_confirmed_by bigint,
    crypto_confirmed_at timestamptz,
    paid_by bigint,
    paid_at timestamptz,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (chat_id, idempotency_key)
);

create index if not exists remittance_orders_chat_created_idx
    on public.remittance_orders (chat_id, created_at desc);
create index if not exists remittance_orders_status_created_idx
    on public.remittance_orders (status, created_at desc);
create unique index if not exists remittance_orders_tx_hash_unique_idx
    on public.remittance_orders (lower(tx_hash))
    where tx_hash is not null;

create table if not exists public.remittance_status_history (
    id bigserial primary key,
    order_id bigint not null references public.remittance_orders(id) on delete cascade,
    from_status text,
    to_status text not null,
    changed_by bigint,
    note text,
    created_at timestamptz not null default now()
);

create index if not exists remittance_status_history_order_idx
    on public.remittance_status_history (order_id, created_at asc);

create or replace function public.set_remittance_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_remittance_orders_updated_at on public.remittance_orders;
create trigger trg_remittance_orders_updated_at
before update on public.remittance_orders
for each row execute function public.set_remittance_updated_at();

alter table public.remittance_orders enable row level security;
alter table public.remittance_status_history enable row level security;

-- No anon/authenticated policies are intentionally created. The application backend
-- accesses these tables with the server-side Supabase key; clients never query them directly.
