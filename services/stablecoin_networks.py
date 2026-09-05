"""Asset-specific transfer network policy for USDT and USDC.

The goal is to prevent a UI selection from implying that every stablecoin exists
on every chain. USDC entries below are limited to native/current Circle-supported
networks that Saraf intentionally exposes in the Mini App. Sell-side availability
is stricter: a network is offered only when a Saraf deposit address is configured.
"""
from __future__ import annotations

from typing import Optional

from config import USDT_DEPOSIT_WALLETS, USDC_DEPOSIT_WALLETS
from services import usdt_service

# User-facing, deliberately curated network set. Codes are stable API values;
# labels are presentation metadata.
_NETWORKS = {
    "USDT": [
        {"code": "TRC20", "label": "Tron (TRC20)", "family": "tron"},
        {"code": "ERC20", "label": "Ethereum (ERC20)", "family": "evm"},
        {"code": "BEP20", "label": "BNB Smart Chain (BEP20)", "family": "evm"},
    ],
    "USDC": [
        {"code": "ERC20", "label": "Ethereum", "family": "evm"},
        {"code": "ARBITRUM", "label": "Arbitrum One", "family": "evm"},
        {"code": "BASE", "label": "Base", "family": "evm"},
        {"code": "POLYGON", "label": "Polygon PoS", "family": "evm"},
        {"code": "SOLANA", "label": "Solana", "family": "solana"},
        {"code": "AVALANCHE", "label": "Avalanche C-Chain", "family": "evm"},
        {"code": "OPTIMISM", "label": "OP Mainnet", "family": "evm"},
    ],
}


def _asset(asset: Optional[str]) -> str:
    return usdt_service.normalize_asset(asset)


def get_buy_networks(asset: Optional[str]) -> list[dict]:
    """Networks Saraf may send the selected asset to for a buy order."""
    return [dict(item) for item in _NETWORKS[_asset(asset)]]


def get_supported_network_codes(asset: Optional[str]) -> set[str]:
    return {item["code"] for item in _NETWORKS[_asset(asset)]}


def get_deposit_wallets(asset: Optional[str]) -> dict[str, str]:
    selected = _asset(asset)
    raw = USDT_DEPOSIT_WALLETS if selected == "USDT" else USDC_DEPOSIT_WALLETS
    allowed = get_supported_network_codes(selected)
    return {
        str(network).strip().upper(): str(address).strip()
        for network, address in (raw or {}).items()
        if str(network).strip().upper() in allowed and str(address).strip()
    }


def get_sell_networks(asset: Optional[str]) -> list[dict]:
    """Only networks with an explicitly configured Saraf deposit wallet."""
    selected = _asset(asset)
    wallets = get_deposit_wallets(selected)
    return [dict(item) for item in _NETWORKS[selected] if item["code"] in wallets]


def get_deposit_wallet(asset: Optional[str], network: Optional[str]) -> Optional[str]:
    if not network:
        return None
    return get_deposit_wallets(asset).get(str(network).strip().upper())


def validate_network(asset: Optional[str], network: str, *, direction: str = "buy") -> str:
    selected = _asset(asset)
    code = str(network or "").strip().upper()
    if not code:
        raise ValueError("شبکه الزامی است.")

    supported = get_supported_network_codes(selected)
    if code not in supported:
        raise ValueError(f"شبکهٔ {network} برای {selected} در صراف پشتیبانی نمی‌شود.")

    if direction == "sell" and not get_deposit_wallet(selected, code):
        raise ValueError(
            f"برای فروش {selected} روی شبکهٔ {code} هنوز آدرس دریافت صراف تنظیم نشده است."
        )
    return code


def public_config() -> dict:
    out = {}
    for asset in ("USDT", "USDC"):
        out[asset] = {
            "buy_networks": get_buy_networks(asset),
            "sell_networks": get_sell_networks(asset),
        }
    return out
