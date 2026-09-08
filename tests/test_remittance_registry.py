import unittest

from services.remittance_asset_registry import ASSETS, normalize_network, pricing_asset


class RemittanceRegistryTests(unittest.TestCase):
    def test_requested_assets_are_registered(self):
        expected = {"USDT","USDC","DAI","TUSD","TRX","BNB","ETH","SOL","WBTC","PAXG","PYUSD","WETH","BTCB","POL","BTC"}
        self.assertEqual(expected, set(ASSETS))

    def test_network_aliases_and_wrapped_pricing(self):
        self.assertEqual("SOL", normalize_network("SOL", "solana"))
        self.assertEqual("BITCOIN", normalize_network("BTC", "bitcoin"))
        self.assertEqual("ETH", pricing_asset("WETH"))
        self.assertEqual("BTC", pricing_asset("WBTC"))
        self.assertEqual("BTC", pricing_asset("BTCB"))

    def test_core_network_sets(self):
        self.assertIn("ARBITRUM", ASSETS["USDT"]["networks"])
        self.assertIn("BASE", ASSETS["USDC"]["networks"])
        self.assertIn("POLYGON", ASSETS["DAI"]["networks"])
        self.assertEqual(("TRC20",), ASSETS["TRX"]["networks"])
        self.assertEqual(("BITCOIN",), ASSETS["BTC"]["networks"])


if __name__ == "__main__":
    unittest.main()
