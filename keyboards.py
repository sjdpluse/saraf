"""
منوهای ربات (Reply Keyboard و Inline Keyboard) — همه به زبان دری.
"""
from urllib.parse import urlencode

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)

from config import (
    TRACKED_CURRENCIES,
    GOLD_KARATS,
    CURRENCY_FLAGS,
    USDT_NETWORKS,
    USDT_EXCHANGES,
    MINI_APP_URL,
    SUPPORT_CHAT_URL,
)

# --- دکمه‌های منوی اصلی ---
BTN_CURRENCY = "💵 نرخ ارزها"
BTN_GOLD = "🥇 نرخ طلا"
BTN_SILVER = "🥈 نرخ نقره"
BTN_CRYPTO = "🪙 نرخ رمزارزها"
BTN_COMPARE = "📊 مقایسه با گذشته"
BTN_CONVERTER = "🔄 مبدل ارز جهانی"
BTN_USDT = "🟢 خرید و فروش تتر - USDT"
BTN_ABOUT = "ℹ️ درباره ربات"
# فقط برای ادمین — نشر دستی پست نرخ‌ها در فیسبوک/اینستاگرام (تست + کنترل دستی)
BTN_ADMIN_POST = "📢 نشر پست (فیسبوک/اینستاگرام)"


def _flag_label(code: str, name: str) -> str:
    flag = CURRENCY_FLAGS.get(code, "")
    return f"{flag} {name}".strip()


def _support_chat_url(text: str) -> str:
    """لینک مستقیم پشتیبانی با متن پیش‌نویس داخل کادر پیام تلگرام."""
    return f"{SUPPORT_CHAT_URL}?{urlencode({'text': text})}"


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    is_admin=True فقط برای کاربرانی که chat_id شان در ADMIN_CHAT_IDS است ست
    می‌شود (نگاه کنید به handlers/start.py) — چون این تابع هر بار برای همان
    chat مشخص و به‌صورت جداگانه صدا زده می‌شود (نه یک منوی global مشترک)، دکمهٔ
    اضافه‌شده فقط در کیبورد همان کاربر ادمین ظاهر می‌شود، نه در کیبورد بقیهٔ
    کاربران.
    """
    rows = [
        [BTN_CURRENCY, BTN_GOLD],
        [BTN_SILVER, BTN_CRYPTO],
        [BTN_COMPARE, BTN_CONVERTER],
        [BTN_USDT],
        [BTN_ABOUT],
    ]
    if is_admin:
        rows.append([BTN_ADMIN_POST])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ---------------------------------------------------------------------------
# نرخ ارز
# ---------------------------------------------------------------------------
def currency_list_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for code, name in TRACKED_CURRENCIES.items():
        row.append(InlineKeyboardButton(_flag_label(code, name), callback_data=f"cur:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🔄 نمایش همهٔ نرخ‌ها", callback_data="cur:all")])
    return InlineKeyboardMarkup(rows)


def currency_quote_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧮 صراف", callback_data=f"curcalc:{code}")],
        ]
    )


# ---------------------------------------------------------------------------
# نرخ طلا
# ---------------------------------------------------------------------------
def gold_karat_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"عیار {k}", callback_data=f"gold:{k}")]
        for k in GOLD_KARATS
    ]
    rows.append([InlineKeyboardButton("🔄 نمایش همهٔ عیارها", callback_data="gold:all")])
    rows.append(
        [InlineKeyboardButton("🧮 ماشین‌حساب خرید/فروش طلا", callback_data="gold:calc")]
    )
    return InlineKeyboardMarkup(rows)


def gold_calc_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟢 خرید طلا", callback_data="goldcalc_mode:buy"),
                InlineKeyboardButton("🔴 فروش طلا", callback_data="goldcalc_mode:sell"),
            ]
        ]
    )


def gold_calc_karat_keyboard(mode: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"عیار {k}", callback_data=f"goldcalc_karat:{mode}:{k}")]
        for k in GOLD_KARATS
    ]
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# نرخ نقره
# ---------------------------------------------------------------------------
def silver_calc_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟢 خرید نقره", callback_data="silvercalc_mode:buy"),
                InlineKeyboardButton("🔴 فروش نقره", callback_data="silvercalc_mode:sell"),
            ]
        ]
    )


# ---------------------------------------------------------------------------
# مقایسه با گذشته
# ---------------------------------------------------------------------------
def compare_target_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for code, name in TRACKED_CURRENCIES.items():
        row.append(InlineKeyboardButton(_flag_label(code, name), callback_data=f"cmp_target:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🥇 طلا (عیار ۲۴)", callback_data="cmp_target:gold")])
    return InlineKeyboardMarkup(rows)


def compare_period_keyboard(target_code: str, target_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏱ ۲۴ ساعت پیش", callback_data=f"cmp_period:{target_code}:1"),
                InlineKeyboardButton("📅 ۷ روز پیش", callback_data=f"cmp_period:{target_code}:7"),
            ],
            [
                InlineKeyboardButton("🗓 ۳۰ روز پیش", callback_data=f"cmp_period:{target_code}:30"),
                InlineKeyboardButton("📆 ۹۰ روز پیش", callback_data=f"cmp_period:{target_code}:90"),
            ],
        ]
    )


# ---------------------------------------------------------------------------
# مبدل ارز جهانی
# ---------------------------------------------------------------------------
def converter_from_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for code, name in TRACKED_CURRENCIES.items():
        row.append(InlineKeyboardButton(_flag_label(code, name), callback_data=f"convfrom:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def converter_to_keyboard(from_code: str) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for code, name in TRACKED_CURRENCIES.items():
        if code == from_code:
            continue
        row.append(InlineKeyboardButton(_flag_label(code, name), callback_data=f"convto:{from_code}:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 تغییر ارز مبدأ", callback_data="convfrom:back")])
    return InlineKeyboardMarkup(rows)


def converter_amount_keyboard() -> InlineKeyboardMarkup:
    presets = [1, 10, 50, 100, 500, 1000]
    rows = []
    row = []
    for amt in presets:
        row.append(InlineKeyboardButton(f"{amt:,}", callback_data=f"convamt:{amt}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("✏️ مقدار دلخواه", callback_data="convamt:custom")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# خرید و فروش تتر (USDT)
# ---------------------------------------------------------------------------
def usdt_menu_keyboard() -> InlineKeyboardMarkup:
    rows = []
    # اگر آدرس مینی‌اپ تنظیم شده، دکمهٔ ورود به تجربهٔ کامل‌تر (فرم + پیگیری سفارش‌ها)
    # را در بالای منو نشان بده. جریان گفتگویی زیر همیشه به‌عنوان مسیر پشتیبان می‌ماند.
    if MINI_APP_URL:
        rows.append(
            [
                InlineKeyboardButton(
                    "🚀 باز کردن اپلیکیشن تتر (پیشنهادی)",
                    web_app=WebAppInfo(url=f"{MINI_APP_URL.rstrip('/')}/miniapp/"),
                )
            ]
        )
        # دکمه‌های خرید/فروش هم مستقیم به همان صفحهٔ خرید/فروش مینی‌اپ باز می‌شوند
        # (نه جریان گفتگویی قدیمی) — با یک پارامتر URL که مینی‌اپ در بارگذاری اول
        # می‌خواند و مستقیم همان صفحه را باز می‌کند.
        rows.append(
            [
                InlineKeyboardButton(
                    "🟢 خرید تتر",
                    web_app=WebAppInfo(url=f"{MINI_APP_URL.rstrip('/')}/miniapp/?action=buy"),
                ),
                InlineKeyboardButton(
                    "🔴 فروش تتر",
                    web_app=WebAppInfo(url=f"{MINI_APP_URL.rstrip('/')}/miniapp/?action=sell"),
                ),
            ]
        )
    else:
        # نبود MINI_APP_URL یعنی مینی‌اپ روی این استقرار فعال نیست — جریان
        # گفتگویی قدیمی داخل خود ربات به‌عنوان تنها مسیر باقی می‌ماند.
        rows.append(
            [
                InlineKeyboardButton("🟢 خرید تتر", callback_data="usdt_action:buy"),
                InlineKeyboardButton("🔴 فروش تتر", callback_data="usdt_action:sell"),
            ]
        )
    return InlineKeyboardMarkup(rows)


def usdt_continue_keyboard(action: str) -> InlineKeyboardMarkup:
    verb = "خرید" if action == "buy" else "فروش"
    info_url = _support_chat_url("سلام، در مورد خرید و فروش تتر در Saraf معلومات بیشتر می‌خواهم.")
    support_url = _support_chat_url("سلام، برای خرید و فروش تتر در Saraf به پشتیبانی نیاز دارم.")
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"✅ درخواست {verb} تتر", callback_data=f"usdt_continue:{action}")],
            [
                InlineKeyboardButton("💬 اطلاعات بیشتر", url=info_url),
                InlineKeyboardButton("🎧 پشتیبانی", url=support_url),
            ],
        ]
    )


def usdt_payment_method_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🏢 حضوری", callback_data=f"usdt_pay:{action}:in_person"),
                InlineKeyboardButton("🏦 آنلاین", callback_data=f"usdt_pay:{action}:online"),
            ]
        ]
    )


def usdt_in_person_paid_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ پرداخت را انجام دادم", callback_data=f"usdt_paid:{action}")]]
    )


def usdt_network_keyboard(action: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(net, callback_data=f"usdt_net:{action}:{net}")]
        for net in USDT_NETWORKS
    ]
    rows.append([InlineKeyboardButton("✏️ شبکهٔ دیگر", callback_data=f"usdt_net:{action}:other")])
    return InlineKeyboardMarkup(rows)


def usdt_buy_exchange_keyboard() -> InlineKeyboardMarkup:
    """انتخاب صرافی/کیف‌پول مقصد برای دریافت تتر در مسیر خرید."""
    rows, row = [], []
    for ex in USDT_EXCHANGES:
        row.append(InlineKeyboardButton(ex, callback_data=f"usdt_buy_exch:{ex}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [InlineKeyboardButton("👛 کیف پول شخصی / دیگر", callback_data="usdt_buy_exch:other")]
    )
    return InlineKeyboardMarkup(rows)


def admin_order_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """دکمه‌های تایید/رد سفارش — مرحلهٔ اول بررسی، فقط در ربات مدیریت (admin_bot.py)."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ تایید سفارش", callback_data=f"admin_confirm:{order_id}"),
                InlineKeyboardButton("❌ رد سفارش", callback_data=f"admin_reject:{order_id}"),
            ]
        ]
    )


def admin_order_complete_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """بعد از تایید سفارش نمایش داده می‌شود — وقتی واقعاً تتر/پول ارسال شد، ادمین این را می‌زند."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📦 تکمیل شد (پرداخت/واریز انجام شد)", callback_data=f"admin_complete:{order_id}")]]
    )


def usdt_rating_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """درخواست امتیازدهی از مشتری بعد از تکمیل سفارش — در ربات اصلی مشتریان استفاده می‌شود."""
    stars_row = [
        InlineKeyboardButton("⭐" * n, callback_data=f"usdt_rate:{order_id}:{n}") for n in range(1, 6)
    ]
    return InlineKeyboardMarkup([stars_row])


def kyc_phone_keyboard() -> ReplyKeyboardMarkup:
    """درخواست اشتراک‌گذاری شمارهٔ تماس در مرحلهٔ احراز هویت."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 ارسال شمارهٔ تماس من", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def kyc_review_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """دکمه‌های تایید/رد احراز هویت — فقط در ربات مدیریت (admin_bot.py)."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ تایید هویت", callback_data=f"admin_kyc_verify:{chat_id}"),
                InlineKeyboardButton("❌ رد هویت", callback_data=f"admin_kyc_reject:{chat_id}"),
            ]
        ]
    )


def usdt_exchange_keyboard() -> InlineKeyboardMarkup:
    rows, row = [], []
    for ex in USDT_EXCHANGES:
        row.append(InlineKeyboardButton(ex, callback_data=f"usdt_exch:{ex}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("✏️ صرافی دیگر", callback_data="usdt_exch:other")])
    return InlineKeyboardMarkup(rows)
