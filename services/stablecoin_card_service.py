"""Asset-aware wrapper around the original customer-card renderer.

This module deliberately does NOT redesign the card. The original Apple Wallet /
bento renderer in services/card_service.py remains the single visual renderer.
Only asset-specific strings and the order-code prefix are substituted while the
card is being generated.
"""
from __future__ import annotations

import contextvars
from typing import Optional

from services import card_service

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

        # Preview applies to both assets. The visual card stays identical; only
        # the not-yet-created order code is replaced with a neutral placeholder.
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


async def _render(order: dict, profile: dict, *, preview: bool) -> Optional[bytes]:
    asset = _normalize_asset(order)
    token_asset = _asset_ctx.set(asset)
    token_preview = _preview_ctx.set(preview)
    try:
        payload = dict(order)
        payload["asset"] = asset
        if preview:
            payload["id"] = 0
        return await card_service.generate_order_card(payload, profile)
    finally:
        _preview_ctx.reset(token_preview)
        _asset_ctx.reset(token_asset)


async def generate_order_card(order: dict, profile: dict) -> Optional[bytes]:
    return await _render(order, profile, preview=False)


async def generate_order_card_preview(order: dict, profile: dict) -> Optional[bytes]:
    return await _render(order, profile, preview=True)
