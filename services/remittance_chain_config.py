import json
import os

# Public mainnet RPC defaults. Production can override any entry with
# REMITTANCE_RPC_<NETWORK>. Commercial/private RPCs are recommended at scale.
RPC_DEFAULTS = {
    "ERC20": "https://ethereum-rpc.publicnode.com",
    "BEP20": "https://bsc-rpc.publicnode.com",
    "ARBITRUM": "https://arbitrum-one-rpc.publicnode.com",
    "BASE": "https://mainnet.base.org",
    "POLYGON": "https://polygon-bor-rpc.publicnode.com",
    "SOL": "https://api.mainnet-beta.solana.com",
    "TRC20": "https://api.trongrid.io",
    "BITCOIN": "https://blockstream.info/api",
}

# Minimum confirmations before cash payout can become ready.
CONFIRMATIONS_DEFAULT = {
    "ERC20": 12,
    "BEP20": 15,
    "ARBITRUM": 20,
    "BASE": 20,
    "POLYGON": 64,
    "SOL": 1,       # finalized commitment is requested from RPC
    "TRC20": 1,     # solidity endpoint is used (solidified transaction)
    "BITCOIN": 2,
}

# Contract/mint identifiers are deliberately allow-listed. Never infer a token
# from its symbol. Entries below are canonical issuer addresses verified from
# issuer documentation. Extra mappings can be supplied through
# REMITTANCE_TOKEN_CONTRACTS_JSON.
TOKEN_CONTRACTS = {
    ("USDC", "ERC20"): ("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 6),
    ("USDC", "ARBITRUM"): ("0xaf88d065e77c8cc2239327c5edb3a432268e5831", 6),
    ("USDC", "BASE"): ("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", 6),
    ("USDC", "POLYGON"): ("0x3c499c542cef5e3811e1192ce70d8cc03d5c3359", 6),
    ("USDC", "SOL"): ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 6),
    ("USDT", "ERC20"): ("0xdac17f958d2ee523a2206206994597c13d831ec7", 6),
    ("USDT", "TRC20"): ("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", 6),
    ("USDT", "SOL"): ("Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", 6),
    ("PYUSD", "ERC20"): ("0x6c3ea9036406852006290770bedfcaba0e23a0e8", 6),
}

NATIVE_ASSETS = {
    ("ETH", "ERC20"): 18,
    ("ETH", "ARBITRUM"): 18,
    ("ETH", "BASE"): 18,
    ("BNB", "BEP20"): 18,
    ("POL", "POLYGON"): 18,
    ("SOL", "SOL"): 9,
    ("TRX", "TRC20"): 6,
    ("BTC", "BITCOIN"): 8,
}


def rpc_url(network: str) -> str:
    network = str(network).upper()
    return os.getenv(f"REMITTANCE_RPC_{network}", RPC_DEFAULTS.get(network, "")).strip()


def required_confirmations(network: str) -> int:
    network = str(network).upper()
    env = os.getenv(f"REMITTANCE_CONFIRMATIONS_{network}")
    if env:
        try:
            return max(1, int(env))
        except ValueError:
            pass
    return CONFIRMATIONS_DEFAULT.get(network, 1)


def _extra_contracts():
    raw = os.getenv("REMITTANCE_TOKEN_CONTRACTS_JSON", "").strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    out = {}
    for asset, networks in parsed.items():
        for network, meta in networks.items():
            if isinstance(meta, str):
                out[(asset.upper(), network.upper())] = (meta, 18)
            else:
                out[(asset.upper(), network.upper())] = (str(meta["address"]), int(meta["decimals"]))
    return out


def token_contract(asset: str, network: str):
    key = (str(asset).upper(), str(network).upper())
    merged = dict(TOKEN_CONTRACTS)
    try:
        merged.update(_extra_contracts())
    except Exception:
        # Invalid operator config must never broaden verification.
        pass
    return merged.get(key)


def native_decimals(asset: str, network: str):
    return NATIVE_ASSETS.get((str(asset).upper(), str(network).upper()))
