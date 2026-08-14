from services import supabase_service as db


def test_has_basic_profile_false_when_no_row(fake_client):
    assert db.has_basic_profile(111) is False


def test_save_basic_profile_then_has_basic_profile_true(fake_client):
    db.save_basic_profile(111, "Ali", "Ahmadi", "0700000000")
    assert db.has_basic_profile(111) is True
    assert db.has_identity_verification(111) is False


def test_save_basic_profile_does_not_touch_existing_docs(fake_client):
    fake_client.table("user_profiles").insert(
        {"chat_id": 111, "id_document_path": "kyc/1.jpg", "selfie_path": "kyc/2.jpg"}
    ).execute()
    db.save_basic_profile(111, "Ali", "Ahmadi", "0700000000")
    profile = db.get_user_profile(111)
    assert profile["first_name"] == "Ali"
    assert profile["id_document_path"] == "kyc/1.jpg"  # دست‌نخورده مانده


def test_save_identity_verification_requires_existing_profile_row(fake_client):
    # اگر پروفایل پایه اصلاً وجود نداشته باشد، UPDATE روی هیچ ردیفی اثر نمی‌کند
    db.save_identity_verification(111, "kyc/id.jpg", "kyc/selfie.jpg")
    assert db.has_identity_verification(111) is False


def test_save_identity_verification_sets_docs_and_optional_payment(fake_client):
    db.save_basic_profile(111, "Ali", "Ahmadi", "0700000000")
    db.save_identity_verification(111, "kyc/id.jpg", "kyc/selfie.jpg", payment_info="Bank 123")
    assert db.has_identity_verification(111) is True
    profile = db.get_user_profile(111)
    assert profile["payment_info"] == "Bank 123"


def test_save_identity_verification_payment_info_optional(fake_client):
    db.save_basic_profile(111, "Ali", "Ahmadi", "0700000000")
    db.save_identity_verification(111, "kyc/id.jpg", "kyc/selfie.jpg", payment_info=None)
    assert db.has_identity_verification(111) is True
    profile = db.get_user_profile(111)
    assert not profile.get("payment_info")


def test_has_identity_verification_requires_both_doc_and_selfie(fake_client):
    fake_client.table("user_profiles").insert({"chat_id": 111, "id_document_path": "kyc/1.jpg"}).execute()
    assert db.has_identity_verification(111) is False
