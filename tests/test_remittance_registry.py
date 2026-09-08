import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "services" / "remittance_asset_registry.py"
spec = importlib.util.spec_from_file_location("remittance_asset_registry_standalone", MODULE_PATH)
registry = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(registry)

ASSETS = registry.ASSETS
normalize_network = registry.normalize_network
pricing_asset = registry.pricing_asset


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
