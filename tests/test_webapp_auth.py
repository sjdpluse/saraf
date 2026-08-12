import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from services import webapp_auth

BOT_TOKEN = "123456:TESTTOKEN"


def _make_init_data(user: dict, auth_date: int = None, bot_token: str = BOT_TOKEN, tamper: bool = False) -> str:
    auth_date = auth_date if auth_date is not None else int(time.time())
    pairs = {"auth_date": str(auth_date), "query_id": "AAEXXX", "user": json.dumps(user)}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if tamper:
        computed_hash = "0" * len(computed_hash)
    pairs["hash"] = computed_hash
    return urlencode(pairs)


def test_valid_init_data_returns_user():
    init_data = _make_init_data({"id": 12345, "username": "sajad"})
    user = webapp_auth.verify_init_data(init_data, BOT_TOKEN)
    assert user["id"] == 12345


def test_tampered_hash_rejected():
    init_data = _make_init_data({"id": 12345}, tamper=True)
    with pytest.raises(webapp_auth.InitDataError):
        webapp_auth.verify_init_data(init_data, BOT_TOKEN)


def test_wrong_bot_token_rejected():
    init_data = _make_init_data({"id": 12345}, bot_token="999:OTHERTOKEN")
    with pytest.raises(webapp_auth.InitDataError):
        webapp_auth.verify_init_data(init_data, BOT_TOKEN)


def test_tampered_user_id_rejected():
    """اگر کسی فقط فیلد user را دستکاری کند (بدون دوباره امضا کردن)، hash دیگر
    مطابقت ندارد — این دقیقاً همان چیزی است که جلوی جعل هویت را می‌گیرد."""
    init_data = _make_init_data({"id": 12345})
    tampered = init_data.replace("12345", "99999")
    with pytest.raises(webapp_auth.InitDataError):
        webapp_auth.verify_init_data(tampered, BOT_TOKEN)


def test_expired_init_data_rejected():
    old_auth_date = int(time.time()) - 999999
    init_data = _make_init_data({"id": 12345}, auth_date=old_auth_date)
    with pytest.raises(webapp_auth.InitDataError):
        webapp_auth.verify_init_data(init_data, BOT_TOKEN, max_age_seconds=86400)


def test_missing_init_data_rejected():
    with pytest.raises(webapp_auth.InitDataError):
        webapp_auth.verify_init_data(None, BOT_TOKEN)


def test_missing_hash_rejected():
    with pytest.raises(webapp_auth.InitDataError):
        webapp_auth.verify_init_data("auth_date=123&user=%7B%7D", BOT_TOKEN)
