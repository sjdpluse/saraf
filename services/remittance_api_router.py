import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel

from config import BOT_TOKEN, USDT_IDENTITY_VERIFICATION_THRESHOLD_USD, USDT_KYC_DOCS_BUCKET
from services.api_errors import ApiError
from services import rate_limiter, remittance_service, supabase_service as db, webapp_auth
from services.remittance_wallet_config import configured_assets

router = APIRouter(prefix="/api/remittances", tags=["remittances"])

_MAX_ID_DOCUMENT_BYTES = 10 * 1024 * 1024
_ALLOWED_ID_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _authenticate(x_telegram_init_data: Optional[str] = Header(None)) -> dict:
    try:
        return webapp_auth.verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def _fee_percent() -> float:
    raw = os.getenv("REMITTANCE_FEE_PERCENT", "0").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 0.0
    return max(0.0, min(value, 25.0))


def _client_order(row: dict) -> dict:
    data = dict(row)
    for key in (
        "idempotency_key", "admin_note", "crypto_confirmed_by", "paid_by",
        "sender_phone", "beneficiary_id_document_path",
    ):
        data.pop(key, None)
    if data.get("status") not in ("payout_ready", "completed"):
        data.pop("pickup_code", None)
    return data


def _validate_beneficiary_document(path: str, chat_id: int) -> str:
    cleaned = str(path or "").strip()
    expected_prefix = f"remittances/{int(chat_id)}/"
    if not cleaned.startswith(expected_prefix) or ".." in cleaned:
        raise ValueError("مدرک هویت گیرنده معتبر نیست؛ دوباره آپلود کنید.")
    if db.download_private_file(USDT_KYC_DOCS_BUCKET, cleaned) is None:
        raise ValueError("مدرک هویت گیرنده پیدا نشد؛ دوباره آپلود کنید.")
    return cleaned


class QuoteRequest(BaseModel):
    amount: float
    asset: str = "USDT"
    network: str


class CreateRequest(BaseModel):
    sender_full_name: str
    sender_country: str
    beneficiary_full_name: str
    beneficiary_phone: str
    beneficiary_province: str
    beneficiary_city: str
    beneficiary_address: str
    beneficiary_id_document_path: str
    amount: float
    asset: str = "USDT"
    network: str


class TxRequest(BaseModel):
    tx_hash: str


@router.get("/config")
async def config(user: dict = Depends(_authenticate)):
    return {
        "assets": configured_assets(),
        "fee_percent": _fee_percent(),
        "identity_verification_threshold_usd": USDT_IDENTITY_VERIFICATION_THRESHOLD_USD,
        "min_usd": float(os.getenv("REMITTANCE_MIN_USD", "10")),
        "max_usd": float(os.getenv("REMITTANCE_MAX_USD", "10000")),
    }


@router.post("/upload-beneficiary-id")
async def upload_beneficiary_id(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(_authenticate),
):
    rate_limiter.enforce("receipt_upload", request, identity=f"remit-id:{user['id']}")
    ext = _ALLOWED_ID_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(status_code=400, detail="تذکره باید تصویر JPG، PNG یا WEBP باشد.")
    content = await file.read(_MAX_ID_DOCUMENT_BYTES + 1)
    if not content or len(content) > _MAX_ID_DOCUMENT_BYTES:
        raise HTTPException(status_code=400, detail="حجم تصویر تذکره باید کمتر از ۱۰ مگابایت باشد.")
    path = f"remittances/{int(user['id'])}/{uuid.uuid4().hex}.{ext}"
    stored = db.upload_private_file(USDT_KYC_DOCS_BUCKET, content, path, file.content_type)
    if not stored:
        raise HTTPException(status_code=503, detail="آپلود تذکره ناموفق بود؛ دوباره تلاش کنید.")
    return {"file_id": stored}


@router.post("/quote")
async def get_quote(payload: QuoteRequest, user: dict = Depends(_authenticate)):
    try:
        return await remittance_service.quote(
            amount=payload.amount,
            asset=payload.asset,
            network=payload.network,
            fee_percent=_fee_percent(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="محاسبهٔ حواله در حال حاضر ممکن نیست.")


@router.post("")
async def create_remittance(
    payload: CreateRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: dict = Depends(_authenticate),
):
    rate_limiter.enforce("order", request, identity=str(user["id"]))
    if not db.has_basic_profile(user["id"]):
        raise ApiError(403, "BASIC_PROFILE_REQUIRED", "ابتدا پروفایل خود را تکمیل کنید.")

    try:
        preview = await remittance_service.quote(
            amount=payload.amount,
            asset=payload.asset,
            network=payload.network,
            fee_percent=_fee_percent(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="محاسبهٔ حواله در حال حاضر ممکن نیست.")

    if preview["usd_value"] > USDT_IDENTITY_VERIFICATION_THRESHOLD_USD and not db.has_identity_verification(user["id"]):
        raise ApiError(
            403,
            "IDENTITY_VERIFICATION_REQUIRED",
            f"برای حواله‌های با ارزش بیشتر از {USDT_IDENTITY_VERIFICATION_THRESHOLD_USD:g} دالر، احراز هویت کامل الزامی است.",
        )

    profile = db.get_user_profile(user["id"]) or {}
    key = (idempotency_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Idempotency-Key الزامی است.")
    try:
        document_path = _validate_beneficiary_document(payload.beneficiary_id_document_path, user["id"])
        order = await remittance_service.create_order(
            chat_id=user["id"],
            sender_name=payload.sender_full_name,
            sender_phone=profile.get("phone"),
            sender_country=payload.sender_country,
            beneficiary_full_name=payload.beneficiary_full_name,
            beneficiary_phone=payload.beneficiary_phone,
            beneficiary_province=payload.beneficiary_province,
            beneficiary_city=payload.beneficiary_city,
            beneficiary_address=payload.beneficiary_address,
            beneficiary_id_document_path=document_path,
            amount=payload.amount,
            asset=payload.asset,
            network=payload.network,
            idempotency_key=key,
            fee_percent=_fee_percent(),
        )
        return _client_order(order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="ثبت حواله ناموفق بود؛ دوباره تلاش کنید.")


@router.post("/{order_id}/tx")
async def submit_transaction(order_id: int, payload: TxRequest, user: dict = Depends(_authenticate)):
    try:
        return _client_order(await remittance_service.submit_tx_hash(
            chat_id=user["id"], order_id=order_id, tx_hash=payload.tx_hash
        ))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="ثبت تراکنش ناموفق بود.")


@router.get("/me")
async def my_remittances(user: dict = Depends(_authenticate)):
    return [_client_order(row) for row in remittance_service.get_my_orders(user["id"])]
