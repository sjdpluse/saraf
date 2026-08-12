import time

import pytest

from services import quote_service


SAMPLE_QUOTE = {
    "usd_rate": 70.5,
    "fee_percent": 2.0,
    "base_afn": 705.0,
    "fee_afn": 14.1,
    "total_afn": 719.1,
    "total_usd": 10.0,
}


def test_create_and_load_quote(fake_client):
    persisted = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)
    assert persisted["quote_id"]
    row = quote_service.load_and_validate(111, persisted["quote_id"], "buy", 10.0)
    assert row["status"] == "active"
    assert row["chat_id"] == 111


def test_load_quote_wrong_owner_rejected(fake_client):
    persisted = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)
    with pytest.raises(quote_service.QuoteError) as exc:
        quote_service.load_and_validate(999, persisted["quote_id"], "buy", 10.0)
    assert exc.value.code == "QUOTE_NOT_FOUND"


def test_load_quote_wrong_amount_rejected(fake_client):
    persisted = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)
    with pytest.raises(quote_service.QuoteError) as exc:
        quote_service.load_and_validate(111, persisted["quote_id"], "buy", 999.0)
    assert exc.value.code == "QUOTE_MISMATCH"


def test_load_quote_wrong_order_type_rejected(fake_client):
    persisted = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)
    with pytest.raises(quote_service.QuoteError) as exc:
        quote_service.load_and_validate(111, persisted["quote_id"], "sell", 10.0)
    assert exc.value.code == "QUOTE_NOT_FOUND"


def test_expired_quote_rejected(fake_client, monkeypatch):
    persisted = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)
    # به‌جای صبر واقعی، expires_at ذخیره‌شده را دستی به گذشته می‌بریم
    fake_client._store["usdt_quotes"][0]["expires_at"] = "2000-01-01T00:00:00+00:00"
    with pytest.raises(quote_service.QuoteError) as exc:
        quote_service.load_and_validate(111, persisted["quote_id"], "buy", 10.0)
    assert exc.value.code == "QUOTE_EXPIRED"
    # و باید در دیتابیس هم status='expired' ثبت شده باشد
    assert fake_client._store["usdt_quotes"][0]["status"] == "expired"


def test_consumed_quote_cannot_be_reused(fake_client):
    persisted = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)
    quote_service.consume(persisted["quote_id"], chat_id=111, order_id=1)
    with pytest.raises(quote_service.QuoteError) as exc:
        quote_service.load_and_validate(111, persisted["quote_id"], "buy", 10.0)
    assert exc.value.code == "QUOTE_CONSUMED"


def test_quote_creation_writes_audit_log(fake_client):
    quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)
    audit_rows = fake_client.rows("audit_log")
    assert any(r["action"] == "quote_created" for r in audit_rows)
