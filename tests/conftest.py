import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tests.fake_supabase import FakeSupabaseClient


@pytest.fixture()
def fake_client(monkeypatch):
    """یک دیتابیس in-memory تازه برای هر تست + قطع کامل side-effect های شبکه‌ای
    (اعلان تلگرام به ادمین، تولید/ارسال کارت دیجیتال) که نباید در تست واحد واقعاً
    اجرا شوند."""
    from services import supabase_service as db

    client = FakeSupabaseClient()
    monkeypatch.setattr(db, "_client", client, raising=False)
    monkeypatch.setattr(db, "get_client", lambda: client)

    from services import usdt_order_service

    async def _noop_notify(*_args, **_kwargs):
        return None

    async def _noop_card(*_args, **_kwargs):
        return None

    monkeypatch.setattr(usdt_order_service, "notify_admins", _noop_notify)
    monkeypatch.setattr(usdt_order_service, "_send_order_card", _noop_card)

    return client


@pytest.fixture()
def anyio_backend():
    return "asyncio"


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)
