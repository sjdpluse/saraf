"""
تولید «کارت دیجیتال مشتری Saraf» — بعد از هر سفارش (خرید یا فروش)، یک کارت شامل
لوگوی Saraf، عکس (سلفی) کاربر، نام، جزئیات معامله و یک QR از آدرس دیپازیت ساخته
می‌شود. این کارت هم برای ادمین و هم برای خودِ کاربر ارسال می‌شود؛ کاربر می‌تواند
هنگام مراجعهٔ حضوری این کارت را به نمایندهٔ صراف نشان دهد تا اعتبار سفارشش تایید شود.

نکات فنی:
  - متن دری/فارسی با arabic_reshaper + python-bidi «شکل‌دهی» می‌شود، چون PIL به‌طور
    پیش‌فرض حروف فارسی را جدا از هم و بدون اتصال رسم می‌کند.
  - فونت از assets/fonts/Vazirmatn-*.ttf (همان فونتی که در پروژه موجود است) خوانده
    می‌شود.
  - تصویر سلفی از باکت خصوصی Supabase Storage دانلود و به‌صورت دایره‌یی برش می‌خورد.
"""
import asyncio
import io
import logging
import os
from typing import Optional

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps

from config import USDT_KYC_DOCS_BUCKET
from services import supabase_service as db

logger = logging.getLogger(__name__)

_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logosaraf.png")

_CARD_W, _CARD_H = 1200, 720

_COLOR_BG_TOP = (15, 23, 42)       # #0F172A
_COLOR_BG_BOTTOM = (30, 58, 95)    # #1E3A5F
_COLOR_CARD = (24, 35, 56)         # #182338
_COLOR_TEXT = (248, 250, 252)      # #F8FAFC
_COLOR_MUTED = (140, 160, 189)     # #8CA0BD
_COLOR_BUY = (5, 150, 105)         # #059669
_COLOR_SELL = (220, 38, 38)        # #DC2626


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(_FONTS_DIR, name)
    # layout_engine=RAQM از libraqm برای شکل‌دهی صحیح حروف فارسی/عربی (اتصال حروف +
    # راست‌به‌چپ) استفاده می‌کند؛ بدون این، حروف فارسی جدا و نامرتب رسم می‌شوند.
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def _has_persian(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06ff" for ch in str(text))


def _draw_text_rtl(draw: ImageDraw.ImageDraw, xy, text: str, font, fill, anchor="ra"):
    text = str(text)
    direction = "rtl" if _has_persian(text) else "ltr"
    draw.text(xy, text, font=font, fill=fill, anchor=anchor, direction=direction)


def _vertical_gradient(w: int, h: int, top: tuple, bottom: tuple) -> Image.Image:
    base = Image.new("RGBA", (w, h), (*top, 255))
    draw = ImageDraw.Draw(base)
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
    return base


def _rounded_mask(size: tuple, radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (size[0] - 1, size[1] - 1)], radius=radius, fill=255)
    return mask


def _circular(img: Image.Image, diameter: int) -> Image.Image:
    img = ImageOps.fit(img.convert("RGB"), (diameter, diameter), centering=(0.5, 0.4))
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter, diameter), fill=255)
    out = Image.new("RGBA", (diameter, diameter))
    out.paste(img, (0, 0), mask)
    return out


def _make_qr(data: str, box_size: int = 8) -> Image.Image:
    qr = qrcode.QRCode(border=1, box_size=box_size, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _build_card_sync(order: dict, profile: dict, selfie_bytes: Optional[bytes]) -> bytes:
    is_buy = order["order_type"] == "buy"
    accent = _COLOR_BUY if is_buy else _COLOR_SELL
    order_code = f"USDT-{order['id']:05d}"
    full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "کاربر Saraf"
    kyc_labels = {"pending": "در انتظار تایید", "verified": "هویت تایید‌شده", "trusted": "مشتری معتمد", "restricted": "محدودشده"}
    kyc_label = kyc_labels.get(profile.get("kyc_status"), "در انتظار تایید")

    card = _vertical_gradient(_CARD_W, _CARD_H, _COLOR_BG_TOP, _COLOR_BG_BOTTOM)
    draw = ImageDraw.Draw(card)

    # --- هدر: لوگو + برند ---
    try:
        logo = Image.open(_LOGO_PATH).convert("RGBA")
        logo.thumbnail((84, 84))
        card.paste(logo, (44, 40), logo)
    except Exception:
        logger.exception("خطا در بارگذاری لوگوی Saraf برای کارت")

    font_brand = _font("Vazirmatn-Bold.ttf", 34)
    font_sub = _font("Vazirmatn-Medium.ttf", 20)
    _draw_text_rtl(draw, (150, 46), "Saraf", font_brand, _COLOR_TEXT, anchor="la")
    _draw_text_rtl(draw, (150, 90), "کارت مشتری معتبر", font_sub, _COLOR_MUTED, anchor="la")

    # --- برچسب نوع معامله (بالا-راست) ---
    badge_text = "خرید تتر" if is_buy else "فروش تتر"
    font_badge = _font("Vazirmatn-Bold.ttf", 24)
    badge_w = 220
    draw.rounded_rectangle(
        [(_CARD_W - 44 - badge_w, 40), (_CARD_W - 44, 88)], radius=20, fill=accent
    )
    _draw_text_rtl(draw, (_CARD_W - 44 - badge_w / 2, 64), badge_text, font_badge, (255, 255, 255), anchor="mm")

    # --- خط جداکننده (نیمه‌شفاف — با ترکیب صحیح آلفا روی یک لایهٔ جدا) ---
    divider_overlay = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(divider_overlay).line([(44, 150), (_CARD_W - 44, 150)], fill=(255, 255, 255, 40), width=2)
    card = Image.alpha_composite(card, divider_overlay)
    draw = ImageDraw.Draw(card)

    # --- عکس سلفی (دایره‌یی) ---
    avatar_d = 190
    avatar_pos = (44, 190)
    if selfie_bytes:
        try:
            selfie_img = Image.open(io.BytesIO(selfie_bytes))
            circ = _circular(selfie_img, avatar_d)
            ring = Image.new("RGBA", (avatar_d + 10, avatar_d + 10), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((0, 0, avatar_d + 10, avatar_d + 10), outline=accent, width=4)
            card.paste(ring, (avatar_pos[0] - 5, avatar_pos[1] - 5), ring)
            card.paste(circ, avatar_pos, circ)
        except Exception:
            logger.exception("خطا در پردازش عکس سلفی برای کارت")
            selfie_bytes = None
    if not selfie_bytes:
        placeholder = Image.new("RGBA", (avatar_d, avatar_d), (*_COLOR_CARD, 255))
        pd = ImageDraw.Draw(placeholder)
        pd.ellipse((0, 0, avatar_d, avatar_d), fill=_COLOR_CARD)
        font_ph = _font("Vazirmatn-Bold.ttf", 70)
        initial = (full_name[0] if full_name else "S").upper()
        pd.text((avatar_d / 2, avatar_d / 2), initial, font=font_ph, fill=_COLOR_MUTED, anchor="mm")
        mask = Image.new("L", (avatar_d, avatar_d), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_d, avatar_d), fill=255)
        card.paste(placeholder, avatar_pos, mask)

    # --- نام و وضعیت کنار عکس ---
    name_x = avatar_pos[0] + avatar_d + 34
    font_name = _font("Vazirmatn-Bold.ttf", 38)
    font_kyc = _font("Vazirmatn-SemiBold.ttf", 22)
    _draw_text_rtl(draw, (name_x, 210), full_name, font_name, _COLOR_TEXT, anchor="la")
    _draw_text_rtl(draw, (name_x, 260), kyc_label, font_kyc, accent, anchor="la")
    font_phone = _font("Vazirmatn-Regular.ttf", 22)
    phone = profile.get("phone") or "-"
    draw.text((name_x, 300), phone, font=font_phone, fill=_COLOR_MUTED, anchor="la")

    # --- جعبهٔ جزئیات معامله (نیمه‌شفاف — با ترکیب صحیح آلفا) ---
    box_y = 410
    box_overlay = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(box_overlay).rounded_rectangle(
        [(44, box_y), (_CARD_W - 320, _CARD_H - 44)], radius=18, fill=(255, 255, 255, 22)
    )
    card = Image.alpha_composite(card, box_overlay)
    draw = ImageDraw.Draw(card)

    font_label = _font("Vazirmatn-Regular.ttf", 20)
    font_value = _font("Vazirmatn-Bold.ttf", 26)

    rows = [
        ("مقدار", f"{order['usdt_amount']:g} USDT"),
        ("مبلغ", f"{order['total_afn']:,.0f} افغانی"),
        ("صرافی / شبکه", f"{order.get('exchange_name') or '-'} / {order.get('network') or '-'}"),
        ("کد سفارش", order_code),
    ]
    ry = box_y + 30
    for label, value in rows:
        _draw_text_rtl(draw, (_CARD_W - 340, ry), label, font_label, _COLOR_MUTED, anchor="ra")
        draw.text((70, ry), value, font=font_value, fill=_COLOR_TEXT, anchor="la")
        ry += 58

    # --- QR کد آدرس دیپازیت (سمت چپ پایین) ---
    deposit_address = order.get("wallet_address") or order.get("deposit_address") or ""
    if deposit_address:
        qr_img = _make_qr(deposit_address, box_size=6)
        qr_size = 220
        qr_img = qr_img.resize((qr_size, qr_size))
        qr_bg_pos = (_CARD_W - 300, box_y)
        draw.rounded_rectangle(
            [qr_bg_pos, (qr_bg_pos[0] + qr_size + 40, qr_bg_pos[1] + qr_size + 70)], radius=18, fill=(255, 255, 255)
        )
        card.paste(qr_img, (qr_bg_pos[0] + 20, qr_bg_pos[1] + 20))
        font_qr_label = _font("Vazirmatn-SemiBold.ttf", 18)
        _draw_text_rtl(
            draw,
            (qr_bg_pos[0] + 20 + qr_size / 2, qr_bg_pos[1] + qr_size + 45),
            "آدرس دیپازیت",
            font_qr_label,
            (30, 41, 59),
            anchor="mm",
        )

    # --- فوتر ---
    font_footer = _font("Vazirmatn-Regular.ttf", 18)
    _draw_text_rtl(
        draw,
        (_CARD_W / 2, _CARD_H - 18),
        "این کارت صرفاً برای شناسایی مشتری نزد نمایندگان Saraf معتبر است  •  پشتیبانی: @SJDPLUS",
        font_footer,
        _COLOR_MUTED,
        anchor="mm",
    )

    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def generate_order_card(order: dict, profile: dict) -> Optional[bytes]:
    """نسخهٔ async — پردازش تصویر (CPU-bound) در ترد جدا اجرا می‌شود تا event loop بلاک نشود."""
    try:
        selfie_bytes = None
        selfie_path = profile.get("selfie_path")
        if selfie_path:
            selfie_bytes = await asyncio.to_thread(db.download_private_file, USDT_KYC_DOCS_BUCKET, selfie_path)
        return await asyncio.to_thread(_build_card_sync, order, profile, selfie_bytes)
    except Exception:
        logger.exception("خطا در تولید کارت دیجیتال سفارش")
        return None
