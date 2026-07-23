"""
منوهای ربات (Reply Keyboard و Inline Keyboard) — همه به زبان دری.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from config import TRACKED_CURRENCIES, GOLD_KARATS

BTN_CURRENCY = "💵 نرخ ارزها"
BTN_GOLD = "🥇 نرخ طلا"
BTN_COMPARE = "📊 مقایسه با گذشته"
BTN_ADVISOR = "🤖 مشاور هوشمند"
BTN_ABOUT = "ℹ️ درباره ربات"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [BTN_CURRENCY, BTN_GOLD],
            [BTN_COMPARE, BTN_ADVISOR],
            [BTN_ABOUT],
        ],
        resize_keyboard=True,
    )


def currency_list_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for code, name in TRACKED_CURRENCIES.items():
        row.append(InlineKeyboardButton(f"{name}", callback_data=f"cur:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🔄 نمایش همهٔ نرخ‌ها", callback_data="cur:all")])
    return InlineKeyboardMarkup(rows)


def gold_karat_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"عیار {k}", callback_data=f"gold:{k}")]
        for k in GOLD_KARATS
    ]
    rows.append([InlineKeyboardButton("🔄 نمایش همهٔ عیارها", callback_data="gold:all")])
    return InlineKeyboardMarkup(rows)


def compare_target_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for code, name in TRACKED_CURRENCIES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"cmp_target:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🥇 طلا (عیار ۲۴)", callback_data="cmp_target:gold")])
    return InlineKeyboardMarkup(rows)


def compare_period_keyboard(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("۲۴ ساعت پیش", callback_data=f"cmp_period:{target}:1"),
                InlineKeyboardButton("۷ روز پیش", callback_data=f"cmp_period:{target}:7"),
            ],
            [
                InlineKeyboardButton("۳۰ روز پیش", callback_data=f"cmp_period:{target}:30"),
                InlineKeyboardButton("۹۰ روز پیش", callback_data=f"cmp_period:{target}:90"),
            ],
        ]
    )
