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


def test_buy_margin_is_monotonic_around_previous_50_usdt_boundary():
    pricing_50 = usdt_service.build_buy_pricing(50, 64.25)
    pricing_51 = usdt_service.build_buy_pricing(51, 64.25)

    assert pricing_50["market_margin_usd"] == 2.0
    assert pricing_51["market_margin_usd"] == 2.0
    assert pricing_50["customer_payable_usd"] == 51.6
    assert pricing_51["customer_payable_usd"] == 52.6
    assert pricing_51["customer_payable_usd"] > pricing_50["customer_payable_usd"]


def test_buy_margin_switches_smoothly_at_80_usdt():
    pricing_79 = usdt_service.build_buy_pricing(79, 64.25)
    pricing_80 = usdt_service.build_buy_pricing(80, 64.25)
    pricing_81 = usdt_service.build_buy_pricing(81, 64.25)

    assert pricing_79["market_margin_usd"] == 2.0
    assert pricing_80["market_margin_usd"] == 2.0
    assert pricing_81["market_margin_usd"] == 2.03

    assert pricing_79["customer_payable_usd"] == 80.6
    assert pricing_80["customer_payable_usd"] == 81.6
    assert pricing_81["customer_payable_usd"] == 82.62

    assert pricing_79["customer_payable_usd"] < pricing_80["customer_payable_usd"] < pricing_81["customer_payable_usd"]


def test_percentage_margin_grows_above_floor():
    pricing_100 = usdt_service.build_buy_pricing(100, 64.25)
    pricing_200 = usdt_service.build_buy_pricing(200, 64.25)

    assert pricing_100["market_margin_usd"] == 2.5
    assert pricing_100["customer_payable_usd"] == 102.0

    assert pricing_200["market_margin_usd"] == 5.0
    assert pricing_200["customer_payable_usd"] == 204.0


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
