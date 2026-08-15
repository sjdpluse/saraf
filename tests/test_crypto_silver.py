from handlers.crypto import _format_usd
from services import silver_service


def test_format_usd_tiny_price_uses_eight_decimals():
    assert _format_usd(0.0000183) == "0.00001830"


def test_format_usd_sub_dollar_uses_four_decimals():
    assert _format_usd(0.523) == "0.5230"


def test_format_usd_normal_price_uses_two_decimals():
    assert _format_usd(64213.567) == "64,213.57"


def test_silver_breakdown_basic_math():
    breakdown = silver_service.build_silver_breakdown(price_usd_per_oz=30.0, afn_per_usd=70.0)
    assert breakdown["price_afn_per_oz"] == 2100.0
    # 2100 / 31.1034768 ≈ 67.5
    assert 67.0 < breakdown["afn_per_gram"] < 68.0


def test_silver_transaction_buy_adds_making_charge():
    breakdown = silver_service.build_silver_breakdown(price_usd_per_oz=30.0, afn_per_usd=70.0)
    result = silver_service.calculate_silver_transaction(breakdown, grams=10, is_buying=True)
    assert result["final_afn"] > result["base_afn"]
    assert result["adjustment_label"] == "اجرت ساخت"


def test_silver_transaction_sell_deducts():
    breakdown = silver_service.build_silver_breakdown(price_usd_per_oz=30.0, afn_per_usd=70.0)
    result = silver_service.calculate_silver_transaction(breakdown, grams=10, is_buying=False)
    assert result["final_afn"] < result["base_afn"]
    assert result["adjustment_label"] == "کسر صرافی"


def test_silver_transaction_rejects_nonpositive_grams():
    import pytest

    breakdown = silver_service.build_silver_breakdown(price_usd_per_oz=30.0, afn_per_usd=70.0)
    with pytest.raises(ValueError):
        silver_service.calculate_silver_transaction(breakdown, grams=0, is_buying=True)
