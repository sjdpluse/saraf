import pytest

from services import wallet_validator as wv


def test_valid_trc20_address():
    addr = wv.validate_wallet_address("TRC20", "TXYZabc123XYZabc123XYZabc123XYZabc")
    assert addr.startswith("T")


def test_invalid_trc20_address_wrong_prefix():
    with pytest.raises(wv.WalletValidationError):
        wv.validate_wallet_address("TRC20", "0xabc123")


def test_valid_erc20_address():
    wv.validate_wallet_address("ERC20", "0x" + "a" * 40)


def test_invalid_erc20_address_wrong_length():
    with pytest.raises(wv.WalletValidationError):
        wv.validate_wallet_address("ERC20", "0x" + "a" * 10)


def test_empty_address_rejected():
    with pytest.raises(wv.WalletValidationError):
        wv.validate_wallet_address("TRC20", "")


def test_address_with_whitespace_rejected():
    with pytest.raises(wv.WalletValidationError):
        wv.validate_wallet_address("ERC20", "0x" + "a" * 20 + " " + "a" * 19)


def test_unknown_custom_network_only_sanity_checked():
    # شبکهٔ سفارشی («سایر») فقط presence + طول منطقی چک می‌شود، نه فرمت دقیق
    addr = wv.validate_wallet_address("SOMECHAIN", "some-valid-looking-address-123")
    assert addr == "some-valid-looking-address-123"
