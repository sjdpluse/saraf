"""
موتور ارزیابی ریسک معاملات تتر (Risk Engine).

اصل طراحی: هیچ عدد یا تصمیمی «جعبهٔ سیاه» نیست — هر سطح ریسک همراه با دلایل دقیق
برمی‌گردد تا در پیام اطلاع‌رسانی به ادمین نمایش داده شود و قابل‌بررسی/تغییر باشد.

سه سطح:
  low    -> کاربر تایید/معتمد + سابقهٔ خوب + مبلغ معمولی        => پردازش عادی
  medium -> کاربر تازه یا هویت هنوز تایید نشده + مبلغ بالا      => بررسی دستی ادمین
  high   -> سابقهٔ لغو/رفتار مشکوک، یا کاربر محدودشده           => توقف و بررسی ویژه

آستانه‌های عددی همه از config.py خوانده می‌شوند تا صاحب کسب‌وکار بتواند بدون
دست‌زدن به منطق، فقط با تغییر عدد در متغیرهای محیطی رفتار سیستم را تنظیم کند.
"""
from config import (
    USDT_RISK_HIGH_AMOUNT_THRESHOLD,
    USDT_RISK_NEW_USER_ORDER_THRESHOLD,
    USDT_RISK_CANCEL_COUNT_THRESHOLD,
    USDT_RISK_PAYMENT_CHANGE_THRESHOLD,
)

RISK_LABELS = {
    "low": "🟢 ریسک پایین",
    "medium": "🟡 ریسک متوسط — نیاز به بررسی دستی",
    "high": "🔴 ریسک بالا — توقف و بررسی ویژه",
}


def assess_risk(profile: dict | None, amount: float) -> tuple[str, list[str]]:
    """
    profile: خروجی supabase_service.get_user_profile(chat_id) یا None (کاربر هنوز
             پروفایلی ندارد — حالتی که عملاً نباید پیش بیاید چون KYC اجباری است،
             ولی برای اطمینان پوشش داده می‌شود).
    برمی‌گرداند: (risk_level, reasons)
    """
    if not profile:
        return "high", ["پروفایل احراز هویت یافت نشد"]

    kyc_status = profile.get("kyc_status", "pending")
    successful = profile.get("successful_orders") or 0
    cancelled = profile.get("cancelled_orders") or 0
    payment_changes = profile.get("payment_info_change_count") or 0

    # --- سطح بالا: کاربر محدودشده یا الگوی رفتار مشکوک ---
    if kyc_status == "restricted":
        reason = profile.get("restricted_reason") or "کاربر توسط ادمین محدود شده است"
        return "high", [reason]

    high_reasons = []
    if cancelled >= USDT_RISK_CANCEL_COUNT_THRESHOLD:
        high_reasons.append(f"{cancelled} معاملهٔ لغوشده/مشکوک در سابقه")
    if payment_changes >= USDT_RISK_PAYMENT_CHANGE_THRESHOLD:
        high_reasons.append(f"{payment_changes} بار تغییر اطلاعات پرداخت")
    if high_reasons:
        return "high", high_reasons

    # --- سطح متوسط: هویت هنوز تایید نشده، یا کاربر تازه + مبلغ بالا ---
    medium_reasons = []
    if kyc_status == "pending":
        medium_reasons.append("هویت هنوز توسط ادمین تایید نشده")

    is_new_user = successful < USDT_RISK_NEW_USER_ORDER_THRESHOLD
    is_high_amount = amount >= USDT_RISK_HIGH_AMOUNT_THRESHOLD
    if is_new_user and is_high_amount:
        medium_reasons.append(
            f"کاربر کم‌تجربه ({successful} معاملهٔ موفق) + مبلغ بالا ({amount:g} USDT)"
        )

    if medium_reasons:
        return "medium", medium_reasons

    return "low", []


def risk_label(level: str) -> str:
    return RISK_LABELS.get(level, level)
