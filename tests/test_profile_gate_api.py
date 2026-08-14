import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode

from fastapi.testclient import TestClient

import api
from services import supabase_service as db

BOT_TOKEN = "123456:testtoken"  # باید با BOT_TOKEN در .env تست هم‌راستا باشد


def _make_init_data(user: dict) -> str:
    auth_date = int(time.time())
    pairs = {"auth_date": str(auth_date), "query_id": "AAEXXX", "user": json.dumps(user)}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    pairs["hash"] = h
    return urlencode(pairs)


SAMPLE_QUOTE = {"usd_rate": 70.5, "fee_percent": 2.0, "total_afn": 719.1, "total_usd": 10.0}


def _order_payload(amount):
    return {
        "amount": amount,
        "quote_id": 1,
        "payment_method": "in_person",
        "network": "TRC20",
        "wallet_address": "TXYZabc123XYZabc123XYZabc123XYZabc",
    }


def test_order_creation_requires_basic_profile(fake_client):
    client = TestClient(api.app)
    init_data = _make_init_data({"id": 111})

    from services import quote_service

    quote = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)

    r = client.post(
        "/api/usdt/orders/buy",
        headers={"X-Telegram-Init-Data": init_data, "Idempotency-Key": "a" * 32},
        json={**_order_payload(10), "quote_id": quote["quote_id"]},
    )
    assert r.status_code == 403
    assert "پروفایل" in r.json()["detail"]


def test_order_creation_allowed_under_threshold_with_basic_profile_only(fake_client):
    client = TestClient(api.app)
    init_data = _make_init_data({"id": 111})
    db.save_basic_profile(111, "Ali", "Ahmadi", "0700000000")

    from services import quote_service

    quote = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)

    with patch("services.usdt_order_service.notify_admins", AsyncMock(return_value=None)), \
         patch("services.usdt_order_service._send_order_card", AsyncMock(return_value=None)):
        r = client.post(
            "/api/usdt/orders/buy",
            headers={"X-Telegram-Init-Data": init_data, "Idempotency-Key": "a" * 32},
            json={**_order_payload(10), "quote_id": quote["quote_id"]},
        )
    assert r.status_code == 200
    assert r.json()["order_id"]


def test_order_creation_above_threshold_requires_identity_verification(fake_client):
    client = TestClient(api.app)
    init_data = _make_init_data({"id": 222})
    db.save_basic_profile(222, "Ali", "Ahmadi", "0700000000")  # فقط پروفایل پایه، بدون مدارک

    from services import quote_service

    big_quote = {**SAMPLE_QUOTE, "total_afn": 25000, "total_usd": 300}
    quote = quote_service.create_quote(222, "buy", 300.0, big_quote)

    r = client.post(
        "/api/usdt/orders/buy",
        headers={"X-Telegram-Init-Data": init_data, "Idempotency-Key": "b" * 32},
        json={**_order_payload(300), "quote_id": quote["quote_id"]},
    )
    assert r.status_code == 403
    body = r.json()
    assert body["error"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"


def test_order_creation_above_threshold_succeeds_after_verification(fake_client):
    client = TestClient(api.app)
    init_data = _make_init_data({"id": 333})
    db.save_basic_profile(333, "Ali", "Ahmadi", "0700000000")
    db.save_identity_verification(333, "kyc/id.jpg", "kyc/selfie.jpg")

    from services import quote_service

    big_quote = {**SAMPLE_QUOTE, "total_afn": 25000, "total_usd": 300}
    quote = quote_service.create_quote(333, "buy", 300.0, big_quote)

    with patch("services.usdt_order_service.notify_admins", AsyncMock(return_value=None)), \
         patch("services.usdt_order_service._send_order_card", AsyncMock(return_value=None)):
        r = client.post(
            "/api/usdt/orders/buy",
            headers={"X-Telegram-Init-Data": init_data, "Idempotency-Key": "c" * 32},
            json={**_order_payload(300), "quote_id": quote["quote_id"]},
        )
    assert r.status_code == 200
    assert r.json()["order_id"]


def test_profile_endpoint_reports_both_tiers(fake_client):
    client = TestClient(api.app)
    init_data = _make_init_data({"id": 444})
    db.save_basic_profile(444, "Ali", "Ahmadi", "0700000000")

    r = client.get("/api/usdt/profile", headers={"X-Telegram-Init-Data": init_data})
    assert r.status_code == 200
    body = r.json()
    assert body["has_basic_profile"] is True
    assert body["has_identity_verification"] is False
    assert body["identity_verification_threshold_usd"] == 250
