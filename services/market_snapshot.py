"""Public, display-only 24h changes for the miniapp map.

Never used for execution quotes. Source timestamps control freshness; a missing,
invalid or expired percentage is returned as null, including for stablecoins.
"""
import asyncio
import math
import time

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/market", tags=["market"])
_IDS = {
    "USDT": "tether",
    "USDC": "usd-coin",
    "BTC": "bitcoin",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "TON": "the-open-network",
}
_CACHE_TTL = 90
_MAX_AGE = 300
_cache = {"assets": [], "attempted_at": None}
_lock = asyncio.Lock()


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def _normalise(data, now):
    assets = []
    for symbol, coin_id in _IDS.items():
        item = data.get(coin_id, {})
        if not isinstance(item, dict):
            item = {}
        updated = _number(item.get("last_updated_at"))
        change = _number(item.get("usd_24h_change"))
        if updated is None or not -60 <= now - updated <= _MAX_AGE:
            change = None
        assets.append({"symbol": symbol, "change_24h": change, "updated_at": updated})
    return assets


def _snapshot(now):
    assets = []
    for item in _cache["assets"]:
        updated = item["updated_at"]
        fresh = updated is not None and -60 <= now - updated <= _MAX_AGE
        assets.append({**item, "change_24h": item["change_24h"] if fresh else None})
    return {
        "source": "CoinGecko",
        "status": "fresh" if any(x["change_24h"] is not None for x in assets) else "unavailable",
        "assets": assets,
    }


@router.get("/snapshot")
async def get_market_snapshot():
    async with _lock:
        now = time.monotonic()
        attempted = _cache["attempted_at"]
        if attempted is None or now - attempted >= _CACHE_TTL:
            _cache["attempted_at"] = now
            try:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    response = await client.get(
                        "https://api.coingecko.com/api/v3/simple/price",
                        params={
                            "ids": ",".join(_IDS.values()),
                            "vs_currencies": "usd",
                            "include_24hr_change": "true",
                            "include_last_updated_at": "true",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                if isinstance(data, dict):
                    _cache["assets"] = _normalise(data, time.time())
            except (httpx.HTTPError, ValueError):
                pass
        return _snapshot(time.time())
