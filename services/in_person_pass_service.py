from __future__ import annotations

import io
import logging
import os
from typing import Optional

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageOps

from services import usdt_service

logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
SARAF_LOGO = os.path.join(ROOT, "logosaraf.png")

IN_PERSON_ADDRESS = "کوته‌سنگی، همادی مارکیت، کابل، افغانستان"
REPRESENTATIVE_PHONE = "0790810632"
SUPPORT_PHONE = "0775146747"

ASSET_LOGOS = {
    "USDT": "https://i.postimg.cc/250WhXsF/tether.png",
    "USDC": "https://i.postimg.cc/0QndtT7N/usd-coin-usdc-logo.jpg",
}
_ASSET_CACHE: dict[str, bytes] = {}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS, name)
    try:
        return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        return ImageFont.truetype("DejaVuSans.ttf", size)


def _rtl(draw: ImageDraw.ImageDraw, xy, text: str, font, fill, anchor="mm") -> None:
    value = str(text)
    direction = "rtl" if any("\u0600" <= ch <= "\u06ff" for ch in value) else "ltr"
    try:
        draw.text(xy, value, font=font, fill=fill, anchor=anchor, direction=direction)
    except Exception:
        draw.text(xy, value, font=font, fill=fill, anchor=anchor)


def _fit_logo(image: Image.Image, size: int, *, circular: bool = False) -> Image.Image:
    source = image.convert("RGBA")
    source = ImageOps.contain(source, (size, size), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    x = (size - source.width) // 2
    y = (size - source.height) // 2
    canvas.alpha_composite(source, (x, y))
    if not circular:
        return canvas
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    out.paste(canvas, (0, 0), mask)
    return out


async def _asset_logo(asset: str) -> Optional[Image.Image]:
    if asset in _ASSET_CACHE:
        try:
            return Image.open(io.BytesIO(_ASSET_CACHE[asset])).convert("RGBA")
        except Exception:
            _ASSET_CACHE.pop(asset, None)
    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            response = await client.get(ASSET_LOGOS[asset])
            response.raise_for_status()
        _ASSET_CACHE[asset] = response.content
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except Exception:
        logger.exception("Could not fetch %s logo for in-person pass", asset)
        return None


async def generate_in_person_pass(action: str, asset: str, code: str) -> bytes:
    selected_asset = usdt_service.normalize_asset(asset)
    if action not in ("buy", "sell"):
        raise ValueError("نوع مراجعه نامعتبر است.")
    if not str(code).isdigit() or len(str(code)) != 4:
        raise ValueError("کد مراجعه باید ۴ رقم باشد.")

    width, height = 1200, 760
    page = Image.new("RGBA", (width, height), (245, 245, 247, 255))
    draw = ImageDraw.Draw(page)

    # Card + subtle header surface
    draw.rounded_rectangle((70, 55, 1130, 705), radius=48, fill=(255, 255, 255, 255), outline=(225, 228, 234, 255), width=2)
    draw.rounded_rectangle((70, 55, 1130, 235), radius=48, fill=(242, 248, 255, 255))
    draw.rectangle((70, 185, 1130, 235), fill=(242, 248, 255, 255))

    # Saraf logo
    try:
        saraf = Image.open(SARAF_LOGO).convert("RGBA")
        saraf = _fit_logo(saraf, 82)
        page.alpha_composite(saraf, (112, 102))
    except Exception:
        logger.exception("Could not load Saraf logo for in-person pass")

    # Asset logo, with safe fallback badge
    asset_img = await _asset_logo(selected_asset)
    if asset_img is not None:
        asset_img = _fit_logo(asset_img, 76, circular=True)
        page.alpha_composite(asset_img, (1002, 104))
    else:
        badge_color = (38, 161, 123, 255) if selected_asset == "USDT" else (39, 117, 202, 255)
        draw.ellipse((1002, 104, 1078, 180), fill=badge_color)
        draw.text((1040, 142), selected_asset[0], font=_font("Vazirmatn-Black.ttf", 32), fill="white", anchor="mm")

    title_font = _font("Vazirmatn-Black.ttf", 34)
    medium = _font("Vazirmatn-Medium.ttf", 21)
    bold = _font("Vazirmatn-Bold.ttf", 25)
    code_font = _font("Vazirmatn-Black.ttf", 62)
    small = _font("Vazirmatn-Medium.ttf", 18)

    draw.text((220, 126), "SARAF", font=_font("Vazirmatn-Black.ttf", 34), fill=(29, 29, 31), anchor="la")
    _rtl(draw, (220, 168), "کارت مراجعهٔ حضوری", medium, (110, 110, 115), anchor="la")
    draw.text((1040, 205), selected_asset, font=_font("Vazirmatn-Bold.ttf", 21), fill=(29, 29, 31), anchor="mm")

    action_fa = "پرداخت حضوری" if action == "buy" else "دریافت حضوری"
    _rtl(draw, (600, 300), action_fa, title_font, (29, 29, 31))
    _rtl(draw, (600, 354), IN_PERSON_ADDRESS, medium, (110, 110, 115))

    draw.rounded_rectangle((380, 395, 820, 545), radius=28, fill=(244, 249, 255, 255), outline=(211, 228, 250, 255), width=2)
    _rtl(draw, (600, 430), "کد مراجعه", small, (110, 110, 115))
    draw.text((600, 498), str(code), font=code_font, fill=(0, 113, 227), anchor="mm", spacing=12)

    # Contact cells
    draw.rounded_rectangle((125, 585, 575, 665), radius=20, fill=(248, 248, 250, 255), outline=(232, 232, 235, 255), width=1)
    draw.rounded_rectangle((625, 585, 1075, 665), radius=20, fill=(248, 248, 250, 255), outline=(232, 232, 235, 255), width=1)
    _rtl(draw, (350, 608), "شماره نماینده صراف", small, (110, 110, 115))
    draw.text((350, 642), REPRESENTATIVE_PHONE, font=bold, fill=(29, 29, 31), anchor="mm")
    _rtl(draw, (850, 608), "پشتیبانی صراف", small, (110, 110, 115))
    draw.text((850, 642), SUPPORT_PHONE, font=bold, fill=(29, 29, 31), anchor="mm")

    out = io.BytesIO()
    page.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
