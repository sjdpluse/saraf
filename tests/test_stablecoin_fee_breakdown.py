from services import usdt_order_service, usdt_service


def test_small_buy_fee_and_profit_breakdown():
    pricing = usdt_service.build_buy_pricing(14, 64.25)

    assert pricing["customer_payable_usd"] == 15.6
    assert pricing["supplier_profit_usd"] == 1.0
    assert pricing["saraf_profit_usd"] == 0.6
    assert pricing["supplier_payout_usd"] == 15.0
    assert pricing["supplier_profit_afn"] == 64.3
    assert pricing["saraf_profit_afn"] == 38.6
    assert pricing["supplier_payout_afn"] == 963.8
    assert pricing["total_afn"] == 1002.3


def test_admin_customer_fee_is_full_markup_not_net_profit():
    quote = {
        "usd_rate": 64.25,
        "base_afn": 899.5,
        "total_usd": 15.6,
        "payable_usd": 15.6,
        "total_afn": 1002.3,
        "supplier_profit_usd": 1.0,
        "supplier_profit_afn": 64.3,
        "supplier_payout_usd": 15.0,
        "supplier_payout_afn": 963.8,
        "saraf_profit_usd": 0.6,
        "saraf_profit_afn": 38.6,
    }

    breakdown = usdt_order_service._buy_admin_pricing(14, quote)

    assert round(breakdown["customer_fee_usd"], 2) == 1.6
    assert round(breakdown["customer_fee_afn"], 1) == 102.8
    assert breakdown["saraf_profit_usd"] == 0.6
    assert breakdown["supplier_profit_usd"] == 1.0
    assert breakdown["supplier_payout_usd"] == 15.0
