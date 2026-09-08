import pytest

from services.api_errors import ApiError
from services.usdt_api_guard import AZIZI_MIN_STABLECOIN_AMOUNT, _validate_online_provider


def test_hesabpay_is_allowed_below_azizi_threshold():
    provider = _validate_online_provider(
        {"payment_method": "online", "payment_provider": "hesabpay"},
        "buy",
        100,
    )
    assert provider == "hesabpay"


def test_azizi_is_rejected_at_exactly_500():
    with pytest.raises(ApiError) as exc_info:
        _validate_online_provider(
            {"payment_method": "online", "payment_provider": "azizi"},
            "buy",
            AZIZI_MIN_STABLECOIN_AMOUNT,
        )
    assert exc_info.value.code == "AZIZI_MIN_AMOUNT"


def test_azizi_is_allowed_only_above_500_for_buy():
    provider = _validate_online_provider(
        {"payment_method": "online", "payment_provider": "azizi"},
        "buy",
        AZIZI_MIN_STABLECOIN_AMOUNT + 0.01,
    )
    assert provider == "azizi"


def test_azizi_is_rejected_below_threshold_for_sell():
    with pytest.raises(ApiError) as exc_info:
        _validate_online_provider(
            {"receive_method": "online", "receive_provider": "azizi"},
            "sell",
            499.99,
        )
    assert exc_info.value.code == "AZIZI_MIN_AMOUNT"


def test_online_provider_is_required_server_side():
    with pytest.raises(ApiError) as exc_info:
        _validate_online_provider({"payment_method": "online"}, "buy", 1000)
    assert exc_info.value.code == "ONLINE_PROVIDER_REQUIRED"


def test_in_person_does_not_require_online_provider():
    assert _validate_online_provider({"payment_method": "in_person"}, "buy", 100) is None
