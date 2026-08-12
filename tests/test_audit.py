from services import audit_service, supabase_service as db


def test_mask_dict_masks_sensitive_fields_only():
    masked = audit_service.mask_dict({"payment_info": "1234567890123456", "note": "hello"})
    assert masked["note"] == "hello"
    assert masked["payment_info"] != "1234567890123456"
    assert masked["payment_info"].startswith("12")
    assert masked["payment_info"].endswith("56")
    assert "*" in masked["payment_info"]


def test_mask_dict_short_values_fully_masked():
    masked = audit_service.mask_dict({"wallet_address": "abc"})
    assert masked["wallet_address"] == "***"


def test_record_writes_to_audit_log(fake_client):
    audit_service.record(action="test_action", entity="test_entity", entity_id=42, actor=1, after={"x": 1})
    rows = fake_client.rows("audit_log")
    assert len(rows) == 1
    assert rows[0]["action"] == "test_action"
    assert rows[0]["entity_id"] == "42"


def test_record_never_raises_on_db_failure(monkeypatch):
    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "get_client", _boom)
    # نباید Exception بالا بیاید — audit نباید عملیات اصلی را fail کند
    audit_service.record(action="x", entity="y")


def test_kyc_status_change_writes_audit(fake_client):
    fake_client.table("user_profiles").insert({"chat_id": 111, "kyc_status": "pending"}).execute()
    db.set_kyc_status(111, "verified", verified_by=999)
    rows = fake_client.rows("audit_log")
    assert any(r["action"] == "kyc_verified" and r["actor"] == 999 for r in rows)


def test_payment_info_change_writes_masked_audit(fake_client):
    fake_client.table("user_profiles").insert(
        {"chat_id": 111, "payment_info": "OLD-CARD-1111", "payment_info_change_count": 0}
    ).execute()
    db.update_payment_info(111, "NEW-CARD-2222")
    rows = fake_client.rows("audit_log")
    matching = [r for r in rows if r["action"] == "payment_info_changed"]
    assert matching
    # اطلاعات پرداخت خام نباید در audit_log ذخیره شود
    assert "OLD-CARD-1111" not in str(matching[0]["before"])
    assert "NEW-CARD-2222" not in str(matching[0]["after"])


def test_payment_info_no_change_no_audit(fake_client):
    fake_client.table("user_profiles").insert(
        {"chat_id": 111, "payment_info": "SAME-CARD", "payment_info_change_count": 0}
    ).execute()
    db.update_payment_info(111, "SAME-CARD")
    rows = fake_client.rows("audit_log")
    assert not [r for r in rows if r["action"] == "payment_info_changed"]
