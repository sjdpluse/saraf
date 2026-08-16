"""
سرویس نرخ رمزارز — قیمت لحظه‌یی چند رمزارز پرکاربرد.

با زنجیرهٔ منابع پشتیبان (fallback chain) کاملاً رایگان و بدون نیاز به کلید،
دقیقاً هم‌راستا با الگوی currency_service.py و local_market_service.py:

  1) CoinGecko  (https://api.coingecko.com)          — منبع اصلی
  2) Binance    (https://api.binance.com)             — پشتیبان (rate limit بسیار بالاتر)

همچنین نتیجه به مدت CACHE_TTL_SECONDS در حافظه کش می‌شود تا:
  - فشار کمتری به هر دو منبع وارد شود و احتمال خطای 429 (Too Many Requests) کاهش یابد
  - در صورت شکست هر دو منبع، آخرین قیمت معتبر (به‌جای نمایش خطای خام به کاربر) بازگردانده شود

خروجی به دالر است؛ تبدیل به افغانی با همان نرخ دالر/افغانی که برای ارزها و
طلا استفاده می‌شود (services.currency_service) در لایهٔ handler انجام می‌شود،
نه این‌جا — دقیقاً همان تفکیک مسئولیتی که gold_service.py دارد.
"""
import json
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
_TIMEOUT = 10.0
CACHE_TTL_SECONDS = 45  # قیمت رمزارز برای نمایش در ربات نیازی به بروزرسانی ثانیه‌به‌ثانیه ندارد

# نگاشت نماد کوتاه <-> شناسهٔ CoinGecko
CRYPTO_IDS: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "shib": "shiba-inu",
}

# نگاشت نماد کوتاه <-> جفت‌ارز Binance (پشتیبان)
BINANCE_SYMBOLS: dict[str, str] = {
    "btc": "BTCUSDT",
    "eth": "ETHUSDT",
    "sol": "SOLUSDT",
    "bnb": "BNBUSDT",
    "xrp": "XRPUSDT",
    "shib": "SHIBUSDT",
}

CRYPTO_NAMES: dict[str, str] = {
    "btc": "بیت‌کوین",
    "eth": "اتریوم",
    "sol": "سولانا",
    "bnb": "بایننس‌کوین",
    "xrp": "ریپل",
    "shib": "شیبا اینو",
}

_cache: dict = {"data": None, "fetched_at": 0.0}


async def _fetch_from_coingecko() -> dict[str, float]:
    ids = ",".join(CRYPTO_IDS.values())
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(COINGECKO_URL, params={"ids": ids, "vs_currencies": "usd"})
        resp.raise_for_status()
        data = resp.json()

    result: dict[str, float] = {}
    for symbol, coingecko_id in CRYPTO_IDS.items():
        price = data.get(coingecko_id, {}).get("usd")
        if price is not None:
            result[symbol] = float(price)
    return result


async def _fetch_from_binance() -> dict[str, float]:
    symbols_param = json.dumps(list(BINANCE_SYMBOLS.values()))
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(BINANCE_URL, params={"symbols": symbols_param})
        resp.raise_for_status()
        data = resp.json()

    price_by_pair = {item["symbol"]: item["price"] for item in data if "symbol" in item}
    result: dict[str, float] = {}
    for symbol, binance_pair in BINANCE_SYMBOLS.items():
        price = price_by_pair.get(binance_pair)
        if price is not None:
            result[symbol] = float(price)
    return result


async def get_crypto_prices_usd(force_refresh: bool = False) -> tuple[dict[str, float], str]:
    """قیمت لحظه‌یی هر رمزارز پیگیری‌شده را به دالر برمی‌گرداند.

    خروجی: (دیکشنری قیمت‌ها, برچسب منبع)
    برچسب منبع یکی از "cache" / "CoinGecko" / "Binance" / "cache-stale" است؛
    "cache-stale" یعنی هر دو منبع لحظه‌یی شکست خوردند و آخرین قیمت معتبر کش‌شده
    (که ممکن است چند دقیقه قدیمی باشد) بازگردانده شده است.

    در صورتی که هیچ‌گاه قیمتی با موفقیت دریافت نشده باشد (کش خالی) و هر دو
    منبع شکست بخورند، یک استثنا پرتاب می‌شود.
    """
    now = time.monotonic()
    is_fresh = _cache["data"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS

    if not force_refresh and is_fresh:
        return _cache["data"], "cache"

    for fetch_fn, source_name in (
        (_fetch_from_coingecko, "CoinGecko"),
        (_fetch_from_binance, "Binance"),
    ):
        try:
            result = await fetch_fn()
        except Exception as exc:
            logger.warning("خطا در دریافت نرخ رمزارز از %s: %s", source_name, exc)
            continue

        if result:
            _cache["data"] = result
            _cache["fetched_at"] = now
            return result, source_name

    if _cache["data"] is not None:
        logger.info("هر دو منبع نرخ رمزارز شکست خوردند؛ استفاده از کش قدیمی به‌جای نمایش خطا به کاربر.")
        return _cache["data"], "cache-stale"

    raise RuntimeError(
        "در حال حاضر هیچ‌یک از منابع نرخ رمزارز (CoinGecko و Binance) در دسترس نیستند."
    )
