"""
تنظیمات مرکزی ربات Saraf
همه مقادیر حساس از متغیرهای محیطی (Environment Variables) خوانده می‌شوند.
هرگز هیچ کلید یا توکن را مستقیم در کد نگذارید.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_CHAT_IDS", "").split(",") if x.strip()
]

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
# --- فیسبوک (پست خودکار نرخ‌ها هنگام تغییر محسوس) ---
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
# حداقل درصد تغییر (نسبت به آخرین پست) که باعث ارسال پست جدید شود
FACEBOOK_CHANGE_THRESHOLD_PERCENT = float(os.getenv("FACEBOOK_CHANGE_THRESHOLD_PERCENT", "0.5"))
# لینکی که در پایان هر پست فیسبوک درج می‌شود
FACEBOOK_POST_SITE_URL = os.getenv("FACEBOOK_POST_SITE_URL", "")
# هر چند دقیقه یک‌بار بررسی شود که آیا تغییر محسوس رخ داده یا نه
FACEBOOK_CHECK_INTERVAL_MINUTES = int(os.getenv("FACEBOOK_CHECK_INTERVAL_MINUTES", "30"))

# --- خرید و فروش تتر (USDT) ---
USDT_MIN_AMOUNT = float(os.getenv("USDT_MIN_AMOUNT", "10"))
USDT_MAX_AMOUNT = float(os.getenv("USDT_MAX_AMOUNT", "10000"))

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
BANK_NAME = "عزیز بانک (Azizi Bank)"
BANK_ACCOUNT_NUMBER = os.getenv("BANK_ACCOUNT_NUMBER", "000601102302066")
BANK_ACCOUNT_HOLDER = os.getenv("BANK_ACCOUNT_HOLDER", "SAJAD ALI MOHAMMADI")

# --- آدرس و شمارهٔ تماس نمایندهٔ حضوری صراف ---
IN_PERSON_ADDRESS = "کوته سنگی، همادی مارکت، کابل، افغانستان"
IN_PERSON_PHONE = "+93790810632"

# مدت اعتبار نرخ نمایش‌داده‌شده به کاربر (به دقیقه) — بعد از این مدت در لحظهٔ
# نهایی‌سازی سفارش، از کاربر خواسته می‌شود دوباره شروع کند تا با نرخ قدیمی ضرر نکند.
USDT_QUOTE_VALIDITY_MINUTES = 10