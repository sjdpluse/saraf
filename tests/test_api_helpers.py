import pytest
from fastapi import HTTPException

import api


def test_own_receipt_url_accepted():
    url = "https://x.supabase.co/storage/v1/object/sign/usdt-receipts/111_1699999999.jpg?token=abc"
    assert api._validate_own_receipt_reference(url, 111) == url


def test_foreign_chat_id_receipt_rejected():
    url = "https://x.supabase.co/storage/v1/object/sign/usdt-receipts/111_1699999999.jpg?token=abc"
    with pytest.raises(HTTPException):
        api._validate_own_receipt_reference(url, 222)


def test_arbitrary_external_url_rejected():
    with pytest.raises(HTTPException):
        api._validate_own_receipt_reference("https://evil.example.com/phishing.html", 111)


def test_empty_receipt_url_rejected():
    with pytest.raises(HTTPException):
        api._validate_own_receipt_reference("", 111)


def test_too_long_receipt_url_rejected():
    with pytest.raises(HTTPException):
        api._validate_own_receipt_reference("https://x/" + "a" * 3000, 111)


def test_safe_ext_uses_content_type_first():
    assert api._safe_ext("weird.name/../../etc", "image/png") == "png"


def test_safe_ext_rejects_unsafe_filename_without_known_content_type():
    # بدون content_type شناخته‌شده و بدون پسوند مجاز -> پیش‌فرض امن jpg
    assert api._safe_ext("a.jpg/../../etc/passwd", None) == "jpg"


def test_safe_ext_accepts_known_extension_fallback():
    assert api._safe_ext("document.pdf", None) == "pdf"
