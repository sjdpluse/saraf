"""
تبدیل تاریخ میلادی به شمسی افغانی (حمل، ثور، جوزا، ...) و نمایش ساعت به وقت افغانستان (UTC+4:30).
این ماژول به هیچ کتابخانهٔ بیرونی نیاز ندارد.
"""
from datetime import datetime, timezone, timedelta

AFGHANISTAN_TZ = timezone(timedelta(hours=4, minutes=30))

PERSIAN_MONTHS = [
    "حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله",
    "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت",
]

_DIGIT_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _to_persian_digits(text: str) -> str:
    return text.translate(_DIGIT_MAP)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """تبدیل تاریخ میلادی به شمسی (الگوریتم استاندارد و آزموده‌شده)."""
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]

    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    for i in range(gm2):
        g_day_no += g_days_in_month[i]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    g_day_no += gd2

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    jm = 12
    jd = j_day_no + 1
    for i in range(11):
        if j_day_no < j_days_in_month[i]:
            jm = i + 1
            jd = j_day_no + 1
            break
        j_day_no -= j_days_in_month[i]

    return jy, jm, jd


def get_afghan_datetime_str() -> str:
    """
    تاریخ و ساعت فعلی را به وقت افغانستان و به شمسی برمی‌گرداند.
    نمونهٔ خروجی: '۱۵ حمل ۱۴۰۴  —  ۱۰:۱۰ ق.ظ'
    """
    now = datetime.now(AFGHANISTAN_TZ)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    month_name = PERSIAN_MONTHS[jm - 1]

    hour12 = now.hour % 12
    if hour12 == 0:
        hour12 = 12
    period = "ق.ظ" if now.hour < 12 else "ب.ظ"

    date_part = f"{jd} {month_name} {jy}"
    time_part = f"{hour12:02d}:{now.minute:02d} {period}"

    return _to_persian_digits(f"{date_part}  —  {time_part}")