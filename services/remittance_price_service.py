"""USD pricing for assets accepted by the remittance service.

CoinGecko is the canonical source for multi-asset settlement. Wrapped/network
representations share the economic price of their underlying asset.
"""
from __future__ import annotations

import time
import httpx

from services.remittance_asset_registry import normalize_asset, pricing_asset

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
_TIMEOUT = 10.0
_CACHE_TTL = 30

COINGECKO_IDS = {
    "USDT": "tether",
    "USDC": "usd-coin",
    "DAI": "dai",
    "TUSD": "true-usd",
    "TRX": "tron",
    "BNB": "binancecoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BTC": "bitcoin",
    "PAXG": "pax-gold",
    "PYUSD": "paypal-usd",
    "POL": "polygon-ecosystem-token",
}

_cache: dict[str, tuple[float, float]] = {}


async def get_asset_price_usd(asset: str) -> tuple[float, str]:
    selected = pricing_asset(normalize_asset(asset))
    now = time.monotonic()
    cached = _cache.get(selected)
    if cached and now - cached[1] < _CACHE_TTL:
        return cached[0], "CoinGecko-cache"

    coin_id = COINGECKO_IDS.get(selected)
    if not coin_id:
        raise ValueError("منبع نرخ این دارایی برای حواله تنظیم نشده است.")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(COINGECKO_URL, params={"ids": coin_id, "vs_currencies": "usd"})
            response.raise_for_status()
            value = response.json().get(coin_id, {}).get("usd")
        price = float(value)
        if price <= 0:
            raise ValueError("invalid price")
        _cache[selected] = (price, now)
        return price, "CoinGecko"
    except Exception as exc:
        if cached:
            return cached[0], "CoinGecko-cache-stale"
        raise RuntimeError(f"قیمت دلاری {selected} در حال حاضر در دسترس نیست.") from exc
