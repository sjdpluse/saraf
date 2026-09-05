"""Additional Mini App endpoints installed without renaming legacy /api/usdt routes."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from config import BOT_TOKEN
from services import (
    in_person_pass_service,
    quote_service,
    risk_engine,
    stablecoin_card_service,
    stablecoin_networks,
    supabase_service as db,
    usdt_service,
    wallet_validator,
    webapp_auth,
)

PASS_TOKEN_TTL_SECONDS = 10 * 60


class CardPreviewRequest(BaseModel):
    action: str
    asset: str = "USDT"
    amount: float
    quote_id: int
    exchange_name: str
    network: str
    wallet_address: Optional[str] = None


class InPersonPassLinkRequest(BaseModel):
    action: str
    asset: str = "USDT"
    code: str


def _authenticate(init_data: Optional[str]) -> dict:
    try:
        return webapp_auth.verify_init_data(init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def _issue_pass_token(action: str, asset: str, code: str) -> str:
    if not BOT_TOKEN:
        raise HTTPException(status_code=503, detail="دانلود کارت در حال حاضر در دسترس نیست.")
    payload = {
        "action": action,
        "asset": asset,
        "code": code,
        "exp": int(time.time()) + PASS_TOKEN_TTL_SECONDS,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    signature = hmac.new(BOT_TOKEN.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def _verify_pass_token(token: str) -> dict:
    try:
        encoded, supplied_sig = str(token).rsplit(".", 1)
        expected_sig = hmac.new(BOT_TOKEN.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied_sig, expected_sig):
            raise ValueError("signature")
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        action = str(payload.get("action") or "")
        asset = usdt_service.normalize_asset(payload.get("asset"))
        code = str(payload.get("code") or "")
        if action not in ("buy", "sell") or not code.isdigit() or len(code) != 4:
            raise ValueError("payload")
        return {"action": action, "asset": asset, "code": code}
    except Exception as exc:
        raise HTTPException(status_code=403, detail="لینک دانلود کارت نامعتبر یا منقضی شده است.") from exc


async def stablecoin_config(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    _authenticate(x_telegram_init_data)
    return stablecoin_networks.public_config()


async def in_person_pass_link(
    payload: InPersonPassLinkRequest,
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    _authenticate(x_telegram_init_data)
    if payload.action not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="نوع مراجعه نامعتبر است.")
    try:
        asset = usdt_service.normalize_asset(payload.asset)
    except usdt_service.StablecoinAssetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    code = str(payload.code or "")
    if not code.isdigit() or len(code) != 4:
        raise HTTPException(status_code=400, detail="کد مراجعه باید ۴ رقم باشد.")

    token = _issue_pass_token(payload.action, asset, code)
    filename = f"saraf-{payload.action}-{asset}-{code}.png"
    return {
        "download_url": f"/api/stablecoins/in-person-pass/download?token={quote(token, safe='')}",
        "file_name": filename,
        "expires_in": PASS_TOKEN_TTL_SECONDS,
    }


async def in_person_pass_download(token: str):
    payload = _verify_pass_token(token)
    try:
        card_bytes = await in_person_pass_service.generate_in_person_pass(
            payload["action"], payload["asset"], payload["code"]
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="ساخت کارت مراجعه ناموفق بود.") from exc

    filename = f"saraf-{payload['action']}-{payload['asset']}-{payload['code']}.png"
    return Response(
        content=card_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Allow-Origin": "https://web.telegram.org",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def card_preview(
    payload: CardPreviewRequest,
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    user = _authenticate(x_telegram_init_data)
    if payload.action not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="نوع معامله نامعتبر است.")

    try:
        asset = usdt_service.normalize_asset(payload.asset)
        quote_row = quote_service.load_and_validate(
            user["id"], payload.quote_id, payload.action, payload.amount, asset=asset
        )
        network = stablecoin_networks.validate_network(
            asset, payload.network, direction=payload.action
        )
    except (usdt_service.StablecoinAssetError, quote_service.QuoteError, ValueError) as exc:
        message = getattr(exc, "message", str(exc))
        raise HTTPException(status_code=400, detail=message)

    if not payload.exchange_name.strip():
        raise HTTPException(status_code=400, detail="نام صرافی یا کیف پول الزامی است.")

    if payload.action == "buy":
        try:
            address = wallet_validator.validate_wallet_address(network, payload.wallet_address or "")
        except wallet_validator.WalletValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        deposit_address = None
        wallet_address = address
    else:
        deposit_address = stablecoin_networks.get_deposit_wallet(asset, network)
        if not deposit_address:
            raise HTTPException(
                status_code=400,
                detail=f"آدرس دریافت صراف برای {asset} روی شبکهٔ {network} تنظیم نشده است.",
            )
        wallet_address = None

    profile = db.get_user_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=403, detail="ابتدا پروفایل خود را تکمیل کنید.")

    risk_level, _ = risk_engine.assess_risk(profile, payload.amount)
    order_preview = {
        "order_type": payload.action,
        "asset": asset,
        "usdt_amount": float(quote_row["usdt_amount"]),
        "usd_rate": float(quote_row["usd_rate"]),
        "fee_percent": float(quote_row.get("fee_percent") or 0),
        "total_afn": float(quote_row["total_afn"]),
        "total_usd": float(quote_row["total_usd"]),
        "exchange_name": payload.exchange_name.strip(),
        "network": network,
        "wallet_address": wallet_address,
        "deposit_address": deposit_address,
        "risk_level": risk_level,
    }
    card_bytes = await stablecoin_card_service.generate_order_card_preview(order_preview, profile)
    if not card_bytes:
        raise HTTPException(status_code=503, detail="ساخت پیش‌نمایش کارت ناموفق بود.")
    return Response(content=card_bytes, media_type="image/png", headers={"Cache-Control": "no-store"})


def install() -> None:
    if getattr(FastAPI, "_saraf_stablecoin_extension_installed", False):
        return
    original_init = FastAPI.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.add_api_route(
            "/api/stablecoins/config",
            stablecoin_config,
            methods=["GET"],
            name="stablecoin_config",
        )
        self.add_api_route(
            "/api/stablecoins/in-person-pass-link",
            in_person_pass_link,
            methods=["POST"],
            name="stablecoin_in_person_pass_link",
        )
        self.add_api_route(
            "/api/stablecoins/in-person-pass/download",
            in_person_pass_download,
            methods=["GET"],
            name="stablecoin_in_person_pass_download",
        )
        self.add_api_route(
            "/api/stablecoins/card-preview",
            card_preview,
            methods=["POST"],
            name="stablecoin_card_preview",
        )

    FastAPI.__init__ = patched_init
    FastAPI._saraf_stablecoin_extension_installed = True
