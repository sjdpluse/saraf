"""
تنظیمات مرکزی ربات Saraf

همه مقادیر حساس از Environment Variables خوانده می‌شوند.
هیچ Token / Secret نباید داخل Source Code قرار بگیرد.
"""

import os

from dotenv import load_dotenv


load_dotenv()


# ============================================================
# Telegram — ربات اصلی
# ============================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
)

ADMIN_CHAT_IDS = [
    int(x.strip())
    for x in os.getenv(
        "ADMIN_CHAT_IDS",
        "",
    ).split(",")
    if x.strip()
]

TELEGRAM_BOT_LINK = os.getenv(
    "TELEGRAM_BOT_LINK",
    "https://t.me/sarafiaf_bot",
)


# ============================================================
# Telegram — ربات مدیریت
# ============================================================

ADMIN_BOT_TOKEN = os.getenv(
    "ADMIN_BOT_TOKEN",
    "",
)

SUPPORT_TELEGRAM_USERNAME = os.getenv(
    "SUPPORT_TELEGRAM_USERNAME",
    "@SJDPLUS",
)

SUPPORT_CHAT_URL = (
    f"https://t.me/"
    f"{SUPPORT_TELEGRAM_USERNAME.lstrip('@')}"
)


# ============================================================
# Mini App
# ============================================================

MINI_APP_URL = os.getenv(
    "MINI_APP_URL",
    "",
)

MINI_APP_VERSION = (
    os.getenv("MINI_APP_VERSION")
    or os.getenv("RAILWAY_GIT_COMMIT_SHA")
    or os.getenv("RAILWAY_DEPLOYMENT_ID")
    or "20260905-v3"
).strip()


# ============================================================
# Supabase
# ============================================================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "",
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "",
)


# ============================================================
# Currency
# ============================================================

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


THOUSAND_UNIT_CURRENCIES = {
    "pkr",
    "irr",
    "inr",
}


FETCH_INTERVAL_MINUTES = int(
    os.getenv(
        "FETCH_INTERVAL_MINUTES",
        "30",
    )
)


LOCAL_MARKET_FETCH_INTERVAL_MINUTES = int(
    os.getenv(
        "LOCAL_MARKET_FETCH_INTERVAL_MINUTES",
        "15",
    )
)


# ============================================================
# Gold
# ============================================================

GRAMS_PER_TROY_OUNCE = 31.1034768

GRAMS_PER_METHQAL = 4.608

GOLD_KARATS = {
    24: 1.0,
    22: 22 / 24,
    21: 21 / 24,
    18: 18 / 24,
}


GOLD_MAKING_CHARGE_PERCENT = float(
    os.getenv(
        "GOLD_MAKING_CHARGE_PERCENT",
        "5",
    )
)

GOLD_SELL_DEDUCTION_PERCENT = float(
    os.getenv(
        "GOLD_SELL_DEDUCTION_PERCENT",
        "2",
    )
)


# ============================================================
# Silver
# ============================================================

SILVER_MAKING_CHARGE_PERCENT = float(
    os.getenv(
        "SILVER_MAKING_CHARGE_PERCENT",
        "5",
    )
)

SILVER_SELL_DEDUCTION_PERCENT = float(
    os.getenv(
        "SILVER_SELL_DEDUCTION_PERCENT",
        "2",
    )
)


# ============================================================
# Facebook
# ============================================================

FACEBOOK_PAGE_ID = os.getenv(
    "FACEBOOK_PAGE_ID",
    "",
)

FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv(
    "FACEBOOK_PAGE_ACCESS_TOKEN",
    "",
)

FACEBOOK_CHANGE_THRESHOLD_PERCENT = float(
    os.getenv(
        "FACEBOOK_CHANGE_THRESHOLD_PERCENT",
        "0.5",
    )
)

FACEBOOK_POST_SITE_URL = os.getenv(
    "FACEBOOK_POST_SITE_URL",
    "",
)

FACEBOOK_CHECK_INTERVAL_MINUTES = int(
    os.getenv(
        "FACEBOOK_CHECK_INTERVAL_MINUTES",
        "30",
    )
)

FACEBOOK_HASHTAGS = os.getenv(
    "FACEBOOK_HASHTAGS",
    (
        "#saraf #صراف #سراف #نرخ_اسعار "
        "#سرای_شهزاده #نرخ_ارز #طلا "
        "#افغانستان #کابل"
    ),
)


# ============================================================
# Instagram — Content Publishing
#
# این بخش همچنان از Facebook Login flow استفاده می‌کند.
# instagram_service.py برای نشر خودکار پست می‌تواند از
# FACEBOOK_PAGE_ACCESS_TOKEN استفاده کند.
# ============================================================

INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv(
    "INSTAGRAM_BUSINESS_ACCOUNT_ID",
    "",
)

INSTAGRAM_CHECK_INTERVAL_MINUTES = int(
    os.getenv(
        "INSTAGRAM_CHECK_INTERVAL_MINUTES",
        "30",
    )
)

INSTAGRAM_CHANGE_THRESHOLD_PERCENT = float(
    os.getenv(
        "INSTAGRAM_CHANGE_THRESHOLD_PERCENT",
        "0.5",
    )
)

INSTAGRAM_HASHTAGS = os.getenv(
    "INSTAGRAM_HASHTAGS",
    (
        "#saraf #صراف #سراف #نرخ_ارز "
        "#نرخ_اسعار #دلار #طلا #نقره "
        "#کابل #افغانستان #exchangerate "
        "#afghanistan #kabul #gold "
        "#silver #usdt"
    ),
)


SOCIAL_POSTS_BUCKET = os.getenv(
    "SOCIAL_POSTS_BUCKET",
    "social-posts",
)


# ============================================================
# Instagram — Comment Automation
#
# مهم:
# این قسمت از Instagram API with Instagram Login استفاده می‌کند.
#
# بنابراین:
#
# Token:
# INSTAGRAM_USER_ACCESS_TOKEN
#
# Host:
# graph.instagram.com
#
# با Facebook Page Token مخلوط نشود.
# ============================================================

INSTAGRAM_APP_SECRET = os.getenv(
    "INSTAGRAM_APP_SECRET",
    "",
).strip()


INSTAGRAM_WEBHOOK_VERIFY_TOKEN = os.getenv(
    "INSTAGRAM_WEBHOOK_VERIFY_TOKEN",
    "",
).strip()


INSTAGRAM_USER_ACCESS_TOKEN = os.getenv(
    "INSTAGRAM_USER_ACCESS_TOKEN",
    "",
).strip()


INSTAGRAM_USER_ID = os.getenv(
    "INSTAGRAM_USER_ID",
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
).strip()


INSTAGRAM_BUSINESS_USERNAME = (
    os.getenv(
        "INSTAGRAM_BUSINESS_USERNAME",
        "",
    )
    .strip()
    .lstrip("@")
    .lower()
)


INSTAGRAM_GRAPH_API_VERSION = os.getenv(
    "INSTAGRAM_GRAPH_API_VERSION",
    "v26.0",
).strip()

if not INSTAGRAM_GRAPH_API_VERSION.startswith("v"):
    INSTAGRAM_GRAPH_API_VERSION = (
        f"v{INSTAGRAM_GRAPH_API_VERSION}"
    )


INSTAGRAM_COMMENT_KEYWORDS = [
    keyword.strip()
    for keyword in os.getenv(
        "INSTAGRAM_COMMENT_KEYWORDS",
        "صراف,سراف,ربات,لینک",
    ).split(",")
    if keyword.strip()
]


INSTAGRAM_DM_LINK_MESSAGE = os.getenv(
    "INSTAGRAM_DM_LINK_MESSAGE",
    (
        "سلام 👋 خوش آمدید به Saraf!\n\n"
        "برای دیدن نرخ لحظه‌یی دالر، طلا، نقره "
        "و همهٔ ارزها — کاملاً رایگان و آنی — "
        "همین لینک را باز کنید:\n"
        "{bot_link}\n\n"
        "هر سوالی هم داشتید، همین‌جا در خدمتتان هستیم 🌟"
    ),
)


INSTAGRAM_AI_REPLY_ENABLED = (
    os.getenv(
        "INSTAGRAM_AI_REPLY_ENABLED",
        "true",
    ).strip().lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


# ============================================================
# OpenRouter — Instagram AI Reply
# ============================================================

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    "",
).strip()


# مدل اصلی
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemma-4-31b-it:free",
).strip()


# اگر مدل اصلی rate-limit/down شود، OpenRouter به این مدل‌ها
# به ترتیب fallback می‌کند.
#
# openrouter/free یک Router رسمی رایگان است که یک Free Model
# در دسترس را انتخاب می‌کند.
OPENROUTER_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv(
        "OPENROUTER_FALLBACK_MODELS",
        "openrouter/free",
    ).split(",")
    if model.strip()
]


OPENROUTER_SYSTEM_PROMPT = os.getenv(
    "OPENROUTER_SYSTEM_PROMPT",
    (
        "شما دستیار رسمی پیج اینستاگرام «Saraf» "
        "(یک برند صرافی و آموزش ترید در افغانستان) هستید. "
        "به کامنت‌های کاربران کوتاه، طبیعی، محترمانه و "
        "به زبان دری/فارسی افغانستان پاسخ دهید. "

        "قوانین: "
        "۱) هرگز هیچ نرخ، قیمت یا عدد مالی مشخصی از خودتان "
        "تولید نکنید، چون ممکن است قدیمی یا اشتباه باشد. "
        "برای نرخ لحظه‌یی، کاربر را به ربات رسمی Saraf ارجاع دهید. "

        "۲) پاسخ حداکثر یک یا دو جمله باشد. "

        "۳) لحن انسانی، حرفه‌یی و دوستانه باشد و شبیه اسپم "
        "یا تبلیغات تکراری نباشد. "

        "۴) لازم نیست در تمام پاسخ‌ها لینک ربات را بنویسید. "

        "۵) اگر کامنت فقط تشکر یا تعریف بود، کوتاه تشکر کنید. "

        "۶) اگر کامنت نامرتبط یا توهین‌آمیز بود، محترمانه و "
        "کوتاه پاسخ دهید و وارد جر و بحث نشوید."
    ),
)


# ============================================================
# Branding
# ============================================================

SARAF_LOGO_URL = os.getenv(
    "SARAF_LOGO_URL",
    "https://i.postimg.cc/B6ZCWdXp/logosaraf.webp",
)


# ============================================================
# USDT
# ============================================================

USDT_MIN_AMOUNT = float(
    os.getenv(
        "USDT_MIN_AMOUNT",
        "10",
    )
)

USDT_MAX_AMOUNT = float(
    os.getenv(
        "USDT_MAX_AMOUNT",
        "10000",
    )
)


USDT_IDENTITY_VERIFICATION_THRESHOLD_USD = float(
    os.getenv(
        "USDT_IDENTITY_VERIFICATION_THRESHOLD_USD",
        "250",
    )
)


USDT_BUY_FEE_TIERS = [
    (10, 499.999999, 2.5),
    (500, 2999.999999, 2.0),
    (3000, 10000, 1.5),
]


USDT_NETWORKS = [
    "TRC20",
    "ERC20",
    "BEP20",
]


USDT_DEPOSIT_WALLETS = {
    "BEP20": "0x4c49Ff39798C564A01F5fdEcB7E335a178f781BA",
}


USDT_EXCHANGES = [
    "Binance",
    "Bybit",
    "OKX",
    "KuCoin",
]


# ============================================================
# Bank Payment
# ============================================================

BANK_NAME = os.getenv(
    "BANK_NAME",
    "عزیز بانک (Azizi Bank)",
)

BANK_ACCOUNT_NUMBER = os.getenv(
    "BANK_ACCOUNT_NUMBER",
    "000601102302066",
)

BANK_ACCOUNT_HOLDER = os.getenv(
    "BANK_ACCOUNT_HOLDER",
    "SAJAD ALI MOHAMMADI",
)


# ============================================================
# In-person
# ============================================================

IN_PERSON_ADDRESS = (
    "کوته سنگی، همادی مارکت، کابل، افغانستان"
)

IN_PERSON_PHONE = (
    "+93790810632"
)


USDT_QUOTE_VALIDITY_MINUTES = 10


USDT_RECEIPTS_BUCKET = os.getenv(
    "USDT_RECEIPTS_BUCKET",
    "usdt-receipts",
)


USDT_KYC_DOCS_BUCKET = os.getenv(
    "USDT_KYC_DOCS_BUCKET",
    "usdt-kyc-docs",
)

USDT_CARDS_BUCKET = os.getenv(
    "USDT_CARDS_BUCKET",
    "usdt-cards",
)


# ============================================================
# Trust Score
# ============================================================

TRUST_SCORE_BASE_VERIFIED = 50

TRUST_SCORE_PER_SUCCESS = 2

TRUST_SCORE_SUCCESS_CAP = 40

TRUST_SCORE_CANCEL_PENALTY = 10

TRUST_SCORE_STREAK_BONUS = 10

TRUST_SCORE_STREAK_LENGTH = 10


# ============================================================
# Risk Engine
# ============================================================

USDT_RISK_HIGH_AMOUNT_THRESHOLD = float(
    os.getenv(
        "USDT_RISK_HIGH_AMOUNT_THRESHOLD",
        "1000",
    )
)

USDT_RISK_NEW_USER_ORDER_THRESHOLD = int(
    os.getenv(
        "USDT_RISK_NEW_USER_ORDER_THRESHOLD",
        "3",
    )
)

USDT_RISK_CANCEL_COUNT_THRESHOLD = int(
    os.getenv(
        "USDT_RISK_CANCEL_COUNT_THRESHOLD",
        "3",
    )
)

USDT_RISK_PAYMENT_CHANGE_THRESHOLD = int(
    os.getenv(
        "USDT_RISK_PAYMENT_CHANGE_THRESHOLD",
        "3",
    )
)