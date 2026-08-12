import pytest

from services import order_transition_service as ots
from services.order_state_machine import InvalidStateTransition


def _seed_order(fake_client, status="pending"):
    row = fake_client.table("usdt_orders").insert({"chat_id": 111, "status": status, "usdt_amount": 10.0}).execute()
    return row.data[0]["id"]


def test_valid_transition_updates_status_and_history(fake_client):
    order_id = _seed_order(fake_client)
    fake_client.table("usdt_order_status_history").insert(
        {"order_id": order_id, "to_status": "confirmed", "changed_by": None}
    ).execute()
    updated = ots.transition_order_status(order_id, "confirmed", changed_by=999, reason="تایید دستی")
    assert updated["status"] == "confirmed"
    history = fake_client.rows("usdt_order_status_history")
    assert any(h["order_id"] == order_id and h.get("changed_by") == 999 for h in history)


def test_invalid_transition_raises(fake_client):
    order_id = _seed_order(fake_client, status="completed")
    with pytest.raises(InvalidStateTransition):
        ots.transition_order_status(order_id, "pending", changed_by=999)


def test_transition_writes_general_audit_log(fake_client):
    order_id = _seed_order(fake_client)
    ots.transition_order_status(order_id, "cancelled", changed_by=999, reason="رد شده توسط ادمین")
    audit_rows = fake_client.rows("audit_log")
    matching = [r for r in audit_rows if r["action"] == "order_cancelled" and r["entity_id"] == str(order_id)]
    assert matching
    assert matching[0]["actor"] == 999
    assert matching[0]["reason"] == "رد شده توسط ادمین"


def test_transition_order_not_found(fake_client):
    with pytest.raises(ots.OrderNotFoundError):
        ots.transition_order_status(99999, "confirmed", changed_by=1)


def test_noop_same_status_returns_without_error(fake_client):
    order_id = _seed_order(fake_client, status="pending")
    result = ots.transition_order_status(order_id, "pending", changed_by=1)
    assert result["status"] == "pending"
