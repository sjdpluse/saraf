from services.remittance_asset_registry import ASSETS, normalize_asset, normalize_network, pricing_asset


def test_requested_assets_are_registered():
    expected = {"USDT","USDC","DAI","TUSD","TRX","BNB","ETH","SOL","WBTC","PAXG","PYUSD","WETH","BTCB","POL","BTC"}
    assert expected == set(ASSETS)


def test_network_aliases_and_wrapped_pricing():
    assert normalize_network("SOL", "solana") == "SOL"
    assert normalize_network("BTC", "bitcoin") == "BITCOIN"
    assert pricing_asset("WETH") == "ETH"
    assert pricing_asset("WBTC") == "BTC"
    assert pricing_asset("BTCB") == "BTC"


def test_core_network_sets():
    assert "ARBITRUM" in ASSETS["USDT"]["networks"]
    assert "BASE" in ASSETS["USDC"]["networks"]
    assert "POLYGON" in ASSETS["DAI"]["networks"]
    assert ASSETS["TRX"]["networks"] == ("TRC20",)
    assert ASSETS["BTC"]["networks"] == ("BITCOIN",)
