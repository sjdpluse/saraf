"""V2 pricing/install layer for remittance_service.

It deliberately patches only the quote function so the proven V1 order state
machine, notifications and payout flow remain unchanged.
"""
from __future__ import annotations

import os
from decimal import Decimal

from services import rate_engine, remittance_service
from services.money import D, quantize_afn, quantize_percent, quantize_rate, quantize_usd, to_float
from services.remittance_asset_registry import normalize_asset, normalize_network
from services.remittance_price_service import get_asset_price_usd
from services.remittance_wallet_config import get_wallet, SUPPORTED


def _limit(name: str, default: str) -> Decimal:
    try:
        return D(os.getenv(name, default))
    except Exception:
        return D(default)


async def quote_v2(*, amount: float, asset: str, network: str, fee_percent: float = 0.0) -> dict:
    selected_asset = normalize_asset(asset)
    selected_network = normalize_network(selected_asset, network)
    amount_d = D(amount)
    if amount_d <= 0:
        raise ValueError("مقدار دارایی باید بیشتر از صفر باشد.")

    asset_price, asset_price_source = await get_asset_price_usd(selected_asset)
    asset_price_d = D(asset_price)
    usd_value = amount_d * asset_price_d

    min_usd = _limit("REMITTANCE_MIN_USD", "10")
    max_usd = _limit("REMITTANCE_MAX_USD", "10000")
    if usd_value < min_usd or usd_value > max_usd:
        raise ValueError(f"ارزش حواله باید بین {min_usd:g} تا {max_usd:g} دالر باشد.")

    wallet = get_wallet(selected_asset, selected_network)
    local = await rate_engine.get_full_quote("usd")
    usd_buy_rate = D(local["saraf_quote"]["buy"])
    fee_pct = max(D(fee_percent), Decimal("0"))
    gross_afn = usd_value * usd_buy_rate
    fee_afn = gross_afn * fee_pct / D(100)
    payout_afn = max(gross_afn - fee_afn, Decimal("0"))

    return {
        "asset": selected_asset,
        "network": selected_network,
        "crypto_amount": to_float(amount_d),
        "asset_price_usd": to_float(asset_price_d),
        "asset_price_source": asset_price_source,
        "usd_value": to_float(quantize_usd(usd_value)),
        "usd_rate": to_float(quantize_rate(usd_buy_rate)),
        "gross_afn": to_float(quantize_afn(gross_afn)),
        "fee_percent": to_float(quantize_percent(fee_pct)),
        "fee_afn": to_float(quantize_afn(fee_afn)),
        "payout_afn": to_float(quantize_afn(payout_afn)),
        "deposit_wallet": wallet,
        "basis": local["saraf_quote"]["basis"],
    }


def install() -> None:
    remittance_service.quote = quote_v2
    remittance_service._deposit_wallet = get_wallet
    remittance_service.SUPPORTED_NETWORKS = SUPPORTED
