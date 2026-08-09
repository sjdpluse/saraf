-- =============================================================================
-- Saraf — به‌روزرسانی پایگاه داده برای قابلیت‌های جدید تتر (شمارهٔ تماس، منبع
-- سفارش، آپلود رسید از طریق مینی‌اپ)
-- این اسکریپت را در Supabase Dashboard → SQL Editor اجرا کن.
-- =============================================================================

-- اگر جدول usdt_orders هنوز وجود ندارد، این نسخهٔ کامل را اجرا کن:
create table if not exists usdt_orders (
  id bigint generated always as identity primary key,
  chat_id bigint not null,
  username text,
  full_name text,
  phone text,
  order_type text not null check (order_type in ('buy', 'sell')),
  usdt_amount numeric not null,
  usd_rate numeric not null,
  fee_percent numeric,
  total_afn numeric not null,
  total_usd numeric not null,
  payment_method text,
  receive_method text,
  network text,
  wallet_address text,
  exchange_name text,
  tx_proof text,
  receipt_file_id text,
  bank_info text,
  source text default 'bot',  -- 'bot' یا 'miniapp'
  status text not null default 'pending' check (status in ('pending', 'confirmed', 'completed', 'cancelled')),
  confirmed_at timestamptz,
  completed_at timestamptz,
  cancelled_at timestamptz,
  rating smallint check (rating between 1 and 5),
  rating_comment text,
  rated_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_usdt_orders_chat_id on usdt_orders (chat_id);
create index if not exists idx_usdt_orders_status on usdt_orders (status);

-- اگر جدول از قبل وجود دارد (نصب‌های قبلی)، فقط ستون‌های جدید را اضافه کن:
alter table usdt_orders add column if not exists phone text;
alter table usdt_orders add column if not exists source text default 'bot';

-- =============================================================================
-- ستون‌های جدید برای Timeline واقعی وضعیت سفارش و سیستم امتیازدهی
-- =============================================================================
alter table usdt_orders add column if not exists confirmed_at timestamptz;
alter table usdt_orders add column if not exists completed_at timestamptz;
alter table usdt_orders add column if not exists cancelled_at timestamptz;
alter table usdt_orders add column if not exists rating smallint check (rating between 1 and 5);
alter table usdt_orders add column if not exists rating_comment text;
alter table usdt_orders add column if not exists rated_at timestamptz;

create index if not exists idx_usdt_orders_completed_at on usdt_orders (completed_at) where completed_at is not null;

-- =============================================================================
-- راه‌اندازی Supabase Storage برای رسیدهای مینی‌اپ (این بخش را باید از داشبورد
-- Supabase انجام دهی، چون ساخت باکت از طریق SQL ساده امکان‌پذیر نیست):
--
-- ۱) به Supabase Dashboard → Storage بروید.
-- ۲) یک باکت جدید با نام دقیق «usdt-receipts» بسازید.
-- ۳) گزینهٔ «Public bucket» را فعال کنید (چون لینک رسید مستقیماً به ادمین
--    نمایش داده می‌شود و نیازی به احراز هویت جداگانه برای دیدن آن نیست).
-- ۴) اگر خواستید نام باکت را تغییر دهید، متغیر محیطی USDT_RECEIPTS_BUCKET را
--    هم در Railway به همان نام تنظیم کنید.
-- =============================================================================
