import os

from config import USDT_DEPOSIT_WALLETS

SUPPORTED = {
    "USDT": ("TRC20", "BEP20", "ERC20"),
    "USDC": ("BEP20", "ERC20"),
}


def get_wallet(asset: str, network: str) -> str:
    asset = str(asset or "").upper()
    network = str(network or "").upper()
    if asset not in SUPPORTED or network not in SUPPORTED[asset]:
        raise ValueError("دارایی یا شبکهٔ حواله پشتیبانی نمی‌شود.")

    env_key = f"REMITTANCE_{asset}_{network}_WALLET"
    wallet = os.getenv(env_key, "").strip()
    if not wallet and asset == "USDT":
        wallet = str((USDT_DEPOSIT_WALLETS or {}).get(network) or "").strip()
    if not wallet:
        raise ValueError(f"آدرس دریافت {asset} روی شبکهٔ {network} هنوز تنظیم نشده است.")
    return wallet


def configured_assets() -> list[dict]:
    items = []
    for asset, networks in SUPPORTED.items():
        available = []
        for network in networks:
            try:
                get_wallet(asset, network)
                available.append(network)
            except ValueError:
                pass
        if available:
            items.append({"asset": asset, "networks": available})
    return items
