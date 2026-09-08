import hashlib
import json
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from services.remittance_chain_config import native_decimals, required_confirmations, rpc_url, token_contract

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


@dataclass
class VerificationResult:
    status: str
    confirmations: int = 0
    block_number: Optional[int] = None
    amount: Optional[Decimal] = None
    error: Optional[str] = None
    meta: Optional[dict] = None

    def as_update(self, *, asset: str, network: str) -> dict:
        return {
            "verification_status": self.status,
            "chain_confirmations": max(0, int(self.confirmations)),
            "chain_block_number": self.block_number,
            "chain_verified_amount": str(self.amount) if self.amount is not None else None,
            "chain_verified_asset": asset if self.status == "verified" else None,
            "chain_verified_network": network if self.status == "verified" else None,
            "chain_verification_error": self.error,
            "chain_verification_meta": self.meta or {},
        }


def _post_json(url: str, payload: dict, timeout: int = 12) -> Any:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "saraf-remittance-watcher/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, timeout: int = 12) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "saraf-remittance-watcher/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _rpc(url: str, method: str, params: list) -> Any:
    data = _post_json(url, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data.get("result")


def _norm_evm(address: str) -> str:
    return str(address or "").lower()


def _hex_int(value: Optional[str]) -> int:
    if not value:
        return 0
    return int(value, 16)


def _amount_matches(actual: Decimal, expected: Decimal, decimals: int) -> bool:
    # Chain precision itself is the tolerance; overpayment is accepted, underpayment is not.
    quantum = Decimal(1) / (Decimal(10) ** decimals)
    return actual + quantum >= expected


def verify_evm(order: dict) -> VerificationResult:
    network = order["network"].upper()
    url = rpc_url(network)
    if not url:
        return VerificationResult("unsupported", error="RPC endpoint is not configured")
    tx_hash = order["tx_hash"]
    receipt = _rpc(url, "eth_getTransactionReceipt", [tx_hash])
    if not receipt:
        return VerificationResult("pending", error="Transaction is not mined yet")
    if _hex_int(receipt.get("status")) != 1:
        return VerificationResult("failed", error="Transaction execution failed")
    tx = _rpc(url, "eth_getTransactionByHash", [tx_hash])
    if not tx:
        return VerificationResult("pending", error="Transaction details unavailable")
    latest = _hex_int(_rpc(url, "eth_blockNumber", []))
    block_number = _hex_int(receipt.get("blockNumber"))
    confirmations = max(0, latest - block_number + 1)
    required = required_confirmations(network)
    expected = Decimal(str(order["crypto_amount"]))
    destination = _norm_evm(order["deposit_wallet"])
    asset = order["asset"].upper()

    native = native_decimals(asset, network)
    if native is not None:
        if _norm_evm(tx.get("to")) != destination:
            return VerificationResult("mismatch", confirmations, block_number, error="Destination wallet mismatch")
        actual = Decimal(_hex_int(tx.get("value"))) / (Decimal(10) ** native)
        if not _amount_matches(actual, expected, native):
            return VerificationResult("mismatch", confirmations, block_number, actual, "Transferred amount is below order amount")
        status = "verified" if confirmations >= required else "confirming"
        return VerificationResult(status, confirmations, block_number, actual, meta={"required_confirmations": required})

    token = token_contract(asset, network)
    if not token:
        return VerificationResult("unsupported", confirmations, block_number, error="Token contract is not allow-listed for this network")
    contract, decimals = token
    contract = _norm_evm(contract)
    total_raw = 0
    destination_topic = "0x" + destination.replace("0x", "").rjust(64, "0")
    for log in receipt.get("logs") or []:
        topics = log.get("topics") or []
        if _norm_evm(log.get("address")) != contract or len(topics) < 3:
            continue
        if str(topics[0]).lower() != TRANSFER_TOPIC:
            continue
        if str(topics[2]).lower() != destination_topic.lower():
            continue
        total_raw += _hex_int(log.get("data"))
    actual = Decimal(total_raw) / (Decimal(10) ** decimals)
    if not _amount_matches(actual, expected, decimals):
        return VerificationResult("mismatch", confirmations, block_number, actual, "Matching token transfer to deposit wallet not found or amount is low")
    status = "verified" if confirmations >= required else "confirming"
    return VerificationResult(status, confirmations, block_number, actual, meta={"contract": contract, "required_confirmations": required})


_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58decode_check(value: str) -> bytes:
    n = 0
    for c in value:
        n = n * 58 + _B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(value) - len(value.lstrip("1"))) + raw
    payload, checksum = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != checksum:
        raise ValueError("Invalid base58check")
    return payload


def _tron_hex(address: str) -> str:
    return _b58decode_check(address).hex().lower()


def verify_tron(order: dict) -> VerificationResult:
    url = rpc_url("TRC20").rstrip("/")
    txid = order["tx_hash"]
    # Solidity endpoint only exposes solidified transactions.
    info = _post_json(url + "/walletsolidity/gettransactioninfobyid", {"value": txid})
    if not info or not info.get("id"):
        return VerificationResult("pending", error="Transaction is not solidified yet")
    if info.get("result") not in (None, "SUCCESS"):
        return VerificationResult("failed", error=f"TRON result: {info.get('result')}")
    tx = _post_json(url + "/walletsolidity/gettransactionbyid", {"value": txid})
    contracts = ((tx.get("raw_data") or {}).get("contract") or [])
    if not contracts:
        return VerificationResult("failed", error="TRON transaction has no contract payload")
    c = contracts[0]
    ctype = c.get("type")
    param = ((c.get("parameter") or {}).get("value") or {})
    asset = order["asset"].upper()
    expected = Decimal(str(order["crypto_amount"]))
    destination_hex = _tron_hex(order["deposit_wallet"])

    if asset == "TRX":
        if ctype != "TransferContract":
            return VerificationResult("mismatch", 1, error="Transaction is not a native TRX transfer")
        if str(param.get("to_address", "")).lower() != destination_hex:
            return VerificationResult("mismatch", 1, error="Destination wallet mismatch")
        actual = Decimal(int(param.get("amount", 0))) / Decimal(10**6)
        if not _amount_matches(actual, expected, 6):
            return VerificationResult("mismatch", 1, amount=actual, error="Transferred TRX amount is below order amount")
        return VerificationResult("verified", 1, amount=actual, meta={"solidified": True})

    token = token_contract(asset, "TRC20")
    if not token:
        return VerificationResult("unsupported", 1, error="TRC20 token contract is not allow-listed")
    contract, decimals = token
    if ctype != "TriggerSmartContract":
        return VerificationResult("mismatch", 1, error="Transaction is not a TRC20 contract transfer")
    if str(param.get("contract_address", "")).lower() != _tron_hex(contract):
        return VerificationResult("mismatch", 1, error="Token contract mismatch")
    data = str(param.get("data", "")).lower()
    if not data.startswith("a9059cbb") or len(data) < 8 + 128:
        return VerificationResult("mismatch", 1, error="Transaction is not transfer(address,uint256)")
    dest20 = data[8 + 24:8 + 64]
    expected_dest20 = destination_hex[-40:]
    if dest20 != expected_dest20:
        return VerificationResult("mismatch", 1, error="Destination wallet mismatch")
    amount_raw = int(data[8 + 64:8 + 128], 16)
    actual = Decimal(amount_raw) / (Decimal(10) ** decimals)
    if not _amount_matches(actual, expected, decimals):
        return VerificationResult("mismatch", 1, amount=actual, error="Transferred token amount is below order amount")
    return VerificationResult("verified", 1, amount=actual, meta={"contract": contract, "solidified": True})


def verify_solana(order: dict) -> VerificationResult:
    url = rpc_url("SOL")
    sig = order["tx_hash"]
    tx = _rpc(url, "getTransaction", [sig, {"encoding": "jsonParsed", "commitment": "finalized", "maxSupportedTransactionVersion": 0}])
    if not tx:
        return VerificationResult("pending", error="Transaction is not finalized yet")
    meta = tx.get("meta") or {}
    if meta.get("err") is not None:
        return VerificationResult("failed", error="Solana transaction failed")
    asset = order["asset"].upper()
    destination = order["deposit_wallet"]
    expected = Decimal(str(order["crypto_amount"]))
    slot = int(tx.get("slot") or 0)

    if asset == "SOL":
        msg = ((tx.get("transaction") or {}).get("message") or {})
        keys = msg.get("accountKeys") or []
        key_values = [k.get("pubkey") if isinstance(k, dict) else k for k in keys]
        try:
            idx = key_values.index(destination)
        except ValueError:
            return VerificationResult("mismatch", 1, slot, error="Destination wallet not present in transaction")
        pre = meta.get("preBalances") or []
        post = meta.get("postBalances") or []
        if idx >= len(pre) or idx >= len(post):
            return VerificationResult("failed", 1, slot, error="Balance metadata missing")
        actual = Decimal(max(0, post[idx] - pre[idx])) / Decimal(10**9)
        if not _amount_matches(actual, expected, 9):
            return VerificationResult("mismatch", 1, slot, actual, "Received SOL amount is below order amount")
        return VerificationResult("verified", 1, slot, actual, meta={"commitment": "finalized"})

    token = token_contract(asset, "SOL")
    if not token:
        return VerificationResult("unsupported", 1, slot, error="SPL token mint is not allow-listed")
    mint, decimals = token
    pre_map = {}
    for bal in meta.get("preTokenBalances") or []:
        if bal.get("mint") == mint and bal.get("owner") == destination:
            pre_map[int(bal["accountIndex"])] = Decimal(str((bal.get("uiTokenAmount") or {}).get("uiAmountString") or "0"))
    received = Decimal("0")
    for bal in meta.get("postTokenBalances") or []:
        if bal.get("mint") != mint or bal.get("owner") != destination:
            continue
        idx = int(bal["accountIndex"])
        after = Decimal(str((bal.get("uiTokenAmount") or {}).get("uiAmountString") or "0"))
        before = pre_map.get(idx, Decimal("0"))
        if after > before:
            received += after - before
    if not _amount_matches(received, expected, decimals):
        return VerificationResult("mismatch", 1, slot, received, "Matching SPL transfer to deposit wallet not found or amount is low")
    return VerificationResult("verified", 1, slot, received, meta={"mint": mint, "commitment": "finalized"})


def verify_bitcoin(order: dict) -> VerificationResult:
    base = rpc_url("BITCOIN").rstrip("/")
    txid = order["tx_hash"]
    tx = _get_json(base + "/tx/" + txid)
    status = tx.get("status") or {}
    if not status.get("confirmed"):
        return VerificationResult("pending", error="Bitcoin transaction is not confirmed")
    tip = int(_get_json(base + "/blocks/tip/height"))
    block_height = int(status["block_height"])
    confirmations = max(0, tip - block_height + 1)
    expected = Decimal(str(order["crypto_amount"]))
    destination = order["deposit_wallet"]
    sats = sum(int(v.get("value", 0)) for v in tx.get("vout") or [] if (v.get("scriptpubkey_address") == destination))
    actual = Decimal(sats) / Decimal(10**8)
    if not _amount_matches(actual, expected, 8):
        return VerificationResult("mismatch", confirmations, block_height, actual, "BTC output to deposit wallet is below order amount")
    required = required_confirmations("BITCOIN")
    state = "verified" if confirmations >= required else "confirming"
    return VerificationResult(state, confirmations, block_height, actual, meta={"required_confirmations": required})


def verify_order(order: dict) -> VerificationResult:
    network = str(order.get("network") or "").upper()
    if not order.get("tx_hash"):
        return VerificationResult("not_submitted")
    try:
        if network in {"ERC20", "BEP20", "ARBITRUM", "BASE", "POLYGON"}:
            return verify_evm(order)
        if network == "TRC20":
            return verify_tron(order)
        if network == "SOL":
            return verify_solana(order)
        if network == "BITCOIN":
            return verify_bitcoin(order)
        return VerificationResult("unsupported", error=f"No verifier for network {network}")
    except Exception as exc:
        return VerificationResult("pending", error=f"Verifier error: {type(exc).__name__}: {exc}")
