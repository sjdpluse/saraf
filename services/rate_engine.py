"""
موتور یکپارچه‌سازی نرخ‌ها.

برای هر ارز سه لایه از اطلاعات را کنار هم قرار می‌دهد:

  ۱) نرخ بازار آزاد جهانی (reference)      -> از currency_service (mid-market بین‌المللی)
  ۲) نرخ واقعی صرافی‌های افغانستان (local)   -> از local_market_service (اسکرپ سرای‌شهزاده/خراسان/بانک)
  ۳) نرخ خرید/فروش خودِ ربات Saraf (quote)   -> نرخ مرجع (ترجیحاً محلی، در غیر این صورت جهانی)
                                                 + حاشیهٔ سود قابل‌تنظیم (spread_service)

اگر اسکرپ محلی برای یک ارز در دسترس نباشد (مثلاً به‌خاطر قطعی سایت یا نبود آن ارز
در جدول سرای‌شهزاده)، موتور به‌صورت خودکار روی نرخ مرجع جهانی + اسپرد سقوط می‌کند
(graceful degradation) و این را در فیلد `basis` مشخص می‌کند.
"""
import logging

from services import currency_service, local_market_service, spread_service

logger = logging.getLogger(__name__)


async def get_full_quote(code: str) -> dict:
    """
    خروجی نمونه:
    {
      "code": "usd",
      "reference_rate": 71.10,           # نرخ بازار آزاد جهانی
      "local": {                          # ممکن است None باشد
          "market": "sarai_shahzada",
          "market_label": "سرای شهزاده (کابل)",
          "buy": 65.90, "sell": 65.95,
      },
      "saraf_quote": {"buy": 65.60, "sell": 66.25, "basis": "local"},
      "spread_percent": 0.6,
    }
    """
    code = code.lower()

    reference_rate = None
    try:
        rates, _source = await currency_service.get_afn_rates()
        reference_rate = rates.get(code)
    except Exception:
        logger.exception("خطا در دریافت نرخ مرجع جهانی برای %s", code)

    local_entry = None
    try:
        local_data = await local_market_service.get_local_market_rates()
        primary = local_market_service.PRIMARY_MARKET
        entry = local_data.get(primary, {}).get(code)
        if entry:
            local_entry = {
                "market": primary,
                "market_label": local_market_service.MARKET_LABELS[primary],
                "buy": entry["buy"],
                "sell": entry["sell"],
            }
    except Exception:
        logger.warning("نرخ محلی برای %s در دسترس نیست؛ استفاده از نرخ مرجع جهانی", code)

    if local_entry is not None:
        basis_rate = (local_entry["buy"] + local_entry["sell"]) / 2
        basis = "local"
    elif reference_rate is not None:
        basis_rate = reference_rate
        basis = "reference"
    else:
        raise RuntimeError(f"هیچ نرخی (نه محلی، نه جهانی) برای {code} در دسترس نیست.")

    saraf_buy, saraf_sell = spread_service.apply_spread(basis_rate, code)
    spread_pct = spread_service.get_spread_percent(code)

    return {
        "code": code,
        "reference_rate": reference_rate,
        "local": local_entry,
        "saraf_quote": {"buy": saraf_buy, "sell": saraf_sell, "basis": basis},
        "spread_percent": spread_pct,
    }


async def get_full_quotes(codes: list[str]) -> dict[str, dict]:
    result = {}
    for code in codes:
        try:
            result[code] = await get_full_quote(code)
        except Exception:
            logger.exception("خطا در ساخت quote کامل برای %s", code)
    return result
