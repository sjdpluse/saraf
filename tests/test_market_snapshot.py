"""Display-only market data: missing values, stale values, and cache behaviour."""
import asyncio
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx

spec = importlib.util.spec_from_file_location(
    "market_snapshot_under_test",
    Path(__file__).resolve().parents[1] / "services" / "market_snapshot.py",
)
market = importlib.util.module_from_spec(spec)
spec.loader.exec_module(market)
NOW = 1800000000


class MarketSnapshotTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        market._cache = {"assets": [], "attempted_at": None}
        market._lock = asyncio.Lock()

    def test_signed_and_real_zero_changes_are_preserved(self):
        result = market._normalise({
            "tether": {"usd_24h_change": 0, "last_updated_at": NOW},
            "bitcoin": {"usd_24h_change": -2.75, "last_updated_at": NOW},
            "solana": {"usd_24h_change": 1.25, "last_updated_at": NOW},
        }, NOW)
        by_symbol = {x["symbol"]: x["change_24h"] for x in result}
        self.assertEqual(by_symbol, {"USDT": 0, "USDC": None, "BTC": -2.75, "SOL": 1.25})

    def test_missing_invalid_and_stale_values_are_not_zero(self):
        for change, timestamp in [(None, NOW), (True, NOW), ("1.2", NOW),
                                  (float("nan"), NOW), (float("inf"), NOW),
                                  (2, None), (2, NOW - 301), (2, NOW + 61)]:
            with self.subTest(change=change, timestamp=timestamp):
                result = market._normalise({"bitcoin": {
                    "usd_24h_change": change, "last_updated_at": timestamp,
                }}, NOW)
                self.assertIsNone(next(x for x in result if x["symbol"] == "BTC")["change_24h"])

    def test_provider_null_record_is_tolerated(self):
        result = market._normalise({"bitcoin": None}, NOW)
        self.assertTrue(all(x["change_24h"] is None for x in result))

    def test_cached_values_expire_using_source_time(self):
        market._cache["assets"] = market._normalise({
            "bitcoin": {"usd_24h_change": 1, "last_updated_at": NOW},
        }, NOW)
        self.assertEqual(market._snapshot(NOW + 300)["status"], "fresh")
        expired = market._snapshot(NOW + 301)
        self.assertEqual(expired["status"], "unavailable")
        self.assertTrue(all(x["change_24h"] is None for x in expired["assets"]))

    async def test_concurrent_visits_share_one_upstream_request(self):
        response = Mock()
        response.json.return_value = {"bitcoin": {"usd_24h_change": -1.5, "last_updated_at": NOW}}
        client = AsyncMock()
        client.get.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch.object(market.httpx, "AsyncClient", return_value=context), patch.object(market.time, "time", return_value=NOW):
            results = await asyncio.gather(*(market.get_market_snapshot() for _ in range(5)))
        self.assertEqual(client.get.await_count, 1)
        params = client.get.call_args.kwargs["params"]
        self.assertEqual(set(params["ids"].split(",")), {"tether", "usd-coin", "bitcoin", "solana"})
        self.assertEqual(params["include_24hr_change"], "true")
        self.assertEqual(params["include_last_updated_at"], "true")
        self.assertTrue(all(result["status"] == "fresh" for result in results))

    async def test_provider_failure_is_cached_without_making_up_values(self):
        client = AsyncMock()
        client.get.side_effect = httpx.ConnectError("unavailable")
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch.object(market.httpx, "AsyncClient", return_value=context):
            first = await market.get_market_snapshot()
            second = await market.get_market_snapshot()
        self.assertEqual(client.get.await_count, 1)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "unavailable")
        self.assertEqual(first["assets"], [])


if __name__ == "__main__":
    unittest.main()
