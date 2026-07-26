"""
مبدل جهانی ارز به ارز (Universal Currency Converter) — شبیه ابزار گوگل.

بر خلاف currency_service (که همیشه پایه را افغانی می‌گیرد و فقط ارزهای TRACKED_CURRENCIES
را پوشش می‌دهد)، این سرویس می‌تواند هر ارز پشتیبانی‌شده توسط fawazahmed0/currency-api
(بیش از ۲۰۰ ارز و رمزارز) را مستقیماً به هر ارز دیگری تبدیل کند، با گرفتن آن ارز
به‌عنوان پایهٔ (base) درخواست.

مثال: convert("usd", "pkr", 100) -> مقدار پاکستانی معادل ۱۰۰ دالر
"""
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

JSDELIVR_BASE_TMPL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json"
PAGES_DEV_BASE_TMPL = "https://latest.currency-api.pages.dev/v1/currencies/{base}.json"

_TIMEOUT = 10.0


async def _fetch_json(url: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("خطا در دریافت %s: %s", url, exc)
        return None


async def _get_rates_for_base(base: str) -> Optional[dict[str, float]]:
    base = base.lower()
    for tmpl in (JSDELIVR_BASE_TMPL, PAGES_DEV_BASE_TMPL):
        data = await _fetch_json(tmpl.format(base=base))
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
