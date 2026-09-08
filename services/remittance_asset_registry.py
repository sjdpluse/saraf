"""Canonical asset/network registry for international remittances."""

ASSETS = {
    "USDT": {"name_fa": "تتر", "networks": ("BEP20", "TRC20", "ERC20", "ARBITRUM", "BASE", "POLYGON", "SOL")},
    "USDC": {"name_fa": "یو‌اس‌دی کوین", "networks": ("BEP20", "ERC20", "ARBITRUM", "BASE", "POLYGON", "SOL")},
    "DAI": {"name_fa": "دای", "networks": ("ERC20", "ARBITRUM", "BASE", "POLYGON")},
    "TUSD": {"name_fa": "ترو یو‌اس‌دی", "networks": ("BEP20", "ERC20", "ARBITRUM", "POLYGON")},
    "TRX": {"name_fa": "ترون", "networks": ("TRC20",)},
    "BNB": {"name_fa": "بی‌ان‌بی", "networks": ("BEP20",)},
    "ETH": {"name_fa": "اتریوم", "networks": ("ERC20", "ARBITRUM", "BASE")},
    "SOL": {"name_fa": "سولانا", "networks": ("SOL",)},
    "WBTC": {"name_fa": "رپد بیت‌کوین", "networks": ("ERC20", "ARBITRUM", "POLYGON")},
    "PAXG": {"name_fa": "پکس گلد", "networks": ("ERC20",)},
    "PYUSD": {"name_fa": "پی‌پل یو‌اس‌دی", "networks": ("ERC20",)},
    "WETH": {"name_fa": "رپد اتریوم", "networks": ("BEP20", "ERC20")},
    "BTCB": {"name_fa": "بیت‌کوین BEP20", "networks": ("BEP20",)},
    "POL": {"name_fa": "پالیگان", "networks": ("POLYGON",)},
    "BTC": {"name_fa": "بیت‌کوین", "networks": ("BITCOIN",)},
}

NETWORK_LABELS = {
    "BEP20": "BNB Smart Chain (BEP20)",
    "TRC20": "Tron (TRC20)",
    "ERC20": "Ethereum (ERC20)",
    "ARBITRUM": "Arbitrum One",
    "BASE": "Base",
    "POLYGON": "Polygon",
    "SOL": "Solana",
    "BITCOIN": "Bitcoin",
}

_STABLECOINS = {"USDT", "USDC", "DAI", "TUSD", "PYUSD"}
_PRICE_ALIASES = {"WETH": "ETH", "WBTC": "BTC", "BTCB": "BTC"}


def normalize_asset(asset: str | None) -> str:
    value = str(asset or "").strip().upper()
    if value not in ASSETS:
        raise ValueError("دارایی انتخاب‌شده برای حواله پشتیبانی نمی‌شود.")
    return value


def normalize_network(asset: str, network: str | None) -> str:
    selected_asset = normalize_asset(asset)
    value = str(network or "").strip().upper()
    aliases = {"SOLANA": "SOL", "BTC": "BITCOIN"}
    value = aliases.get(value, value)
    if value not in ASSETS[selected_asset]["networks"]:
        raise ValueError("شبکهٔ انتخاب‌شده برای این دارایی پشتیبانی نمی‌شود.")
    return value


def asset_name_fa(asset: str) -> str:
    return ASSETS[normalize_asset(asset)]["name_fa"]


def is_stablecoin(asset: str) -> bool:
    return normalize_asset(asset) in _STABLECOINS


def pricing_asset(asset: str) -> str:
    selected = normalize_asset(asset)
    return _PRICE_ALIASES.get(selected, selected)


def network_label(network: str) -> str:
    code = str(network or "").strip().upper()
    return NETWORK_LABELS.get(code, code)
