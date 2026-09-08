import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from config import BOT_TOKEN
from services import rate_limiter, remittance_service, supabase_service as db, webapp_auth
from services.remittance_wallet_config import configured_assets

router = APIRouter(prefix="/api/remittances", tags=["remittances"])


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


class QuoteRequest(BaseModel):
    amount: float
    asset: str = "USDT"
    network: str


class CreateRequest(BaseModel):
    sender_country: str
    beneficiary_full_name: str
    beneficiary_phone: str
    beneficiary_province: str
    beneficiary_city: str
    beneficiary_address: Optional[str] = None
    relationship: str
    purpose: str
    amount: float
    asset: str = "USDT"
    network: str


class TxRequest(BaseModel):
    tx_hash: str


@router.get("/config")
async def config(user: dict = Depends(_authenticate)):
    return {"assets": configured_assets(), "fee_percent": _fee_percent()}


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
        raise HTTPException(status_code=403, detail="ابتدا پروفایل خود را تکمیل کنید.")
    profile = db.get_user_profile(user["id"]) or {}
    key = (idempotency_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Idempotency-Key الزامی است.")
    try:
        order = await remittance_service.create_order(
            chat_id=user["id"],
            sender_name=f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or None,
            sender_phone=profile.get("phone"),
            sender_country=payload.sender_country,
            beneficiary_full_name=payload.beneficiary_full_name,
            beneficiary_phone=payload.beneficiary_phone,
            beneficiary_province=payload.beneficiary_province,
            beneficiary_city=payload.beneficiary_city,
            beneficiary_address=payload.beneficiary_address,
            relationship=payload.relationship,
            purpose=payload.purpose,
            amount=payload.amount,
            asset=payload.asset,
            network=payload.network,
            idempotency_key=key,
            fee_percent=_fee_percent(),
        )
        return order
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="ثبت حواله ناموفق بود؛ دوباره تلاش کنید.")


@router.post("/{order_id}/tx")
async def submit_transaction(order_id: int, payload: TxRequest, user: dict = Depends(_authenticate)):
    try:
        return await remittance_service.submit_tx_hash(
            chat_id=user["id"], order_id=order_id, tx_hash=payload.tx_hash
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="ثبت تراکنش ناموفق بود.")


@router.get("/me")
async def my_remittances(user: dict = Depends(_authenticate)):
    return remittance_service.get_my_orders(user["id"])
