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

# --- Groq (مشاور هوشمند) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

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

# --- فاصلهٔ زمانی جمع‌آوری خودکار نرخ‌های مرجع (به دقیقه) برای تاریخچه ---
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "30"))

# --- فاصلهٔ زمانی اسکرپ نرخ بازارهای محلی (سرای‌شهزاده/خراسان/بانک) به دقیقه ---
LOCAL_MARKET_FETCH_INTERVAL_MINUTES = int(
    os.getenv("LOCAL_MARKET_FETCH_INTERVAL_MINUTES", "15")
)

# --- واحدهای طلا ---
GRAMS_PER_TROY_OUNCE = 31.1034768
GRAMS_PER_METHQAL = 4.608  # مثقال افغانی/ایرانی (تقریبی و رایج)
GOLD_KARATS = {24: 1.0, 22: 22 / 24, 21: 21 / 24, 18: 18 / 24, 14: 14 / 24}
