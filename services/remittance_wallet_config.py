import json
import os

from config import USDT_DEPOSIT_WALLETS
from services.remittance_asset_registry import ASSETS, normalize_asset, normalize_network

SUPPORTED = {asset: tuple(meta["networks"]) for asset, meta in ASSETS.items()}
LEGACY_ASSETS = {"USDT", "USDC"}


def v2_enabled() -> bool:
    return os.getenv("REMITTANCE_V2_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _json_wallets() -> dict:
    raw = os.getenv("REMITTANCE_WALLETS_JSON", "{}").strip() or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("REMITTANCE_WALLETS_JSON معتبر نیست.") from exc
    return data if isinstance(data, dict) else {}


def assert_asset_enabled(asset: str) -> str:
    selected = normalize_asset(asset)
    if selected not in LEGACY_ASSETS and not v2_enabled():
        raise ValueError("دارایی‌های جدید حواله هنوز فعال نشده‌اند؛ ابتدا migration نسخه V2 را اجرا کنید.")
    return selected


def get_wallet(asset: str, network: str) -> str:
    selected_asset = assert_asset_enabled(asset)
    selected_network = normalize_network(selected_asset, network)

    wallet = str(_json_wallets().get(selected_asset, {}).get(selected_network) or "").strip()
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
        if asset not in LEGACY_ASSETS and not v2_enabled():
            continue
        available = []
        for network in networks:
            try:
                get_wallet(asset, network)
                available.append(network)
            except ValueError:
                pass
        if available:
            items.append({
                "asset": asset,
                "name_fa": ASSETS[asset]["name_fa"],
                "networks": available,
            })
    return items
