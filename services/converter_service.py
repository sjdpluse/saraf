"""
مبدل جهانی ارز به ارز (Universal Currency Converter) — شبیه ابزار گوگل.

بر خلاف currency_service (که همیشه پایه را افغانی می‌گیرد و فقط ارزهای TRACKED_CURRENCIES
را پوشش می‌دهد)، این سرویس می‌تواند هر ارز پشتیبانی‌شده توسط fawazahmed0/currency-api
(بیش از ۲۰۰ ارز و رمزارز) را مستقیماً به هر ارز دیگری تبدیل کند، با گرفتن آن ارز
به‌عنوان پایهٔ (base) درخواست.

مثال: convert("usd", "pkr", 100) -> مقدار پاکستانی معادل ۱۰۰ دالر

نکتهٔ مهم دربارهٔ تازگی داده:
  jsDelivr (منبع اصلی/CDN) گاهی برای بعضی از ارزهای پایه، نسخهٔ کش‌شدهٔ خیلی
  قدیمی (حتی چند ماه!) برمی‌گرداند، در حالی که خودِ درخواست HTTP موفق (200)
  است و کد قبلی متوجه این قدیمی‌بودن نمی‌شد. برای همین، فیلد "date" هر پاسخ
  را چک می‌کنیم؛ اگر بیش از MAX_DATA_AGE_DAYS روز قدیمی باشد، آن پاسخ را
  نامعتبر در نظر گرفته و به منبع بعدی (پایگاه جایگزین) سقوط می‌کنیم.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

JSDELIVR_BASE_TMPL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json"
PAGES_DEV_BASE_TMPL = "https://latest.currency-api.pages.dev/v1/currencies/{base}.json"
# فال‌بک نهایی: نسخهٔ «تاریخ‌دار» صریح از pages.dev (اگر @latest هم روی هر دو
# CDN به مشکل بخورد، مستقیم تاریخ امروز/دیروز را با نام صریح درخواست می‌کنیم).
DATED_PAGES_DEV_TMPL = "https://{date}.currency-api.pages.dev/v1/currencies/{base}.json"

_TIMEOUT = 10.0
MAX_DATA_AGE_DAYS = 2


def _is_fresh(data: dict) -> bool:
    date_str = data.get("date")
    if not date_str:
        return False
    try:
        data_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    age_days = (datetime.now(timezone.utc) - data_date).days
    return age_days <= MAX_DATA_AGE_DAYS


async def _fetch_json(url: str, *, check_freshness: bool = True) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if check_freshness and not _is_fresh(data):
                logger.warning(
                    "دادهٔ برگشتی از %s قدیمی است (تاریخ=%s)؛ نادیده گرفته و به منبع بعدی سقوط می‌شود.",
                    url, data.get("date"),
                )
                return None
            return data
    except Exception as exc:
        logger.warning("خطا در دریافت %s: %s", url, exc)
        return None


async def _get_rates_for_base(base: str) -> Optional[dict[str, float]]:
    base = base.lower()

    for tmpl in (JSDELIVR_BASE_TMPL, PAGES_DEV_BASE_TMPL):
        data = await _fetch_json(tmpl.format(base=base))
        if data and base in data:
            return data[base]

    # فال‌بک نهایی: تاریخ امروز و دیروز را صریحاً از آینهٔ pages.dev درخواست کن
    # (بدون چک تازگی، چون خودمان تاریخ را در URL مشخص کرده‌ایم).
    now = datetime.now(timezone.utc)
    for days_back in (0, 1):
        date_str = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
        url = DATED_PAGES_DEV_TMPL.format(date=date_str, base=base)
        data = await _fetch_json(url, check_freshness=False)
        if data and base in data:
            return data[base]

    return None


async def convert(from_code: str, to_code: str, amount: float) -> float:
    """مقدار `amount` واحد از from_code را به to_code تبدیل می‌کند."""
    from_code = from_code.lower()
    to_code = to_code.lower()

    if from_code == to_code:
        return round(amount, 6)

    rates = await _get_rates_for_base(from_code)
    if not rates or to_code not in rates:
        raise RuntimeError(
            f"نرخ تبدیل {from_code.upper()} به {to_code.upper()} در دسترس نیست. "
            "لطفاً کد ارزها را بررسی کنید یا کمی بعد دوباره تلاش کنید."
        )

    result = amount * rates[to_code]
    return round(result, 6)


async def get_unit_rate(from_code: str, to_code: str) -> float:
    """۱ واحد from_code معادل چند واحد to_code است."""
    return await convert(from_code, to_code, 1.0)