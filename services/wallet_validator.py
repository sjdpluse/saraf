"""Wallet/network address validation for supported stablecoin networks."""
from __future__ import annotations

import re

_TRC20_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
_EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_SOLANA_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

# Network codes are the API values used by the Mini App. EVM-compatible chains
# intentionally share one address-shape validator; this validates syntax, not
# ownership or whether a given exchange has enabled deposits on that chain.
_NETWORK_PATTERNS = {
    "TRC20": _TRC20_RE,
    "ERC20": _EVM_RE,
    "BEP20": _EVM_RE,
    "ARBITRUM": _EVM_RE,
    "BASE": _EVM_RE,
    "POLYGON": _EVM_RE,
    "AVALANCHE": _EVM_RE,
    "OPTIMISM": _EVM_RE,
    "SOLANA": _SOLANA_RE,
}


class WalletValidationError(ValueError):
    pass


def validate_network(network: str, allowed_networks: list[str]) -> str:
    network = (network or "").strip()
    if not network:
        raise WalletValidationError("شبکه الزامی است.")
    if allowed_networks and network.upper() not in {str(n).upper() for n in allowed_networks}:
        raise WalletValidationError("شبکهٔ انتخاب‌شده پشتیبانی نمی‌شود.")
    return network


def validate_wallet_address(network: str, address: str) -> str:
    address = (address or "").strip()
    if not address:
        raise WalletValidationError("آدرس ولت الزامی است.")
    if len(address) < 8 or len(address) > 128:
        raise WalletValidationError("آدرس ولت نامعتبر است (طول غیرمعمول).")
    if re.search(r"\s", address):
        raise WalletValidationError("آدرس ولت نباید فاصله داشته باشد.")

    code = (network or "").strip().upper()
    pattern = _NETWORK_PATTERNS.get(code)
    if pattern is not None and not pattern.match(address):
        raise WalletValidationError(
            f"آدرس ولت با فرمت استاندارد شبکهٔ {network} مطابقت ندارد."
        )
    return address
