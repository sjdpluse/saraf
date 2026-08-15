"""
سرویس نرخ رمزارز — قیمت لحظه‌یی چند رمزارز پرکاربرد از CoinGecko
(https://api.coingecko.com — رایگان، بدون نیاز به کلید API برای این حجم کم درخواست).

خروجی به دالر است؛ تبدیل به افغانی با همان نرخ دالر/افغانی که برای ارزها و
طلا استفاده می‌شود (services.currency_service) در لایهٔ handler انجام می‌شود،
نه این‌جا — دقیقاً همان تفکیک مسئولیتی که gold_service.py دارد.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
_TIMEOUT = 10.0

# نگاشت نماد کوتاه <-> شناسهٔ CoinGecko
CRYPTO_IDS: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "shib": "shiba-inu",
}

CRYPTO_NAMES: dict[str, str] = {
    "btc": "بیت‌کوین",
    "eth": "اتریوم",
    "sol": "سولانا",
    "bnb": "بایننس‌کوین",
    "xrp": "ریپل",
    "shib": "شیبا اینو",
}


async def get_crypto_prices_usd() -> dict[str, float]:
    """قیمت لحظه‌یی هر رمزارز پیگیری‌شده را به دالر، در یک درخواست، برمی‌گرداند.
    خروجی نمونه: {"btc": 64213.5, "eth": 3450.2, ...}"""
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

    if not result:
        raise RuntimeError("قیمت هیچ رمزارزی از CoinGecko دریافت نشد.")
    return result
