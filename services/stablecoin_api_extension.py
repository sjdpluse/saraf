"""Additional Mini App endpoints installed without renaming legacy /api/usdt routes."""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from config import BOT_TOKEN
from services import (
    quote_service,
    risk_engine,
    stablecoin_card_service,
    stablecoin_networks,
    supabase_service as db,
    usdt_service,
    wallet_validator,
    webapp_auth,
)


class CardPreviewRequest(BaseModel):
    action: str
    asset: str = "USDT"
    amount: float
    quote_id: int
    exchange_name: str
    network: str
    wallet_address: Optional[str] = None


def _authenticate(init_data: Optional[str]) -> dict:
    try:
        return webapp_auth.verify_init_data(init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


async def stablecoin_config(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    _authenticate(x_telegram_init_data)
    return stablecoin_networks.public_config()


async def card_preview(
    payload: CardPreviewRequest,
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
):
    user = _authenticate(x_telegram_init_data)
    if payload.action not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="نوع معامله نامعتبر است.")

    try:
        asset = usdt_service.normalize_asset(payload.asset)
        quote = quote_service.load_and_validate(
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
        "usdt_amount": float(quote["usdt_amount"]),
        "usd_rate": float(quote["usd_rate"]),
        "fee_percent": float(quote.get("fee_percent") or 0),
        "total_afn": float(quote["total_afn"]),
        "total_usd": float(quote["total_usd"]),
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
            "/api/stablecoins/card-preview",
            card_preview,
            methods=["POST"],
            name="stablecoin_card_preview",
        )

    FastAPI.__init__ = patched_init
    FastAPI._saraf_stablecoin_extension_installed = True
