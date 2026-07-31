"""
منوهای ربات (Reply Keyboard و Inline Keyboard) — همه به زبان دری.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from config import TRACKED_CURRENCIES, GOLD_KARATS, CURRENCY_FLAGS

BTN_CURRENCY = "💵 نرخ ارزها"
BTN_GOLD = "🥇 نرخ طلا"
BTN_COMPARE = "📊 مقایسه با گذشته"
BTN_CONVERTER = "🔄 مبدل ارز جهانی"
BTN_ABOUT = "ℹ️ درباره ربات"


def _flag_label(code: str, name: str) -> str:
    flag = CURRENCY_FLAGS.get(code, "")
    return f"{flag} {name}".strip()


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [BTN_CURRENCY, BTN_GOLD],
            [BTN_COMPARE, BTN_CONVERTER],
            [BTN_ABOUT],
        ],
        resize_keyboard=True,
    )


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
# مبدل ارز جهانی — کاملاً منو محور (بدون نیاز به تایپ فرمت خاص)
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