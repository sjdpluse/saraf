from decimal import Decimal

from services import money


def test_D_from_float_str_roundtrip_no_binary_error():
    # Decimal(str(0.1)) باید دقیقاً 0.1 باشد؛ Decimal(0.1) مستقیم چنین نیست.
    assert money.D(0.1) == Decimal("0.1")
    assert money.D("10.5") == Decimal("10.5")
    assert money.D(10) == Decimal("10")


def test_quantize_afn_rounds_half_up():
    assert money.quantize_afn(Decimal("100.05")) == Decimal("100.1")
    assert money.quantize_afn(Decimal("100.04")) == Decimal("100.0")


def test_money_equal_tolerant_of_float_noise():
    assert money.money_equal(10.1, Decimal("10.1"))
    assert money.money_equal(0.1 + 0.2, 0.3)  # این با float خام می‌شکند، با Decimal نه
    assert not money.money_equal(10, 10.5)


def test_quantize_usd_two_decimals():
    assert money.quantize_usd(Decimal("12.345")) == Decimal("12.35")  # HALF_UP


def test_D_rejects_none():
    import pytest

    with pytest.raises(money.MoneyError):
        money.D(None)
