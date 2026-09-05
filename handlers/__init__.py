"""Handler package bootstrap.

The production path opens the Mini App, but the legacy conversational fallback
must obey the same asset/network policy. This patch keeps the existing handler
API stable while replacing only its network selection/deposit-address behavior.
"""
from __future__ import annotations

import contextvars

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from handlers import usdt as _usdt
from services import stablecoin_networks

_current_asset: contextvars.ContextVar[str] = contextvars.ContextVar(
    "telegram_stablecoin_asset", default="USDT"
)

_original_asset = _usdt._asset


def _asset_with_context(context):
    asset = _original_asset(context)
    _current_asset.set(asset)
    return asset


def _safe_network_keyboard(action: str) -> InlineKeyboardMarkup:
    asset = _current_asset.get()
    networks = (
        stablecoin_networks.get_buy_networks(asset)
        if action == "buy"
        else stablecoin_networks.get_sell_networks(asset)
    )

    rows = [
        [
            InlineKeyboardButton(
                item["label"],
                callback_data=f"usdt_net:{action}:{item['code']}",
            )
        ]
        for item in networks
    ]
    if networks:
        rows.append(
            [
                InlineKeyboardButton(
                    "✏️ وارد کردن نام شبکه",
                    callback_data=f"usdt_net:{action}:other",
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    f"⚠️ شبکهٔ فعال برای فروش {asset} تنظیم نشده",
                    callback_data=f"usdt_net:{action}:__none__",
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


async def _safe_after_network_selected(send_func, context, action: str, network: str) -> None:
    asset = _usdt._asset(context)
    try:
        selected_network = stablecoin_networks.validate_network(
            asset,
            network,
            direction=action,
        )
    except ValueError as exc:
        await send_func(
            f"⚠️ {exc}\n\nلطفاً یک شبکهٔ معتبر برای {asset} انتخاب کنید.",
            reply_markup=_safe_network_keyboard(action),
        )
        return

    context.user_data[_usdt.NETWORK] = selected_network

    if action == "buy":
        context.user_data[_usdt.AWAITING_WALLET] = True
        await send_func(
            f"شبکهٔ انتخابی: *{selected_network}*\n\n"
            f"آدرس ولت خود برای دریافت {asset} در همین شبکه را ارسال کنید.",
            parse_mode="Markdown",
        )
        return

    deposit_wallet = stablecoin_networks.get_deposit_wallet(asset, selected_network)
    if not deposit_wallet:
        await send_func(
            f"⚠️ آدرس دریافت صراف برای {asset} روی شبکهٔ {selected_network} تنظیم نشده است.",
            reply_markup=_safe_network_keyboard("sell"),
        )
        return

    context.user_data[_usdt.AWAITING_TX_PROOF] = True
    amount = context.user_data.get(_usdt.AMOUNT, 0)
    await send_func(
        f"مقدار *{amount:g} {asset}* را به آدرس زیر در شبکهٔ *{selected_network}* ارسال کنید:\n\n"
        f"`{deposit_wallet}`\n\n"
        "⚠️ دارایی، شبکه و آدرس را دقیقاً بررسی کنید. انتقال روی شبکهٔ اشتباه ممکن است قابل بازیابی نباشد.\n\n"
        "پس از انتقال، *TxID* یا *عکس رسید تراکنش* را ارسال کنید.",
        parse_mode="Markdown",
    )


# Monkey-patch only the legacy fallback hooks. Mini App/API use the same
# stablecoin_networks service directly, so both paths share one policy.
_usdt._asset = _asset_with_context
_usdt.usdt_network_keyboard = _safe_network_keyboard
_usdt._after_network_selected = _safe_after_network_selected
