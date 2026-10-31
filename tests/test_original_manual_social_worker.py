"""NO LIVE Meta calls: original Saraf social queue safety regressions."""
import asyncio
import sys
import types
import unittest
from unittest.mock import patch

from scripts.run_original_manual_social_worker import (
    assert_ready, classify, publish_original_pair,
)


class SocialPortTests(unittest.TestCase):
    def test_requires_all_private_keys_and_cutover(self):
        with self.assertRaisesRegex(RuntimeError, "MISSING_REQUIRED"):
            assert_ready({})
        env = {
            "SARAF_ORIGINAL_SOCIAL_PUBLISH_ENABLED": "true",
            "SARAF_ORIGINAL_CUTOVER_APPROVED": "true",
            "SUPABASE_URL": "https://example.test",
            "SUPABASE_KEY": "stub",
            "FACEBOOK_PAGE_ID": "stub",
            "FACEBOOK_PAGE_ACCESS_TOKEN": "stub",
            "INSTAGRAM_BUSINESS_ACCOUNT_ID": "stub",
        }
        assert_ready(env)
        env["SARAF_ORIGINAL_CUTOVER_APPROVED"] = "false"
        with self.assertRaisesRegex(RuntimeError, "NOT_ENABLED"):
            assert_ready(env)

    def test_graph_errors_are_never_unconditionally_retried(self):
        self.assertEqual(classify((True, "ok")), "posted")
        self.assertEqual(classify((False, "timeout")), "unknown")
        self.assertEqual(classify(TimeoutError("accepted maybe")), "unknown")
        self.assertEqual(classify(None), "unknown")

    def test_original_services_invoked_concurrently_with_force_without_real_post(self):
        history = []
        async def quotes():
            return {"usd": {"reference_rate": 70}}, {"karats": {24: {}}}, None
        async def fb(q, g, s, force=False):
            history.append(("facebook", force, q is not None))
            return True, "ok"
        async def ig(q, g, s, force=False):
            history.append(("instagram", force, q is not None))
            return False, "network uncertainty"
        jobs = types.ModuleType("jobs")
        jobs.get_current_quotes_and_metals = quotes
        services = types.ModuleType("services")
        services.facebook_service = types.SimpleNamespace(check_and_maybe_post=fb)
        services.instagram_service = types.SimpleNamespace(check_and_maybe_post=ig)
        with patch.dict(sys.modules, {"jobs": jobs, "services": services}):
            statuses = asyncio.run(publish_original_pair())
        self.assertEqual(statuses[:2], ("posted", "unknown"))
        self.assertEqual(len(history), 2)
        self.assertTrue(all(force and valid for _, force, valid in history))

    def test_absent_real_price_never_dispatches_fake_post(self):
        async def quotes():
            return None, None, None
        jobs = types.ModuleType("jobs")
        jobs.get_current_quotes_and_metals = quotes
        services = types.ModuleType("services")
        with patch.dict(sys.modules, {"jobs": jobs, "services": services}):
            result = asyncio.run(publish_original_pair())
        self.assertEqual(result[:2], ("failed", "failed"))


if __name__ == "__main__":
    unittest.main()
