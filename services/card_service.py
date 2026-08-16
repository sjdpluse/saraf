"""
تولید «کارت دیجیتال مشتری Saraf» — نسخهٔ روشن، به سبک بصری Apple Card / Apple Wallet
(بنتو‌گرید تمیز، هالهٔ رنگی محو پشت کارت سفید، سایه‌های نرم). بعد از هر سفارش
(خرید یا فروش)، یک کارت شامل لوگوی Saraf، عکس (سلفی) کاربر، نام، جزئیات معامله و
QR آدرس دیپازیت ساخته می‌شود و هم برای ادمین و هم برای خودِ کاربر ارسال می‌شود.

نکات فنی:
  - متن دری/فارسی با انجین RAQM (اتصال حروف + راست‌به‌چپ) رسم می‌شود.
  - پالت رنگ دقیقاً از webapp/src/index.css («Saraf Design System — روشن، آبی،
    شیشه‌یی، الهام از Apple») گرفته شده تا کارت تلگرام و مینی‌اپ یک برند واحد باشند.
  - تمام شکل‌های نیمه‌شفاف (هاله، پیل‌ها، جعبه‌های بنتو) روی یک لایهٔ RGBA جدا رسم و
    با alpha_composite ترکیب می‌شوند تا آلفا درست ترکیب شود.
"""
import asyncio
import io
import logging
import os
from typing import Optional

import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from config import USDT_KYC_DOCS_BUCKET
from services import supabase_service as db

logger = logging.getLogger(__name__)

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logosaraf.png")

# ============================================================================
# پالت — عیناً از توکن‌های webapp/src/index.css (Saraf Design System)
# ============================================================================
_PAGE_BG = (245, 245, 247)          # --color-bg
_CARD_BG = (255, 255, 255)          # --color-card
_BORDER = (0, 0, 0, 14)             # --color-border
_TEXT = (29, 29, 31)                # --color-text
_TEXT_MUTED = (110, 110, 115)       # --color-text-muted
_TEXT_FAINT = (174, 174, 180)       # --color-text-faint

_PRIMARY = (0, 113, 227)            # --color-primary
_PRIMARY_LIGHT = (10, 132, 255)     # --color-primary-light
_PRIMARY_DARK = (0, 64, 201)        # --color-primary-dark
_MINT = (48, 209, 200)              # لهجهٔ تزیینی برای هاله (شیمر اپلی)

_BUY = (28, 166, 76)
_BUY_BG = (52, 199, 89, 30)
_SELL = (255, 59, 48)
_SELL_BG = (255, 59, 48, 26)
_GOLD = (168, 120, 24)
_GOLD_BG = (255, 176, 32, 40)

_KYC_STYLE = {
    "pending":    ("در انتظار تایید", _TEXT_MUTED, (0, 0, 0, 12)),
    "verified":   ("هویت تایید‌شده", _PRIMARY, (0, 113, 227, 26)),
    "trusted":    ("مشتری معتمد",   _GOLD,    _GOLD_BG),
    "restricted": ("محدودشده",      _SELL,    _SELL_BG),
}

# ============================================================================
# هندسهٔ کارت (بنتو‌گرید)
# ============================================================================
_PAGE_W, _PAGE_H = 1320, 900
_RING = 46                                      # ضخامت هالهٔ رنگی دور کارت
_CARD_BOX = (_RING, _RING, _PAGE_W - _RING, _PAGE_H - _RING)
_CARD_W = _CARD_BOX[2] - _CARD_BOX[0]
_CARD_H = _CARD_BOX[3] - _CARD_BOX[1]
_OUTER_RADIUS = 60
_CARD_RADIUS = 44
_CELL_RADIUS = 26

_PAD = 50
_CONTENT_X0 = _CARD_BOX[0] + _PAD
_CONTENT_Y0 = _CARD_BOX[1] + _PAD
_CONTENT_X1 = _CARD_BOX[2] - _PAD
_CONTENT_Y1 = _CARD_BOX[3] - _PAD

_RIGHT_COL_W = 300
_GUTTER = 40
_LEFT_X1 = _CONTENT_X1 - _RIGHT_COL_W - _GUTTER
_RIGHT_X0 = _LEFT_X1 + _GUTTER


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(_ASSETS_DIR, name)
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def _has_persian(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06ff" for ch in str(text))


def _rtl(draw: ImageDraw.ImageDraw, xy, text, font, fill, anchor="ra"):
    text = str(text)
    direction = "rtl" if _has_persian(text) else "ltr"
    draw.text(xy, text, font=font, fill=fill, anchor=anchor, direction=direction)


def _composite(base: Image.Image, draw_fn) -> Image.Image:
    """یک لایهٔ RGBA شفاف هم‌اندازهٔ base می‌سازد، draw_fn روی آن می‌کشد، و با
    ترکیب صحیح آلفا روی base سوار می‌کند — برای هر شکل نیمه‌شفاف (پیل، جعبهٔ
    بنتو، هاله) استفاده می‌شود."""
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(overlay))
    return Image.alpha_composite(base, overlay)


def _rounded_mask(size, radius) -> Image.Image:
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
    return qr.make_image(fill_color=_TEXT, back_color=(255, 255, 255)).convert("RGB")


def _fit_text(draw, text, font, max_width) -> str:
    """اگر متن از max_width عریض‌تر باشد، با «…» کوتاه می‌شود تا هرگز از جعبهٔ خودش
    بیرون نزند (مثلاً نام‌های خیلی بلند یا اسم صرافی‌های طولانی)."""
    text = str(text)
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return (text + "…") if text else "…"


def _pill_width(draw, text, font, h_pad):
    return draw.textlength(str(text), font=font) + h_pad * 2


def _draw_pill(base, draw, xy, text, font, fg, bg_rgba, h=44, h_pad=20):
    """پیل کوچک (مثل «Writer» / «Golden User» در طرح مرجع) — xy گوشهٔ راست-بالای پیل
    است چون متن و چیدمان راست‌به‌چپ است."""
    x_right, y_top = xy
    w = _pill_width(draw, text, font, h_pad)
    box = (x_right - w, y_top, x_right, y_top + h)
    base = _composite(base, lambda d: d.rounded_rectangle(box, radius=h // 2, fill=bg_rgba))
    draw = ImageDraw.Draw(base)
    _rtl(draw, (x_right - w / 2, y_top + h / 2), text, font, fg, anchor="mm")
    return base, box


def _bento_cell(base, box, fill=(247, 247, 249, 255), border=True):
    base = _composite(base, lambda d: d.rounded_rectangle(box, radius=_CELL_RADIUS, fill=fill))
    if border:
        base = _composite(base, lambda d: d.rounded_rectangle(box, radius=_CELL_RADIUS, outline=(0, 0, 0, 16), width=2))
    return base


def _build_halo(size) -> Image.Image:
    """هالهٔ رنگیِ محو پشت کارت — دقیقاً همان الهامِ طرح مرجع (Bento gradient glow)
    اما با پالت برند Saraf (آبی اپل + لهجهٔ نعنایی/طلایی) به‌جای رنگ‌های دلخواه."""
    w, h = size
    blobs = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(blobs)
    d.ellipse((-w * 0.15, -h * 0.25, w * 0.62, h * 0.62), fill=(*_PRIMARY_LIGHT, 235))
    d.ellipse((w * 0.42, h * 0.30, w * 1.15, h * 1.25), fill=(*_PRIMARY_DARK, 225))
    d.ellipse((w * 0.18, -h * 0.10, w * 0.85, h * 0.48), fill=(*_MINT, 150))
    d.ellipse((w * 0.60, -h * 0.15, w * 1.10, h * 0.40), fill=(*_GOLD, 110))
    blobs = blobs.filter(ImageFilter.GaussianBlur(60))
    mask = _rounded_mask(size, _OUTER_RADIUS)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(blobs, (0, 0), mask)
    return out


def _build_shadow(size, box, radius, blur=34, offset=(0, 16), alpha=70) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    shifted = (box[0] + offset[0], box[1] + offset[1], box[2] + offset[0], box[3] + offset[1])
    ImageDraw.Draw(layer).rounded_rectangle(shifted, radius=radius, fill=(20, 30, 48, alpha))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def _build_card_sync(order: dict, profile: dict, selfie_bytes: Optional[bytes]) -> bytes:
    is_buy = order["order_type"] == "buy"
    accent = _BUY if is_buy else _SELL
    accent_bg = _BUY_BG if is_buy else _SELL_BG
    order_code = f"USDT-{order['id']:05d}"
    full_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "کاربر Saraf"
    kyc_label, kyc_fg, kyc_bg = _KYC_STYLE.get(profile.get("kyc_status"), _KYC_STYLE["pending"])

    # --- صفحه (پس‌زمینهٔ روشن) + سایهٔ نرم زیر کارت + هالهٔ رنگی ---
    page = Image.new("RGBA", (_PAGE_W, _PAGE_H), (*_PAGE_BG, 255))
    page = Image.alpha_composite(page, _build_shadow((_PAGE_W, _PAGE_H), _CARD_BOX, _CARD_RADIUS))
    page = Image.alpha_composite(page, _build_halo((_PAGE_W, _PAGE_H)))

    # --- کارت سفید روی هاله (فقط لبهٔ حلقه‌یی هاله نمایان می‌ماند) ---
    card_mask = _rounded_mask((_CARD_W, _CARD_H), _CARD_RADIUS)
    white_card = Image.new("RGBA", (_CARD_W, _CARD_H), (*_CARD_BG, 255))
    page.paste(white_card, (_CARD_BOX[0], _CARD_BOX[1]), card_mask)
    base = page
    draw = ImageDraw.Draw(base)

    # ------------------------------------------------------------------ هدر
    try:
        logo = Image.open(_LOGO_PATH).convert("RGBA")
        logo.thumbnail((64, 64))
        base.paste(logo, (_CONTENT_X0, _CONTENT_Y0 - 4), logo)
    except Exception:
        logger.exception("خطا در بارگذاری لوگوی Saraf برای کارت")

    font_brand = _font("Vazirmatn-Black.ttf", 30)
    font_brand_sub = _font("Vazirmatn-Medium.ttf", 18)
    wordmark_x = _CONTENT_X0 + 76
    _rtl(draw, (wordmark_x, _CONTENT_Y0 - 2), "Saraf", font_brand, _TEXT, anchor="la")
    _rtl(draw, (wordmark_x, _CONTENT_Y0 + 34), "کارت دیجیتال مشتری", font_brand_sub, _TEXT_MUTED, anchor="la")

    # پیل نوع معامله (بالا-راست)
    font_badge = _font("Vazirmatn-Bold.ttf", 19)
    badge_text = "خرید تتر" if is_buy else "فروش تتر"
    base, badge_box = _draw_pill(base, draw, (_CONTENT_X1, _CONTENT_Y0 - 2), badge_text, font_badge,
                                  accent, (*accent_bg[:3], 34), h=42, h_pad=22)
    draw = ImageDraw.Draw(base)

    header_bottom = _CONTENT_Y0 + 92
    base = _composite(base, lambda d: d.line([(_CONTENT_X0, header_bottom), (_CONTENT_X1, header_bottom)],
                                              fill=(0, 0, 0, 18), width=2))
    draw = ImageDraw.Draw(base)

    # --------------------------------------------------------------- پروفایل
    avatar_d = 138
    avatar_pos = (_CONTENT_X0, header_bottom + 30)
    if selfie_bytes:
        try:
            selfie_img = Image.open(io.BytesIO(selfie_bytes))
            circ = _circular(selfie_img, avatar_d)
            ring = Image.new("RGBA", (avatar_d + 10, avatar_d + 10), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((0, 0, avatar_d + 10, avatar_d + 10), outline=accent, width=4)
            base.paste(ring, (avatar_pos[0] - 5, avatar_pos[1] - 5), ring)
            base.paste(circ, avatar_pos, circ)
        except Exception:
            logger.exception("خطا در پردازش عکس سلفی برای کارت")
            selfie_bytes = None
    if not selfie_bytes:
        placeholder = Image.new("RGBA", (avatar_d, avatar_d), (0, 0, 0, 0))
        pd = ImageDraw.Draw(placeholder)
        pd.ellipse((0, 0, avatar_d, avatar_d), fill=(*_PRIMARY, 24))
        font_ph = _font("Vazirmatn-Bold.ttf", 54)
        initial = (full_name[0] if full_name else "S").upper()
        pd.text((avatar_d / 2, avatar_d / 2 + 2), initial, font=font_ph, fill=_PRIMARY, anchor="mm")
        base.paste(placeholder, avatar_pos, placeholder)
        draw = ImageDraw.Draw(base)

    name_x = avatar_pos[0] + avatar_d + 30
    font_name = _font("Vazirmatn-Bold.ttf", 32)
    full_name_fit = _fit_text(draw, full_name, font_name, _LEFT_X1 - name_x)
    _rtl(draw, (name_x, avatar_pos[1] + 6), full_name_fit, font_name, _TEXT, anchor="la")

    # ردیف پیل‌ها (نوع KYC + امتیاز اعتماد) — دقیقا الهام‌گرفته از پیل‌های طرح مرجع
    font_pill = _font("Vazirmatn-SemiBold.ttf", 17)
    pill_y = avatar_pos[1] + 54
    px = name_x
    kyc_w = draw.textlength(kyc_label, font=font_pill) + 36
    base = _composite(base, lambda d, b=(px, pill_y, px + kyc_w, pill_y + 38): d.rounded_rectangle(b, radius=19, fill=kyc_bg))
    draw = ImageDraw.Draw(base)
    _rtl(draw, (px + kyc_w / 2, pill_y + 19), kyc_label, font_pill, kyc_fg, anchor="mm")
    px += kyc_w + 12

    trust = profile.get("trust_score")
    if trust is not None:
        trust_text = f"⭐ {trust}/100"
        trust_w = draw.textlength(trust_text, font=font_pill) + 36
        base = _composite(base, lambda d, b=(px, pill_y, px + trust_w, pill_y + 38): d.rounded_rectangle(b, radius=19, fill=(0, 0, 0, 10)))
        draw = ImageDraw.Draw(base)
        _rtl(draw, (px + trust_w / 2, pill_y + 19), trust_text, font_pill, _TEXT_MUTED, anchor="mm")

    font_phone = _font("Vazirmatn-Regular.ttf", 18)
    phone = profile.get("phone") or "-"
    draw.text((name_x, avatar_pos[1] + avatar_d - 26), phone, font=font_phone, fill=_TEXT_FAINT, anchor="la",
               direction="ltr")

    # -------------------------------------------------------- خط توضیح سفارش
    desc_y = avatar_pos[1] + avatar_d + 34
    font_desc = _font("Vazirmatn-Medium.ttf", 20)
    amount_txt = f"{order['usdt_amount']:g}"
    action_txt = "درخواست خرید" if is_buy else "درخواست فروش"
    desc = f"{action_txt} {amount_txt} USDT از طریق {order.get('exchange_name') or 'صرافی منتخب'} — شبکهٔ {order.get('network') or '-'}"
    desc = _fit_text(draw, desc, font_desc, _LEFT_X1 - _CONTENT_X0)
    _rtl(draw, (_CONTENT_X0, desc_y), desc, font_desc, _TEXT_MUTED, anchor="la")

    # ------------------------------------------------------------ گرید بنتو
    grid_y0 = desc_y + 46
    grid_y1 = _CONTENT_Y1 - 118  # جا برای فوتر (پیل + آیکون‌ها)
    gap = 22
    cell_w = (_LEFT_X1 - _CONTENT_X0 - gap) / 2
    row_h = (grid_y1 - grid_y0 - gap) / 2

    def stat_cell(box, label, value, value_color=_TEXT, value_font_size=30):
        nonlocal base, draw
        base = _bento_cell(base, box)
        draw = ImageDraw.Draw(base)
        font_lbl = _font("Vazirmatn-Medium.ttf", 17)
        font_val = _font("Vazirmatn-Bold.ttf", value_font_size)
        pad_in = 24
        max_w = (box[2] - box[0]) - pad_in * 2
        value_fit = _fit_text(draw, value, font_val, max_w)
        _rtl(draw, (box[2] - pad_in, box[1] + 20), label, font_lbl, _TEXT_MUTED, anchor="ra")
        _rtl(draw, (box[2] - pad_in, box[3] - 26), value_fit, font_val, value_color, anchor="rd")

    c1 = (_CONTENT_X0, grid_y0, _CONTENT_X0 + cell_w, grid_y0 + row_h)
    c2 = (_CONTENT_X0 + cell_w + gap, grid_y0, _LEFT_X1, grid_y0 + row_h)
    c3 = (_CONTENT_X0, grid_y0 + row_h + gap, _CONTENT_X0 + cell_w, grid_y1)
    c4 = (_CONTENT_X0 + cell_w + gap, grid_y0 + row_h + gap, _LEFT_X1, grid_y1)

    stat_cell(c1, "مقدار تتر", f"{order['usdt_amount']:g} USDT", accent, 30)
    stat_cell(c2, "مبلغ کل", f"{order['total_afn']:,.0f} AFN", _TEXT, 30)
    stat_cell(c3, "صرافی / شبکه", f"{order.get('exchange_name') or '-'} / {order.get('network') or '-'}", _TEXT, 20)
    rate = order.get("usd_rate")
    rate_txt = f"{rate:,.2f} AFN" if rate else "-"
    stat_cell(c4, "نرخ هر دلار", rate_txt, _TEXT, 24)

    # --------------------------------------------------------------- فوتر
    footer_y = grid_y1 + 26
    pill_h = 62
    icon_d = 62
    icons_w = icon_d * 2 + 16
    pill_box = (_CONTENT_X0, footer_y, _LEFT_X1 - icons_w - 16, footer_y + pill_h)
    base = _composite(base, lambda d: d.rounded_rectangle(pill_box, radius=pill_h // 2,
                                                            fill=(*_PRIMARY_DARK, 255)))
    draw = ImageDraw.Draw(base)
    font_cta = _font("Vazirmatn-Bold.ttf", 20)
    _rtl(draw, ((pill_box[0] + pill_box[2]) / 2, (pill_box[1] + pill_box[3]) / 2),
         "پیگیری سفارش در ربات @SarafBot", font_cta, (255, 255, 255), anchor="mm")

    def icon_circle_support(cx0):
        nonlocal base, draw
        box = (cx0, footer_y, cx0 + icon_d, footer_y + icon_d)
        base = _composite(base, lambda d: d.ellipse(box, fill=(247, 247, 249, 255), outline=(0, 0, 0, 16), width=2))
        draw = ImageDraw.Draw(base)
        font_icon = _font("Vazirmatn-Bold.ttf", 18)
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        draw.text((cx, cy), "SOS", font=font_icon, fill=_PRIMARY_DARK, anchor="mm")

    def icon_circle_check(cx0, ok):
        nonlocal base, draw
        box = (cx0, footer_y, cx0 + icon_d, footer_y + icon_d)
        fill = (*_BUY, 26) if ok else (0, 0, 0, 10)
        base = _composite(base, lambda d: d.ellipse(box, fill=fill, outline=(0, 0, 0, 16), width=2))
        draw = ImageDraw.Draw(base)
        if ok:
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            pts = [(cx - 13, cy + 1), (cx - 4, cy + 10), (cx + 15, cy - 12)]
            draw.line(pts, fill=_BUY, width=5, joint="curve")
        else:
            font_icon = _font("Vazirmatn-Bold.ttf", 26)
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            draw.text((cx, cy - 2), "…", font=font_icon, fill=_TEXT_MUTED, anchor="mm")

    icon_circle_support(pill_box[2] + 16)
    icon_circle_check(pill_box[2] + 16 + icon_d + 16, profile.get("kyc_status") in ("verified", "trusted"))

    # ---------------------------------------------------------- ستون راست: QR
    right_gap = 22
    qr_top = header_bottom + 26
    qr_box = (_RIGHT_X0, qr_top, _CONTENT_X1, qr_top + _RIGHT_COL_W)
    base = _bento_cell(base, qr_box, fill=(*_PRIMARY, 14))
    draw = ImageDraw.Draw(base)
    deposit_address = order.get("wallet_address") or order.get("deposit_address") or ""
    if deposit_address:
        qr_pad = 26
        qr_size = _RIGHT_COL_W - qr_pad * 2 - 34
        qr_img = _make_qr(deposit_address, box_size=6).resize((qr_size, qr_size))
        qr_chip = (qr_box[0] + qr_pad, qr_box[1] + qr_pad, qr_box[0] + qr_pad + qr_size + 20, qr_box[1] + qr_pad + qr_size + 20)
        base = _composite(base, lambda d: d.rounded_rectangle(qr_chip, radius=20, fill=(255, 255, 255, 255)))
        base.paste(qr_img, (qr_chip[0] + 10, qr_chip[1] + 10))
        draw = ImageDraw.Draw(base)
        font_qr_lbl = _font("Vazirmatn-SemiBold.ttf", 17)
        _rtl(draw, ((qr_box[0] + qr_box[2]) / 2, qr_chip[3] + 26), "آدرس دیپازیت — اسکن کنید",
             font_qr_lbl, _TEXT_MUTED, anchor="mm")
        font_addr = _font("Vazirmatn-Regular.ttf", 14)
        short_addr = deposit_address if len(deposit_address) <= 20 else deposit_address[:8] + "…" + deposit_address[-6:]
        draw.text(((qr_box[0] + qr_box[2]) / 2, qr_chip[3] + 54), short_addr, font=font_addr, fill=_TEXT_FAINT,
                   anchor="mm", direction="ltr")
    else:
        font_np = _font("Vazirmatn-Medium.ttf", 17)
        _rtl(draw, ((qr_box[0] + qr_box[2]) / 2, (qr_box[1] + qr_box[3]) / 2), "بدون آدرس دیپازیت",
             font_np, _TEXT_FAINT, anchor="mm")

    # زیر QR: کد سفارش، سپس چیپ وضعیت ریسک / معاملات موفق — هر دو تا کف ستون کشیده
    # می‌شوند تا فضای خالی نمانَد.
    remaining_top = qr_box[3] + right_gap
    remaining_h = _CONTENT_Y1 - remaining_top
    code_h = min(118, remaining_h * 0.42)
    code_box = (_RIGHT_X0, remaining_top, _CONTENT_X1, remaining_top + code_h)
    base = _bento_cell(base, code_box)
    draw = ImageDraw.Draw(base)
    font_code_lbl = _font("Vazirmatn-Medium.ttf", 16)
    font_code_val = _font("Vazirmatn-Bold.ttf", 26)
    _rtl(draw, (code_box[2] - 22, code_box[1] + 20), "کد سفارش", font_code_lbl, _TEXT_MUTED, anchor="ra")
    code_fit = _fit_text(draw, order_code, font_code_val, (code_box[2] - code_box[0]) - 44)
    draw.text((code_box[2] - 22, code_box[1] + 52), code_fit, font=font_code_val, fill=_TEXT, anchor="ra",
               direction="ltr")

    risk_box = (_RIGHT_X0, code_box[3] + right_gap, _CONTENT_X1, _CONTENT_Y1)
    base = _bento_cell(base, risk_box)
    draw = ImageDraw.Draw(base)
    risk_mid_y = (risk_box[1] + risk_box[3]) / 2
    font_risk_lbl = _font("Vazirmatn-Medium.ttf", 16)
    font_risk_val = _font("Vazirmatn-Bold.ttf", 22)
    _rtl(draw, (risk_box[2] - 22, risk_box[1] + 22), "معاملات موفق", font_risk_lbl, _TEXT_MUTED, anchor="ra")
    _rtl(draw, (risk_box[2] - 22, risk_box[1] + 50), f"{profile.get('successful_orders', 0)}", font_risk_val, _TEXT,
         anchor="ra")
    _rtl(draw, (risk_box[2] - 22, risk_mid_y + 14), "وضعیت ریسک", font_risk_lbl, _TEXT_MUTED, anchor="ra")
    risk_level = order.get("risk_level") or "low"
    risk_map = {"low": ("پایین", _BUY), "medium": ("متوسط", _GOLD), "high": ("بالا", _SELL)}
    risk_txt, risk_col = risk_map.get(risk_level, risk_map["low"])
    _rtl(draw, (risk_box[2] - 22, risk_mid_y + 42), risk_txt, font_risk_val, risk_col, anchor="ra")

    # --------------------------------------------------------------- خروجی
    buf = io.BytesIO()
    base.convert("RGB").save(buf, format="PNG", optimize=True)
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
