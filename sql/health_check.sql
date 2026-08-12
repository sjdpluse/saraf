-- =============================================================================
-- Saraf 2.0 — اسکریپت سلامت‌سنجی دیتابیس (Read-Only)
-- =============================================================================
-- این اسکریپت فقط SELECT است — هیچ داده‌ای را تغییر نمی‌دهد. می‌توانید آن را
-- هر چند وقت یک‌بار (مثلاً هفتگی) در Supabase SQL Editor اجرا کنید تا مطمئن
-- شوید ایندکس‌ها/قیدهای حیاتی سر جای خودشان هستند و داده‌ها ناسازگار نشده‌اند.
--
-- هر بخش یک سرتیتر دارد؛ می‌توانید کل فایل را یک‌جا اجرا کنید (Supabase چند
-- نتیجه را پشت‌هم نشان می‌دهد) یا هر بخش را جداگانه کپی/اجرا کنید.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1) ایندکس‌های حیاتی — به‌خصوص usdt_orders_chat_id_idempotency_key_uidx که کل
--    تضمین «۱۰ درخواست هم‌زمان -> ۱ سفارش» رویش سوار است. باید همیشه ۹ ردیف
--    برگرداند؛ اگر کمتر بود، همان ایندکس گم‌شده را دوباره از migration مربوطه
--    اجرا کنید.
-- -----------------------------------------------------------------------------
SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'usdt_orders_chat_id_idempotency_key_uidx',
    'usdt_quotes_chat_id_created_at_idx',
    'usdt_quotes_active_expiry_idx',
    'usdt_order_status_history_order_idx',
    'usdt_order_status_history_unattributed_idx',
    'audit_log_entity_idx',
    'audit_log_actor_idx',
    'audit_log_created_at_idx',
    'audit_log_action_idx'
  )
ORDER BY indexname;


-- -----------------------------------------------------------------------------
-- 2) قیدهای (CHECK constraints) حیاتی — باید هر ۴ ردیف برگردانند و status باید
--    'CHECK' باشد (نه چیز دیگری).
-- -----------------------------------------------------------------------------
SELECT conname AS constraint_name, conrelid::regclass AS table_name, contype, convalidated
FROM pg_constraint
WHERE conname IN (
    'usdt_orders_positive_amounts_check',
    'usdt_orders_fee_percent_check',
    'user_profiles_nonnegative_counters_check',
    'usdt_orders_status_check'
  )
ORDER BY conname;
-- نکته: این ۳ تای اول با NOT VALID ساخته شدند، پس convalidated=false طبیعی
-- است (یعنی روی ردیف‌های قدیمی‌تر اعتبارسنجی نشده، ولی برای INSERT/UPDATE
-- جدید همیشه اعمال می‌شود). اگر می‌خواهید کاملاً validate هم بشوند:
--   ALTER TABLE public.usdt_orders VALIDATE CONSTRAINT usdt_orders_positive_amounts_check;
--   ALTER TABLE public.usdt_orders VALIDATE CONSTRAINT usdt_orders_fee_percent_check;
--   ALTER TABLE public.user_profiles VALIDATE CONSTRAINT user_profiles_nonnegative_counters_check;
-- (این یک عملیات فقط-خواندنی روی داده است، چیزی را تغییر نمی‌دهد؛ فقط اگر رکورد
-- قدیمی ناقضی پیدا شود خطا می‌دهد و باید دستی بررسی شود.)


-- -----------------------------------------------------------------------------
-- 3) باکت‌های Storage — هر سه باید public = false باشند (رسید/KYC/کارت دیجیتال
--    نباید با لینک عمومی قابل‌حدس‌زدن قابل‌دسترس باشند).
-- -----------------------------------------------------------------------------
SELECT id, name, public
FROM storage.buckets
WHERE id IN ('usdt-receipts', 'usdt-kyc-docs', 'usdt-cards')
ORDER BY id;
-- انتظار: public = false برای هر سه ردیف.


-- -----------------------------------------------------------------------------
-- 4) شمارش ردیف‌ها به تفکیک جدول — یک نمای کلی سریع از حجم داده.
-- -----------------------------------------------------------------------------
SELECT 'users' AS table_name, count(*) FROM public.users
UNION ALL SELECT 'user_profiles', count(*) FROM public.user_profiles
UNION ALL SELECT 'usdt_orders', count(*) FROM public.usdt_orders
UNION ALL SELECT 'usdt_quotes', count(*) FROM public.usdt_quotes
UNION ALL SELECT 'usdt_order_status_history', count(*) FROM public.usdt_order_status_history
UNION ALL SELECT 'audit_log', count(*) FROM public.audit_log
ORDER BY table_name;


-- -----------------------------------------------------------------------------
-- 5) idempotency_key تکراری برای یک chat_id — باید همیشه صفر ردیف برگرداند.
--    اگر چیزی برگشت، یعنی ایندکس یکتای بخش ۱ یا گم شده یا کار نمی‌کند —
--    فوراً نیاز به بررسی جدی دارد (دقیقاً همان چیزی که کل idempotency را
--    تضمین می‌کند).
-- -----------------------------------------------------------------------------
SELECT chat_id, idempotency_key, count(*) AS duplicate_count
FROM public.usdt_orders
WHERE idempotency_key IS NOT NULL
GROUP BY chat_id, idempotency_key
HAVING count(*) > 1;
-- انتظار: بدون ردیف.


-- -----------------------------------------------------------------------------
-- 6) سفارش‌های تکمیل/لغوشده بدون timestamp مربوطه — نشانهٔ یک مسیر status update
--    قدیمی/دورزده که از transition_order_status عبور نکرده (extra_fields ثبت
--    نشده). اگر ردیفی برگشت، یعنی یک جای دیگر کد مستقیم status را عوض کرده.
-- -----------------------------------------------------------------------------
SELECT id, status, created_at, confirmed_at, completed_at, cancelled_at, source
FROM public.usdt_orders
WHERE (status = 'completed' AND completed_at IS NULL)
   OR (status = 'confirmed' AND confirmed_at IS NULL)
   OR (status = 'cancelled' AND cancelled_at IS NULL)
ORDER BY created_at DESC
LIMIT 50;
-- انتظار: بدون ردیف (یا فقط سفارش‌های بسیار قدیمی از قبل از این هاردنینگ).


-- -----------------------------------------------------------------------------
-- 7) Quote های «active» ولی از قبل منقضی‌شده که هنوز expire نشده‌اند — یعنی
--    کاربر آن Quote را هرگز دوباره لمس نکرده (نه finalize کرد، نه دوباره
--    درخواست داد) تا مسیر _mark_expired صدا زده شود. کاملاً بی‌خطر (این
--    Quote ها دیگر توسط load_and_validate پذیرفته نمی‌شوند چون expires_at
--    چک می‌شود)، ولی برای نظافت/گزارش مفید است.
-- -----------------------------------------------------------------------------
SELECT id, chat_id, order_type, usdt_amount, created_at, expires_at
FROM public.usdt_quotes
WHERE status = 'active' AND expires_at < now()
ORDER BY expires_at DESC
LIMIT 50;


-- -----------------------------------------------------------------------------
-- 8) سفارش‌های pending قدیمی‌تر از ۲۴ ساعت — این یک چک عملیاتی است (نه باگ):
--    یعنی سفارشی هست که هنوز منتظر بررسی ادمین مانده. برای رصد صف کاری مفید
--    است، نه برای دیباگ.
-- -----------------------------------------------------------------------------
SELECT id, chat_id, order_type, usdt_amount, status, created_at,
       now() - created_at AS age
FROM public.usdt_orders
WHERE status = 'pending' AND created_at < now() - interval '24 hours'
ORDER BY created_at ASC
LIMIT 50;


-- -----------------------------------------------------------------------------
-- 9) سفارش‌هایی که quote_id دارند ولی Quote مرتبط هنوز 'active' مانده (باید
--    بعد از ساخت سفارش به 'consumed' تغییر کند). اگر ردیفی برگشت، یعنی
--    quote_service.consume برای آن سفارش صدا زده نشده یا خطا خورده — از audit_log
--    (پایین) هم می‌توانید ردش کنید.
-- -----------------------------------------------------------------------------
SELECT o.id AS order_id, o.status AS order_status, o.quote_id,
       q.status AS quote_status, q.expires_at
FROM public.usdt_orders o
JOIN public.usdt_quotes q ON q.id = o.quote_id
WHERE q.status = 'active'
ORDER BY o.created_at DESC
LIMIT 50;
-- انتظار: بدون ردیف.


-- -----------------------------------------------------------------------------
-- 10) پروفایل‌های کاربری با شمارندهٔ ناسازگار (successful + cancelled باید با
--     total_orders جور دربیاید). اختلاف جزئی می‌تواند طبیعی باشد (مثلاً
--     سفارش‌هایی که هنوز pending/rejected‌اند نه completed/cancelled)، پس این
--     صرفاً برای بررسی چشمی است، نه یک قاعدهٔ سخت.
-- -----------------------------------------------------------------------------
SELECT chat_id, total_orders, successful_orders, cancelled_orders,
       (total_orders - successful_orders - cancelled_orders) AS neither_completed_nor_cancelled,
       trust_score, kyc_status
FROM public.user_profiles
WHERE total_orders > 0
  AND (successful_orders + cancelled_orders) > total_orders  -- این حالت واقعاً غیرممکن باید باشد
ORDER BY chat_id
LIMIT 50;
-- انتظار: بدون ردیف. (برخلاف بخش‌های قبل، این یکی واقعاً نباید هیچ‌وقت رخ بدهد.)


-- -----------------------------------------------------------------------------
-- 11) خلاصهٔ audit_log هفت روز اخیر به تفکیک action — یک نمای کلی سریع از چه
--     نوع رویدادهایی اخیراً ثبت شده‌اند (بدون نمایش before/after که ممکن است
--     حاوی داده‌های masked باشد ولی بهتر است در گزارش کلی نیاید).
-- -----------------------------------------------------------------------------
SELECT action, entity, count(*) AS event_count, max(created_at) AS last_seen
FROM public.audit_log
WHERE created_at > now() - interval '7 days'
GROUP BY action, entity
ORDER BY event_count DESC;


-- -----------------------------------------------------------------------------
-- 12) اکشن‌های ادمین بدون actor — یعنی یک ترنزیشن/رویداد حساس ثبت شده ولی
--     مشخص نیست کدام ادمین آن را انجام داده (actor NULL). برای اکشن‌های
--     'quote_created'/'quote_consumed'/'order_created' که actor آن‌ها خودِ
--     مشتری (chat_id) است این طبیعی نیست که NULL باشد؛ برای بقیه (مثل
--     order_confirmed/order_completed/kyc_verified) actor باید همیشه شناسهٔ
--     ادمین باشد.
-- -----------------------------------------------------------------------------
SELECT action, entity, entity_id, created_at
FROM public.audit_log
WHERE actor IS NULL
  AND action IN ('order_confirmed', 'order_completed', 'order_cancelled', 'kyc_verified', 'kyc_restricted')
ORDER BY created_at DESC
LIMIT 50;
-- انتظار: بدون ردیف (یا فقط رویدادهای خیلی قدیمی قبل از این هاردنینگ).
-- =============================================================================
