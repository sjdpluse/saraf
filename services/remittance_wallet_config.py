import json
import os

from config import USDT_DEPOSIT_WALLETS
from services.remittance_asset_registry import ASSETS, network_label, normalize_asset, normalize_network

SUPPORTED = {asset: tuple(meta["networks"]) for asset, meta in ASSETS.items()}


def _json_wallets() -> dict:
    raw = os.getenv("REMITTANCE_WALLETS_JSON", "{}").strip() or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("REMITTANCE_WALLETS_JSON معتبر نیست.") from exc
    return data if isinstance(data, dict) else {}


def get_wallet(asset: str, network: str) -> str:
    selected_asset = normalize_asset(asset)
    selected_network = normalize_network(selected_asset, network)

    wallet = str(_json_wallets().get(selected_asset, {}).get(selected_network) or "").strip()

    # Backward compatibility with V1 variables.
    if not wallet:
        env_key = f"REMITTANCE_{selected_asset}_{selected_network}_WALLET"
        wallet = os.getenv(env_key, "").strip()
    if not wallet and selected_asset == "USDT":
        wallet = str((USDT_DEPOSIT_WALLETS or {}).get(selected_network) or "").strip()

    if not wallet:
        raise ValueError(f"آدرس دریافت {selected_asset} روی شبکهٔ {selected_network} هنوز تنظیم نشده است.")
    return wallet


def configured_assets() -> list[dict]:
    items = []
    for asset, networks in SUPPORTED.items():
        available = []
        for network in networks:
            try:
                get_wallet(asset, network)
                available.append({"code": network, "label": network_label(network)})
            except ValueError:
                pass
        if available:
            items.append({
                "asset": asset,
                "name_fa": ASSETS[asset]["name_fa"],
                "networks": available,
            })
    return items
