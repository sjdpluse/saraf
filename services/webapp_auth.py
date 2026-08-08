"""
اعتبارسنجی initData ارسالی از Telegram Mini App، طبق مستندات رسمی تلگرام:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

بدون این اعتبارسنجی، هرکسی می‌تواند مستقیماً API را صدا بزند و به‌جای کاربر دیگری
سفارش ثبت کند؛ این ماژول دقیقاً همان چیزی است که به سیستم اعتبار واقعی (نه فقط
ظاهری) می‌دهد.
"""
import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import parse_qsl


class InitDataError(ValueError):
    pass


def verify_init_data(init_data: Optional[str], bot_token: str, max_age_seconds: int = 86400) -> dict:
    """
    initData را اعتبارسنجی می‌کند و دیکشنری کاربر تلگرامی (id, username, first_name, ...)
    را برمی‌گرداند. در صورت نامعتبر یا منقضی بودن، InitDataError پرتاب می‌شود.
    """
    if not init_data:
        raise InitDataError("initData ارسال نشده است.")
    if not bot_token:
        raise InitDataError("BOT_TOKEN در سرور تنظیم نشده است.")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("امضای initData یافت نشد.")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("امضای initData نامعتبر است.")

    auth_date = int(pairs.get("auth_date", "0") or "0")
    if max_age_seconds and auth_date and (time.time() - auth_date) > max_age_seconds:
        raise InitDataError("initData منقضی شده است؛ لطفاً مینی‌اپ را دوباره باز کنید.")

    user_raw = pairs.get("user")
    if not user_raw:
        raise InitDataError("اطلاعات کاربر در initData یافت نشد.")

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        raise InitDataError("اطلاعات کاربر قابل‌خواندن نیست.")

    if "id" not in user:
        raise InitDataError("شناسهٔ کاربر در initData یافت نشد.")

    return user
