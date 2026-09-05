"""Asset-aware wrapper around the original customer-card renderer.

This module deliberately does NOT redesign the card. The original Apple Wallet /
bento renderer in services/card_service.py remains the single visual renderer.
Only asset-specific strings, the order-code prefix, and the verified deposit
address are adapted while the card is being generated.
"""
from __future__ import annotations

import contextvars
from typing import Optional

from services import card_service, stablecoin_networks

_asset_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("card_asset", default="USDT")
_preview_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar("card_preview", default=False)

_ASSET_FA = {"USDT": "تتر", "USDC": "USD Coin"}

if not getattr(card_service, "_stablecoin_asset_patch_installed", False):
    _original_rtl = card_service._rtl
    _original_fit_text = card_service._fit_text
    _original_pill_width = card_service._pill_width

    def _replace_asset_text(value) -> str:
        text = str(value)
        asset = _asset_ctx.get()
        if _preview_ctx.get():
            text = text.replace("USDT-00000", "PREVIEW")
        if asset == "USDT":
            return text
        text = text.replace("USDT", asset)
        text = text.replace("تتر", _ASSET_FA[asset])
        if _preview_ctx.get():
            text = text.replace(f"{asset}-00000", "PREVIEW")
        return text

    def _rtl(draw, xy, text, font, fill, anchor="ra"):
        return _original_rtl(draw, xy, _replace_asset_text(text), font, fill, anchor=anchor)

    def _fit_text(draw, text, font, max_width):
        return _original_fit_text(draw, _replace_asset_text(text), font, max_width)

    def _pill_width(draw, text, font, h_pad):
        return _original_pill_width(draw, _replace_asset_text(text), font, h_pad)

    card_service._rtl = _rtl
    card_service._fit_text = _fit_text
    card_service._pill_width = _pill_width
    card_service._stablecoin_asset_patch_installed = True


def _normalize_asset(order: dict) -> str:
    value = str(order.get("asset") or "USDT").strip().upper()
    return value if value in _ASSET_FA else "USDT"


def _normalized_payload(order: dict, asset: str, preview: bool) -> dict:
    payload = dict(order)
    payload["asset"] = asset

    # For sell cards, never trust the historical hard-coded EVM address that may
    # be present in the legacy order service. Resolve the address from the same
    # asset+network policy used by the Mini App/API. This preserves the old card
    # layout while making its QR/address correct for USDT or USDC.
    if payload.get("order_type") == "sell":
        real_deposit = stablecoin_networks.get_deposit_wallet(asset, payload.get("network"))
        payload["wallet_address"] = real_deposit or payload.get("deposit_address") or ""
        payload["deposit_address"] = real_deposit or payload.get("deposit_address") or ""

    if preview:
        payload["id"] = 0
    return payload


async def _render(order: dict, profile: dict, *, preview: bool) -> Optional[bytes]:
    asset = _normalize_asset(order)
    token_asset = _asset_ctx.set(asset)
    token_preview = _preview_ctx.set(preview)
    try:
        return await card_service.generate_order_card(_normalized_payload(order, asset, preview), profile)
    finally:
        _preview_ctx.reset(token_preview)
        _asset_ctx.reset(token_asset)


async def generate_order_card(order: dict, profile: dict) -> Optional[bytes]:
    return await _render(order, profile, preview=False)


async def generate_order_card_preview(order: dict, profile: dict) -> Optional[bytes]:
    return await _render(order, profile, preview=True)
