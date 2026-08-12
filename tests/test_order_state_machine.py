from services.order_state_machine import is_valid_transition, validate_transition, InvalidStateTransition
import pytest


def test_pending_to_confirmed_allowed():
    assert is_valid_transition("pending", "confirmed")


def test_pending_to_cancelled_allowed():
    assert is_valid_transition("pending", "cancelled")


def test_confirmed_to_completed_allowed():
    assert is_valid_transition("confirmed", "completed")


def test_completed_is_terminal_no_outgoing_transitions():
    assert not is_valid_transition("completed", "pending")
    assert not is_valid_transition("completed", "cancelled")
    assert not is_valid_transition("completed", "confirmed")


def test_cancelled_to_completed_rejected():
    assert not is_valid_transition("cancelled", "completed")


def test_same_status_is_noop_allowed():
    assert is_valid_transition("pending", "pending")


def test_validate_transition_raises_on_invalid():
    with pytest.raises(InvalidStateTransition):
        validate_transition("completed", "pending")


def test_unknown_status_rejected():
    assert not is_valid_transition("pending", "totally_made_up_status")
