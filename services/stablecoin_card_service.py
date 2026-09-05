"""Asset-aware digital customer card for USDT / USDC orders."""
import asyncio
import io
import logging
import os
from typing import Optional
from urllib.request import Request, urlopen

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps

from config import USDT_KYC_DOCS_BUCKET
from services import supabase_service as db

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONTS = os.path.join(_ROOT, "assets", "fonts")
_SARAF_LOGO = os.path.join(_ROOT, "logosaraf.png")
_ASSET_LOGOS = {
    "USDT": "https://i.postimg.cc/250WhXsF/tether.png",
    "USDC": "https://i.postimg.cc/0QndtT7N/usd-coin-usdc-logo.jpg",
}
_ASSET_NAMES = {"USDT": "تتر", "USDC": "یو‌اس‌دی کوین"}

W, H = 1320, 900
BG = (245, 245, 247)
CARD = (255, 255, 255)
TEXT = (29, 29, 31)
MUTED = (110, 110, 115)
BLUE = (0, 113, 227)
GREEN = (28, 166, 76)
RED = (220, 55, 48)
BORDER = (224, 224, 229)


def _font(name: str, size: int):
    return ImageFont.truetype(os.path.join(_FONTS, name), size, layout_engine=ImageFont.Layout.RAQM)


def _rtl(draw, xy, text, font, fill, anchor="ra"):
    text = str(text)
    direction = "rtl" if any("\u0600" <= c <= "\u06ff" for c in text) else "ltr"
    draw.text(xy, text, font=font, fill=fill, anchor=anchor, direction=direction)


def _asset(order: dict) -> str:
    value = str(order.get("asset") or "USDT").upper()
    return value if value in _ASSET_LOGOS else "USDT"


def _order_code(order: dict, asset: str) -> str:
    return f"{asset}-{int(order['id']):05d}"


def _rounded_photo(data: bytes, size: int) -> Optional[Image.Image]:
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img = ImageOps.fit(img, (size, size), centering=(0.5, 0.4))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        out = Image.new("RGBA", (size, size))
        out.paste(img, (0, 0), mask)
        return out
    except Exception:
        logger.exception("Could not render profile photo on order card")
        return None


def _load_asset_logo(asset: str) -> Optional[Image.Image]:
    try:
        req = Request(_ASSET_LOGOS[asset], headers={"User-Agent": "Saraf/1.0"})
        with urlopen(req, timeout=4) as response:
            data = response.read(2 * 1024 * 1024)
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img.thumbnail((86, 86))
        return img
    except Exception:
        logger.warning("Could not load %s logo for customer card; text fallback will be used", asset)
        return None


def _qr(data: str, size: int = 220) -> Image.Image:
    code = qrcode.QRCode(border=1, box_size=7, error_correction=qrcode.constants.ERROR_CORRECT_M)
    code.add_data(data)
    code.make(fit=True)
    return code.make_image(fill_color=TEXT, back_color="white").convert("RGB").resize((size, size))


def _fit(draw, text: str, font, width: int) -> str:
    text = str(text)
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text + "…"


def _cell(draw, box, title, value, value_color=TEXT, value_size=29):
    draw.rounded_rectangle(box, radius=24, fill=(248, 248, 250), outline=BORDER, width=2)
    _rtl(draw, (box[2] - 22, box[1] + 20), title, _font("Vazirmatn-Medium.ttf", 17), MUTED)
    value_font = _font("Vazirmatn-Bold.ttf", value_size)
    value = _fit(draw, value, value_font, box[2] - box[0] - 44)
    _rtl(draw, (box[2] - 22, box[3] - 24), value, value_font, value_color, anchor="rd")


def _build(order: dict, profile: dict, selfie_bytes: Optional[bytes]) -> bytes:
    asset = _asset(order)
    asset_name = _ASSET_NAMES[asset]
    is_buy = order.get("order_type") == "buy"
    accent = GREEN if is_buy else RED
    code = _order_code(order, asset)

    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((44, 44, W - 44, H - 44), radius=44, fill=CARD, outline=BORDER, width=2)

    # Header / Saraf identity
    try:
        logo = Image.open(_SARAF_LOGO).convert("RGBA")
        logo.thumbnail((64, 64))
        canvas.paste(logo, (92, 88), logo)
    except Exception:
        logger.exception("Could not load Saraf logo")
    _rtl(draw, (174, 92), "صراف", _font("Vazirmatn-Black.ttf", 30), TEXT, anchor="la")
    _rtl(draw, (174, 130), "کارت دیجیتال مشتری", _font("Vazirmatn-Medium.ttf", 18), MUTED, anchor="la")

    # Selected asset identity — uses the exact URL configured by the product.
    asset_logo = _load_asset_logo(asset)
    if asset_logo:
        canvas.paste(asset_logo, (W - 186, 82), asset_logo)
    _rtl(draw, (W - 202, 96), asset, _font("Vazirmatn-Black.ttf", 30), BLUE, anchor="ra")
    _rtl(draw, (W - 202, 132), asset_name, _font("Vazirmatn-Medium.ttf", 17), MUTED, anchor="ra")
    draw.line((92, 180, W - 92, 180), fill=BORDER, width=2)

    # Customer identity
    full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "کاربر صراف"
    avatar = _rounded_photo(selfie_bytes, 138) if selfie_bytes else None
    if avatar:
        canvas.paste(avatar, (94, 218), avatar)
    else:
        draw.ellipse((94, 218, 232, 356), fill=(235, 244, 255))
        initial = full_name[0] if full_name else "ص"
        draw.text((163, 288), initial, font=_font("Vazirmatn-Bold.ttf", 52), fill=BLUE, anchor="mm")

    _rtl(draw, (264, 232), full_name, _font("Vazirmatn-Bold.ttf", 31), TEXT, anchor="la")
    phone = profile.get("phone") or "-"
    draw.text((264, 282), str(phone), font=_font("Vazirmatn-Regular.ttf", 18), fill=MUTED, anchor="la", direction="ltr")
    badge = f"{'خرید' if is_buy else 'فروش'} {asset}"
    draw.rounded_rectangle((264, 318, 468, 364), radius=23, fill=(236, 248, 240) if is_buy else (255, 240, 239))
    _rtl(draw, (366, 341), badge, _font("Vazirmatn-Bold.ttf", 18), accent, anchor="mm")

    amount = float(order.get("usdt_amount") or 0)
    total_afn = float(order.get("total_afn") or 0)
    rate = float(order.get("usd_rate") or 0)
    exchange = order.get("exchange_name") or "-"
    network = order.get("network") or "-"

    left = 92
    grid_top = 410
    grid_right = 900
    gap = 20
    cell_w = (grid_right - left - gap) // 2
    cell_h = 132
    _cell(draw, (left, grid_top, left + cell_w, grid_top + cell_h), f"مقدار {asset}", f"{amount:g} {asset}", accent)
    _cell(draw, (left + cell_w + gap, grid_top, grid_right, grid_top + cell_h), "مبلغ کل", f"{total_afn:,.0f} AFN")
    _cell(draw, (left, grid_top + cell_h + gap, left + cell_w, grid_top + cell_h * 2 + gap), "صرافی / شبکه", f"{exchange} / {network}", TEXT, 20)
    _cell(draw, (left + cell_w + gap, grid_top + cell_h + gap, grid_right, grid_top + cell_h * 2 + gap), "نرخ هر دالر", f"{rate:,.2f} AFN", TEXT, 24)

    # QR / code
    right_x = 940
    address = order.get("wallet_address") or order.get("deposit_address") or ""
    draw.rounded_rectangle((right_x, 218, W - 92, 558), radius=26, fill=(244, 249, 255), outline=BORDER, width=2)
    if address:
        qr_img = _qr(str(address))
        canvas.paste(qr_img, (right_x + 55, 250))
        _rtl(draw, ((right_x + W - 92) / 2, 500), "آدرس واریز — اسکن کنید", _font("Vazirmatn-Medium.ttf", 16), MUTED, anchor="mm")
    else:
        _rtl(draw, ((right_x + W - 92) / 2, 385), "بدون آدرس واریز", _font("Vazirmatn-Medium.ttf", 17), MUTED, anchor="mm")

    draw.rounded_rectangle((right_x, 580, W - 92, 706), radius=24, fill=(248, 248, 250), outline=BORDER, width=2)
    _rtl(draw, (W - 114, 602), "کد سفارش", _font("Vazirmatn-Medium.ttf", 16), MUTED)
    draw.text((W - 114, 650), code, font=_font("Vazirmatn-Bold.ttf", 25), fill=TEXT, anchor="ra", direction="ltr")

    draw.rounded_rectangle((92, 746, W - 92, 810), radius=32, fill=(0, 64, 201))
    _rtl(draw, (W / 2, 778), f"پیگیری سفارش {asset} در ربات صراف", _font("Vazirmatn-Bold.ttf", 20), (255, 255, 255), anchor="mm")

    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


async def generate_order_card(order: dict, profile: dict) -> Optional[bytes]:
    try:
        selfie_bytes = None
        selfie_path = profile.get("selfie_path")
        if selfie_path:
            selfie_bytes = await asyncio.to_thread(db.download_private_file, USDT_KYC_DOCS_BUCKET, selfie_path)
        return await asyncio.to_thread(_build, order, profile, selfie_bytes)
    except Exception:
        logger.exception("خطا در تولید کارت دیجیتال سفارش USDT/USDC")
        return None
