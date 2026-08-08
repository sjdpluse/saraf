# به‌روزرسانی Saraf — ربات مدیریت جدا + مینی‌اپ خرید/فروش تتر

این بسته مستقیماً روی آخرین نسخهٔ ریپازیتوری `sjdpluse/saraf` (کلون‌شده از گیت‌هاب)
اعمال شده و از نظر import و اجرا کامل تست شده است. کافیست محتوای این پوشه را روی
پوشهٔ پروژهٔ محلی‌ات کپی/جای‌گزین کنی و commit بزنی.

## خلاصهٔ همهٔ تغییرات

### فایل‌های تغییریافته
- `config.py` — افزودن `ADMIN_BOT_TOKEN`، `SUPPORT_TELEGRAM_USERNAME`، `MINI_APP_URL`، `USDT_RECEIPTS_BUCKET`
- `keyboards.py` — کیبوردهای جدید (انتخاب صرافی خرید، درخواست شماره تماس، تایید/رد ادمین) + دکمهٔ WebApp در منوی تتر
- `handlers/usdt.py` — بازنویسی کامل: اطلاع‌رسانی از طریق ربات مدیریت جدا، دریافت الزامی شماره تماس، انتخاب صرافی/کیف‌پول مقصد در خرید
- `bot.py` — مسیریابی پیام‌های جدید (شماره تماس، Contact)
- `api.py` — رفع باگ از‌قبل‌موجود (ایمپورت ماژول‌های حذف‌شدهٔ `gold_rate_engine`/`gold_market_service`) + endpointهای کامل مینی‌اپ + سرو کردن فایل‌های build
- `services/supabase_service.py` — توابع جدید: `get_usdt_orders_by_chat_id`, `upload_usdt_receipt`
- `requirements.txt` — افزودن `python-multipart` (لازم برای آپلود فایل در FastAPI)
- `Procfile` — افزودن سرویس `admin_worker`

### فایل‌های جدید
- `admin_bot.py` — ربات مستقل مدیریت (تایید/رد سفارش با یک لمس)
- `services/usdt_order_service.py` — منبع واحد ثبت سفارش (استفاده‌شده هم توسط ربات، هم API)
- `services/webapp_auth.py` — اعتبارسنجی امضای initData تلگرام
- `webapp/` — مینی‌اپ کامل (React + Vite)، از قبل build شده در `webapp/dist/`
- `sql/2026_08_usdt_miniapp_update.sql` — مهاجرت پایگاه داده
- `.env.example` — نمونهٔ متغیرهای محیطی

## ⚠️ یک باگ از قبل موجود که اصلاح شد
در کامیت «back to v2» دو فایل `services/gold_rate_engine.py` و
`services/gold_market_service.py` حذف شده بودند اما `api.py` هنوز به آن‌ها ارجاع
می‌داد — یعنی سرویس `web` روی Railway در حال کرش بود. این را با بازگرداندن منطق
محاسبهٔ طلا به `gold_service.py` (همان چیزی که ربات هم استفاده می‌کند) اصلاح کردم؛
الان `/api/gold` و `/api/gold/{karat}` دوباره کار می‌کنند.

## مراحل دیپلوی (به ترتیب انجام بده)

### ۱) پایگاه داده
اسکریپت `sql/2026_08_usdt_miniapp_update.sql` را در Supabase SQL Editor اجرا کن.
سپس طبق راهنمای داخل همان فایل، یک باکت Storage عمومی به نام `usdt-receipts` بساز.

### ۲) ساخت ربات مدیریت
در تلگرام به @BotFather پیام بده، `/newbot` بزن، یک ربات کاملاً جدید بساز (مثلاً
`SarafAdminBot`) و توکنش را در `.env` به‌عنوان `ADMIN_BOT_TOKEN` قرار بده.

### ۳) متغیرهای محیطی
فایل `.env.example` را ببین و مقادیر واقعی (`ADMIN_BOT_TOKEN`, `MINI_APP_URL` و...)
را در Railway → Variables برای هر سه سرویس (`worker`, `admin_worker`, `web`) تنظیم کن.
`MINI_APP_URL` باید همان آدرس عمومی سرویس `web` باشد (مثلاً
`https://saraf-production.up.railway.app`) — این را بعد از اولین دیپلوی از تب
Settings → Networking همان سرویس در Railway پیدا می‌کنی.

### ۴) افزودن سرویس admin_worker در Railway
روی Railway، یک سرویس جدید در همان پروژه بساز که از همین ریپازیتوری، با
Start Command برابر `python admin_bot.py` اجرا شود (یا مطمئن شو Railway
`Procfile` را می‌خواند و پردازهٔ `admin_worker` را خودش می‌سازد).

### ۵) اتصال اولیهٔ ربات مدیریت
بعد از دیپلوی، با همان اکانت تلگرامی‌ای که چت‌آیدی‌اش در `ADMIN_CHAT_IDS` هست، به
ربات مدیریت پیام `/start` بفرست (تلگرام اجازه نمی‌دهد رباتی به کاربری که مکالمه
را شروع نکرده پیام بدهد).

### ۶) دیپلوی نهایی
بعد از تنظیم `MINI_APP_URL`، سرویس `web` را یک‌بار دیگر Redeploy کن تا دکمهٔ
مینی‌اپ در منوی تتر ظاهر شود (اگر `MINI_APP_URL` خالی باشد، ربات به‌صورت خودکار
فقط جریان گفتگویی معمولی را نشان می‌دهد — هیچ‌چیزی خراب نمی‌شود).

### ۷) (اختیاری ولی پیشنهادی) تنظیم دکمهٔ منوی تلگرام
در @BotFather → ربات اصلی → Bot Settings → Menu Button → آدرس مینی‌اپ
(`https://<your-app>.up.railway.app/miniapp/`) را ثبت کن تا کاربران بتوانند از
دکمهٔ کنار جعبهٔ پیام هم مستقیم وارد اپ شوند.

## توسعهٔ محلی مینی‌اپ (در صورت نیاز به تغییر بعدی)
```bash
cd webapp
npm install
npm run dev        # پیش‌نمایش محلی روی پورت 5173 (با پراکسی به /api روی 8000)
npm run build      # ساخت نسخهٔ نهایی در webapp/dist/ — این پوشه باید commit شود
```
`webapp/dist/` را حتماً commit کن، چون سرویس `web` مستقیماً همین فایل‌های
build-شده را سرو می‌کند و Railway به‌صورت پیش‌فرض مرحلهٔ build فرانت‌اند را اجرا
نمی‌کند.

## تست‌هایی که همین‌جا قبل از تحویل انجام شد
- سینتکس تمام فایل‌های پایتون تغییریافته ✅
- import کامل `bot.py`, `api.py`, `admin_bot.py` با متغیرهای محیطی نمونه ✅
- `build_application()` ربات اصلی (۲۹ handler) ✅
- اجرای واقعی `uvicorn api:app` و تست زندهٔ endpointها:
  - `/api/health` → 200 ✅
  - `/miniapp/` → 200 (فایل‌های React سرو می‌شوند) ✅
  - `/api/usdt/quote` بدون initData → 401 (رد صحیح) ✅
  - `/api/usdt/quote` با initData معتبر (امضای HMAC شبیه‌سازی‌شده) → عبور از احراز هویت ✅
  - `/api/usdt/orders/me` با initData معتبر → 200 ✅
- `npm run build` مینی‌اپ بدون خطا ✅
