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
-- Trust Profile کاربران + سیستم KYC + Risk Engine + کارت دیجیتال
-- =============================================================================

-- پروفایل احراز هویت و اعتبار هر کاربر — یک رکورد به‌ازای هر chat_id، فقط یک‌بار
-- در اولین سفارش پر می‌شود.
create table if not exists user_profiles (
  chat_id bigint primary key,
  first_name text,
  last_name text,
  phone text,
  payment_info text,
  id_document_path text,          -- مسیر داخل باکت خصوصی (نه لینک عمومی)
  selfie_path text,                -- مسیر داخل باکت خصوصی
  kyc_status text not null default 'pending'
    check (kyc_status in ('pending', 'verified', 'trusted', 'restricted')),
  trust_score int not null default 0,
  total_orders int not null default 0,
  successful_orders int not null default 0,
  cancelled_orders int not null default 0,
  current_success_streak int not null default 0,
  total_volume_usdt numeric not null default 0,
  payment_info_change_count int not null default 0,
  joined_at timestamptz not null default now(),
  last_order_at timestamptz,
  verified_by bigint,
  verified_at timestamptz,
  restricted_reason text
);

-- فیلدهای ریسک و کارت روی هر سفارش
alter table usdt_orders add column if not exists risk_level text default 'low'
  check (risk_level in ('low', 'medium', 'high'));
alter table usdt_orders add column if not exists risk_reasons text;
alter table usdt_orders add column if not exists card_image_path text;

-- =============================================================================
-- راه‌اندازی باکت‌های Storage — همهٔ این‌ها را از داشبورد Supabase انجام بده
-- (Supabase Dashboard → Storage → New bucket)؛ ساخت باکت از طریق SQL ساده
-- امکان‌پذیر نیست:
--
-- ۱) باکت «usdt-receipts» → Public (رسیدهای بانکی/تراکنش از مینی‌اپ)
-- ۲) باکت «usdt-kyc-docs» → Private (عکس تذکره و سلفی — حتماً خصوصی بماند)
-- ۳) باکت «usdt-cards»    → Private (کارت‌های دیجیتال — شامل عکس و اطلاعات شخصی)
--
-- اگر خواستی نام باکت‌ها را تغییر بدهی، متغیرهای محیطی متناظر را هم در Railway
-- به همان نام تنظیم کن: USDT_RECEIPTS_BUCKET, USDT_KYC_DOCS_BUCKET, USDT_CARDS_BUCKET
-- =============================================================================
