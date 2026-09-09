"""Canonical asset/network registry for international remittances."""

_ICON_BASE = "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color"


def _icon(symbol: str) -> str:
    return f"{_ICON_BASE}/{symbol.lower()}.png"


ASSETS = {
    "USDT": {
        "name": "Tether USD",
        "logo_url": "https://i.postimg.cc/250WhXsF/tether.png",
        "networks": ("BEP20", "TRC20", "ERC20", "ARBITRUM", "BASE", "POLYGON", "SOL"),
    },
    "USDC": {
        "name": "USD Coin",
        "logo_url": "https://i.postimg.cc/0QndtT7N/usd-coin-usdc-logo.jpg",
        "networks": ("BEP20", "ERC20", "ARBITRUM", "BASE", "POLYGON", "SOL"),
    },
    "DAI": {"name": "Dai", "logo_url": _icon("DAI"), "networks": ("ERC20", "ARBITRUM", "BASE", "POLYGON")},
    "TUSD": {"name": "TrueUSD", "logo_url": _icon("TUSD"), "networks": ("BEP20", "ERC20", "ARBITRUM", "POLYGON")},
    "TRX": {"name": "TRON", "logo_url": _icon("TRX"), "networks": ("TRC20",)},
    "BNB": {"name": "BNB", "logo_url": _icon("BNB"), "networks": ("BEP20",)},
    "ETH": {"name": "Ethereum", "logo_url": _icon("ETH"), "networks": ("ERC20", "ARBITRUM", "BASE")},
    "SOL": {"name": "Solana", "logo_url": _icon("SOL"), "networks": ("SOL",)},
    "WBTC": {"name": "Wrapped Bitcoin", "logo_url": _icon("WBTC"), "networks": ("ERC20", "ARBITRUM", "POLYGON")},
    "PAXG": {"name": "PAX Gold", "logo_url": _icon("PAXG"), "networks": ("ERC20",)},
    "PYUSD": {"name": "PayPal USD", "logo_url": _icon("PYUSD"), "networks": ("ERC20",)},
    "WETH": {"name": "Wrapped Ether", "logo_url": _icon("WETH"), "networks": ("BEP20", "ERC20")},
    "BTCB": {"name": "Bitcoin BEP20", "logo_url": _icon("BTCB"), "networks": ("BEP20",)},
    "POL": {"name": "Polygon Ecosystem Token", "logo_url": _icon("POL"), "networks": ("POLYGON",)},
    "BTC": {"name": "Bitcoin", "logo_url": _icon("BTC"), "networks": ("BITCOIN",)},
}

NETWORK_LABELS = {
    "BEP20": "BNB Smart Chain (BSC)",
    "TRC20": "Tron (TRX)",
    "ERC20": "Ethereum (ETH)",
    "ARBITRUM": "Arbitrum One (ARB)",
    "BASE": "Base",
    "POLYGON": "Polygon (POL)",
    "SOL": "Solana (SOL)",
    "BITCOIN": "Bitcoin (BTC)",
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


def asset_name(asset: str) -> str:
    return ASSETS[normalize_asset(asset)]["name"]


def asset_logo(asset: str) -> str:
    return ASSETS[normalize_asset(asset)]["logo_url"]


def is_stablecoin(asset: str) -> bool:
    return normalize_asset(asset) in _STABLECOINS


def pricing_asset(asset: str) -> str:
    selected = normalize_asset(asset)
    return _PRICE_ALIASES.get(selected, selected)


def network_label(network: str) -> str:
    code = str(network or "").strip().upper()
    return NETWORK_LABELS.get(code, code)
