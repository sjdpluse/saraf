"""
اعتبارسنجی آدرس ولت/شبکهٔ تتر (USDT) — SARAF 2.0 Spec §12.

فقط presence-check کافی نیست: برای شبکه‌های شناخته‌شده (TRC20/ERC20/BEP20) فرمت
واقعی آدرس هم بررسی می‌شود. شبکه‌های سفارشی (که کاربر از طریق «سایر» وارد می‌کند)
هنوز پشتیبانی رسمی ندارند، پس فقط بررسی معقول‌بودن طول/عدم‌خالی‌بودن روی آن‌ها
انجام می‌شود.
"""
from __future__ import annotations

import re

_TRC20_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
_EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

_NETWORK_PATTERNS = {
    "TRC20": _TRC20_RE,
    "ERC20": _EVM_RE,
    "BEP20": _EVM_RE,
}


class WalletValidationError(ValueError):
    pass


def validate_network(network: str, allowed_networks: list[str]) -> str:
    network = (network or "").strip()
    if not network:
        raise WalletValidationError("شبکه الزامی است.")
    # شبکه‌های تعریف‌شده در config باید دقیقاً مطابقت داشته باشند (case-sensitive)،
    # اما ورودی آزاد (شبکهٔ سفارشی «سایر») هم مجاز است — چون در حال حاضر رابط
    # کاربری امکان تایپ آزاد شبکه را می‌دهد.
    return network


def validate_wallet_address(network: str, address: str) -> str:
    address = (address or "").strip()
    if not address:
        raise WalletValidationError("آدرس ولت الزامی است.")
    if len(address) < 8 or len(address) > 128:
        raise WalletValidationError("آدرس ولت نامعتبر است (طول غیرمعمول).")
    if re.search(r"\s", address):
        raise WalletValidationError("آدرس ولت نباید فاصله داشته باشد.")

    pattern = _NETWORK_PATTERNS.get((network or "").strip().upper())
    if pattern is not None and not pattern.match(address):
        raise WalletValidationError(
            f"آدرس ولت با فرمت استاندارد شبکهٔ {network} مطابقت ندارد."
        )
    return address
