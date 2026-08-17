"""
تنظیمات مرکزی ربات Saraf
همه مقادیر حساس از متغیرهای محیطی (Environment Variables) خوانده می‌شوند.
هرگز هیچ کلید یا توکن را مستقیم در کد نگذارید.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram (ربات اصلی مشتریان) ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_CHAT_IDS", "").split(",") if x.strip()
]
TELEGRAM_BOT_LINK = os.getenv("TELEGRAM_BOT_LINK", "https://t.me/sarafiaf_bot")

# --- Telegram (ربات دوم، مخصوص مدیریت — تایید/رد سفارش‌های تتر توسط ادمین) ---
# این ربات کاملاً جدا از ربات مشتریان اجرا می‌شود تا اعلان‌های حساس مالی با پیام‌های
# عمومی مخلوط نشوند. توکن را فقط در .env قرار بده، هرگز در کد ننویس.
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "")

# آی‌دی پشتیبانی که در پیام‌های «سفارش در انتظار» به کاربر نمایش داده می‌شود
SUPPORT_TELEGRAM_USERNAME = os.getenv("SUPPORT_TELEGRAM_USERNAME", "@SJDPLUS")
# لینک مستقیم چت با پشتیبانی — برای دکمهٔ «اطلاعات بیشتر» در جریان خرید/فروش
SUPPORT_CHAT_URL = f"https://t.me/{SUPPORT_TELEGRAM_USERNAME.lstrip('@')}"

# --- Mini App (وب‌اپلیکیشن داخل تلگرام برای خرید/فروش تتر) ---
# آدرس عمومی جایی که فرانت‌اند مینی‌اپ سرو می‌شود (همان سرویس وب/api.py روی Railway)
MINI_APP_URL = os.getenv("MINI_APP_URL", "")

# --- Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # service_role key (سرور-ساید فقط)

# --- ارزهایی که ربات پیگیری می‌کند (کد سه‌حرفی ISO) ---
TRACKED_CURRENCIES = {
    "usd": "دالر امریکایی",
    "eur": "یورو",
    "gbp": "پوند انگلیسی",
    "pkr": "کلدار پاکستانی",
    "irr": "تومان ایرانی",
    "aed": "درهم امارات",
    "inr": "روپیه هندی",
    "sar": "ریال سعودی",
    "try": "لیرهٔ ترکی",
    "cny": "یوان چین",
    "aud": "دالر آسترالیا",
    "cad": "دالر کانادا",
    "chf": "فرانک سویس",
    "sek": "کرون سویدن",
}

# --- بیرق کشورها به ازای هر ارز (برای نمایش جذاب‌تر) ---
CURRENCY_FLAGS = {
    "usd": "🇺🇸",
    "eur": "🇪🇺",
    "gbp": "🇬🇧",
    "pkr": "🇵🇰",
    "irr": "🇮🇷",
    "aed": "🇦🇪",
    "inr": "🇮🇳",
    "sar": "🇸🇦",
    "try": "🇹🇷",
    "cny": "🇨🇳",
    "aud": "🇦🇺",
    "cad": "🇨🇦",
    "chf": "🇨🇭",
    "sek": "🇸🇪",
}

# --- ارزهایی که باید به ازای هر ۱۰۰۰ واحد نمایش داده شوند ---
THOUSAND_UNIT_CURRENCIES = {"pkr", "irr", "inr"}

# --- فاصلهٔ زمانی جمع‌آوری خودکار نرخ‌های مرجع (به دقیقه) برای تاریخچه ---
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "30"))

# --- فاصلهٔ زمانی اسکرپ نرخ بازارهای محلی (سرای‌شهزاده/خراسان/بانک) به دقیقه ---
LOCAL_MARKET_FETCH_INTERVAL_MINUTES = int(
    os.getenv("LOCAL_MARKET_FETCH_INTERVAL_MINUTES", "15")
)

# --- واحدهای طلا ---
GRAMS_PER_TROY_OUNCE = 31.1034768
GRAMS_PER_METHQAL = 4.608  # مثقال افغانی/ایرانی (تقریبی و رایج)
GOLD_KARATS = {24: 1.0, 22: 22 / 24, 21: 21 / 24, 18: 18 / 24}

# --- ماشین‌حساب خرید و فروش طلا ---
GOLD_MAKING_CHARGE_PERCENT = float(os.getenv("GOLD_MAKING_CHARGE_PERCENT", "5"))
GOLD_SELL_DEDUCTION_PERCENT = float(os.getenv("GOLD_SELL_DEDUCTION_PERCENT", "2"))

# --- ماشین‌حساب خرید و فروش نقره (خالص/۹۹۹ — رایج‌ترین شکل عرضهٔ جهانی نقره؛
# برخلاف طلا، دادهٔ معتبری از عیارهای رایج نقره در بازار محلی افغانستان در
# دسترس نبود، پس فقط همین یک عیار نمایش داده می‌شود) ---
SILVER_MAKING_CHARGE_PERCENT = float(os.getenv("SILVER_MAKING_CHARGE_PERCENT", "5"))
SILVER_SELL_DEDUCTION_PERCENT = float(os.getenv("SILVER_SELL_DEDUCTION_PERCENT", "2"))

# --- فیسبوک (پست خودکار نرخ‌ها هنگام تغییر محسوس) ---
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
# حداقل درصد تغییر (نسبت به آخرین پست) که باعث ارسال پست جدید شود
FACEBOOK_CHANGE_THRESHOLD_PERCENT = float(os.getenv("FACEBOOK_CHANGE_THRESHOLD_PERCENT", "0.5"))
# لینکی که در پایان هر پست فیسبوک درج می‌شود
FACEBOOK_POST_SITE_URL = os.getenv("FACEBOOK_POST_SITE_URL", "")
# هر چند دقیقه یک‌بار بررسی شود که آیا تغییر محسوس رخ داده یا نه
FACEBOOK_CHECK_INTERVAL_MINUTES = int(os.getenv("FACEBOOK_CHECK_INTERVAL_MINUTES", "30"))
# هشتگ‌هایی که در پایان کپشن پست فیسبوک درج می‌شوند
FACEBOOK_HASHTAGS = os.getenv(
    "FACEBOOK_HASHTAGS",
    "#saraf #صراف #سراف #نرخ_اسعار #سرای_شهزاده #نرخ_ارز #طلا #افغانستان #کابل",
)

# --- اینستاگرام (پست خودکار نرخ‌ها هنگام تغییر محسوس — از همان اپ/توکن فیسبوک) ---
# اینستاگرام کسب‌وکاری/سازنده باید به همین صفحهٔ فیسبوک بالا وصل باشد؛ توکن هم
# همان FACEBOOK_PAGE_ACCESS_TOKEN است (Graph API برای هر دو یکی است)، پس چیز
# جدیدی برای احراز هویت لازم نیست — فقط شناسهٔ اکانت اینستاگرام کسب‌وکاری.
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
# هر چند دقیقه یک‌بار بررسی شود که آیا تغییر محسوس رخ داده یا نه
INSTAGRAM_CHECK_INTERVAL_MINUTES = int(os.getenv("INSTAGRAM_CHECK_INTERVAL_MINUTES", "30"))
# حداقل درصد تغییر (نسبت به آخرین پست اینستاگرام) که باعث ارسال پست جدید شود
INSTAGRAM_CHANGE_THRESHOLD_PERCENT = float(os.getenv("INSTAGRAM_CHANGE_THRESHOLD_PERCENT", "0.5"))
# هشتگ‌های اینستاگرام (جدا از فیسبوک نگه داشته شده چون سبک هشتگ‌گذاری اینستاگرام
# معمولاً متفاوت و پرتعدادتر است)
INSTAGRAM_HASHTAGS = os.getenv(
    "INSTAGRAM_HASHTAGS",
    "#saraf #صراف #سراف #نرخ_ارز #نرخ_اسعار #دلار #طلا #نقره #کابل #افغانستان "
    "#exchangerate #afghanistan #kabul #gold #silver #usdt",
)
# باکت عمومی (public) Supabase Storage که تصویر پست موقتاً در آن آپلود می‌شود تا
# یک لینک عمومی (image_url) برای Instagram Graph API فراهم شود — اینستاگرام
# برخلاف فیسبوک، آپلود مستقیم فایل باینری را نمی‌پذیرد و صرفاً یک URL عمومی
# می‌خواهد. باید در Supabase به‌صورت public ساخته شود (راهنما در
# supabase/migrations و README).
SOCIAL_POSTS_BUCKET = os.getenv("SOCIAL_POSTS_BUCKET", "social-posts")

# --- اینستاگرام: اتوماسیون کامنت (وبهوک) — پاسخ AI به کامنت‌ها + دایرکت خودکار
# وقتی کلمهٔ کلیدی کامنت شود ---
# App Secret همان اپ Meta که برای گرفتن FACEBOOK_PAGE_ACCESS_TOKEN ساختید (از
# Settings → Basic) — برای تایید امضای وبهوک (X-Hub-Signature-256) لازم است تا
# کسی نتواند با جعل درخواست، پیام دلخواه به‌جای وبهوک واقعی متا بفرستد.
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "")
# یک رشتهٔ دلخواه (خودتان می‌سازید) — همین مقدار را هنگام تنظیم Webhook در
# داشبورد Meta هم وارد می‌کنید؛ متا موقع تایید (GET) همین را پس می‌فرستد.
INSTAGRAM_WEBHOOK_VERIFY_TOKEN = os.getenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "")
# کلمات کلیدی‌یی که وقتی در کامنت دیده شوند، همان لحظه یک دایرکت (private reply)
# حاوی لینک ربات فرستاده می‌شود — بدون هیچ شرط فالو (طبق تصمیم شما)، مستقیم.
INSTAGRAM_COMMENT_KEYWORDS = [
    kw.strip() for kw in os.getenv("INSTAGRAM_COMMENT_KEYWORDS", "صراف,سراف,ربات,لینک").split(",") if kw.strip()
]
# متن دایرکتی که بعد از دیدن کلمهٔ کلیدی فرستاده می‌شود؛ {bot_link} جایگزین می‌شود.
INSTAGRAM_DM_LINK_MESSAGE = os.getenv(
    "INSTAGRAM_DM_LINK_MESSAGE",
    "سلام 👋 خوش آمدید به Saraf!\n\n"
    "برای دیدن نرخ لحظه‌یی دالر، طلا، نقره و همهٔ ارزها — کاملاً رایگان و آنی —"
    " همین لینک را باز کنید:\n{bot_link}\n\n"
    "هر سوالی هم داشتید، همین‌جا در خدمتتان هستیم 🌟",
)
# پاسخ خودکار AI زیر همهٔ کامنت‌های پست‌ها (طبق تصمیم شما: همهٔ کامنت‌ها، نه فقط
# آن‌هایی که کلمهٔ کلیدی دارند) — این دو مسیر (دایرکت با کلمهٔ کلیدی / پاسخ AI
# زیر کامنت) کاملاً مستقل از هم اجرا می‌شوند و می‌توانند هر دو روی یک کامنت بیفتند.
INSTAGRAM_AI_REPLY_ENABLED = os.getenv("INSTAGRAM_AI_REPLY_ENABLED", "true").lower() == "true"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
# System prompt به‌عمد صراحتاً از AI می‌خواهد هرگز عدد/نرخ مشخص ننویسد (چون
# ممکن است AI نرخ اشتباه یا قدیمی حدس بزند و این در یک برند صرافی می‌تواند
# گمراه‌کننده و پرخطر باشد) — همیشه کاربر را به ربات برای نرخ واقعی ارجاع می‌دهد.
OPENROUTER_SYSTEM_PROMPT = os.getenv(
    "OPENROUTER_SYSTEM_PROMPT",
    "شما دستیار رسمی پیج اینستاگرام «Saraf» (یک برند صرافی و آموزش ترید در "
    "افغانستان) هستید و به کامنت‌های زیر پست‌های اینستاگرام پاسخ کوتاه، گرم، "
    "محترمانه و به زبان دری/فارسی افغانستان می‌دهید. قوانین سخت‌گیرانه: "
    "۱) هرگز هیچ عدد یا نرخ مشخصی برای ارز، طلا، نقره یا هر قیمتی ننویسید — "
    "چون ممکن است اشتباه یا قدیمی باشد؛ همیشه کاربر را برای نرخ واقعی و لحظه‌یی "
    "به ربات تلگرام Saraf ارجاع دهید. ۲) پاسخ باید حداکثر یک تا دو جمله باشد، "
    "نه یک پاراگراف. ۳) لحن صمیمی و حرفه‌یی، بدون تبلیغاتی یا اسپم به‌نظر رسیدن؛ "
    "لازم نیست هر بار لینک ربات را تکرار کنید. ۴) اگر کامنت توهین‌آمیز یا نامرتبط "
    "بود، کوتاه و مودبانه پاسخ دهید یا فقط تشکر کنید؛ هرگز جر و بحث نکنید.",
)

# --- لوگوی Saraf (برای جاسازی در تصویر پست فیسبوک) ---
# در هر بار تولید تصویر پست، این لینک فچ (دانلود) و در طراحی استفاده می‌شود؛
# در صورت تغییر لوگو در آینده، فقط کافی است این متغیر محیطی به‌روزرسانی شود.
SARAF_LOGO_URL = os.getenv("SARAF_LOGO_URL", "https://i.postimg.cc/B6ZCWdXp/logosaraf.webp")

# --- خرید و فروش تتر (USDT) ---
USDT_MIN_AMOUNT = float(os.getenv("USDT_MIN_AMOUNT", "10"))
USDT_MAX_AMOUNT = float(os.getenv("USDT_MAX_AMOUNT", "10000"))

# آستانهٔ اجباری‌شدن احراز هویت کامل (مدرک هویتی + سلفی). زیر این مبلغ، تکمیل
# اطلاعات پایه (نام/نام خانوادگی/شماره تماس) برای ثبت سفارش کافی است.
USDT_IDENTITY_VERIFICATION_THRESHOLD_USD = float(
    os.getenv("USDT_IDENTITY_VERIFICATION_THRESHOLD_USD", "250")
)

# کارمزد پلکانی خرید تتر (٪) — فقط برای خرید؛ فروش کارمزد اضافه ندارد و صرفاً
# بر مبنای نرخ خرید دالر صرافی‌های محلی محاسبه می‌شود.
# هر ردیف: (حداقل مقدار, حداکثر مقدار, درصد کارمزد)
USDT_BUY_FEE_TIERS = [
    (10, 499.999999, 2.5),
    (500, 2999.999999, 2.0),
    (3000, 10000, 1.5),
]

# شبکه‌های قابل انتخاب برای واریز/دریافت تتر
USDT_NETWORKS = ["TRC20", "ERC20", "BEP20"]

# آدرس ولت‌های خودِ صراف برای دریافت تتر (هنگام فروش کاربر) — فقط شبکه‌هایی که
# اینجا تعریف شده‌اند فعلاً پشتیبانی می‌شوند. برای افزودن شبکهٔ جدید کافیست یک
# ردیف دیگر به این دیکشنری اضافه شود.
USDT_DEPOSIT_WALLETS = {
    "BEP20": "0x4c49Ff39798C564A01F5fdEcB7E335a178f781BA",
}

# صرافی‌های آنلاین رایج برای انتخاب سریع در فروش تتر
USDT_EXCHANGES = ["Binance", "Bybit", "OKX", "KuCoin"]

# --- اطلاعات پرداخت بانکی (برای خرید تتر به‌صورت آنلاین) ---
# منبع واحد برای هم ربات چت (handlers/usdt.py) و هم مینی‌اپ (از طریق
# GET /api/usdt/payment-info در api.py) — قبلاً مینی‌اپ این مقادیر را جدا و
# hardcode شده در JSX داشت که با تغییر این‌جا هماهنگ نمی‌شد.
BANK_NAME = os.getenv("BANK_NAME", "عزیز بانک (Azizi Bank)")
BANK_ACCOUNT_NUMBER = os.getenv("BANK_ACCOUNT_NUMBER", "000601102302066")
BANK_ACCOUNT_HOLDER = os.getenv("BANK_ACCOUNT_HOLDER", "SAJAD ALI MOHAMMADI")

# --- آدرس و شمارهٔ تماس نمایندهٔ حضوری صراف ---
IN_PERSON_ADDRESS = "کوته سنگی، همادی مارکت، کابل، افغانستان"
IN_PERSON_PHONE = "+93790810632"

# مدت اعتبار نرخ نمایش‌داده‌شده به کاربر (به دقیقه) — بعد از این مدت در لحظهٔ
# نهایی‌سازی سفارش، از کاربر خواسته می‌شود دوباره شروع کند تا با نرخ قدیمی ضرر نکند.
USDT_QUOTE_VALIDITY_MINUTES = 10

# نام باکت Supabase Storage برای نگهداری رسیدها/اسکرین‌شات‌های ارسالی از طریق مینی‌اپ
USDT_RECEIPTS_BUCKET = os.getenv("USDT_RECEIPTS_BUCKET", "usdt-receipts")

# --- KYC (احراز هویت) — باکت‌های خصوصی (نه عمومی) ---
USDT_KYC_DOCS_BUCKET = os.getenv("USDT_KYC_DOCS_BUCKET", "usdt-kyc-docs")
USDT_CARDS_BUCKET = os.getenv("USDT_CARDS_BUCKET", "usdt-cards")

# --- Trust Score — فرمول شفاف و قابل‌توضیح ---
TRUST_SCORE_BASE_VERIFIED = 50       # امتیاز پایه بعد از تایید هویت
TRUST_SCORE_PER_SUCCESS = 2          # امتیاز هر معاملهٔ موفق
TRUST_SCORE_SUCCESS_CAP = 40         # سقف امتیاز قابل‌کسب از معاملات موفق
TRUST_SCORE_CANCEL_PENALTY = 10      # جریمهٔ هر معاملهٔ لغوشده/مشکوک
TRUST_SCORE_STREAK_BONUS = 10        # پاداش رسیدن به رکورد معاملات موفق پیاپی
TRUST_SCORE_STREAK_LENGTH = 10       # چند معاملهٔ موفق پیاپی برای ارتقا به 🟢 Trusted

# --- Risk Engine — آستانه‌های قابل‌تنظیم ---
# مبلغی که برای کاربر تازه («کم‌تجربه») به‌عنوان «مبلغ بالا» حساب می‌شود
USDT_RISK_HIGH_AMOUNT_THRESHOLD = float(os.getenv("USDT_RISK_HIGH_AMOUNT_THRESHOLD", "1000"))
# کاربر با کمتر از این تعداد معاملهٔ موفق، «تازه‌کار» محسوب می‌شود
USDT_RISK_NEW_USER_ORDER_THRESHOLD = int(os.getenv("USDT_RISK_NEW_USER_ORDER_THRESHOLD", "3"))
# این تعداد معاملهٔ لغوشده/مشکوک باعث ریسک بالا می‌شود
USDT_RISK_CANCEL_COUNT_THRESHOLD = int(os.getenv("USDT_RISK_CANCEL_COUNT_THRESHOLD", "3"))
# این تعداد تغییر اطلاعات پرداخت باعث ریسک بالا می‌شود
USDT_RISK_PAYMENT_CHANGE_THRESHOLD = int(os.getenv("USDT_RISK_PAYMENT_CHANGE_THRESHOLD", "3"))