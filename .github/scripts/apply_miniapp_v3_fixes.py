from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one match, found {count}: {old[:120]!r}")
    write(path, text.replace(old, new, 1))


# ---------------------------------------------------------------------------
# Shared in-person constants + cryptographically stronger 4-digit generator
# ---------------------------------------------------------------------------
write("webapp/src/lib/inPerson.js", r'''export const IN_PERSON_ADDRESS = "کوته‌سنگی، همادی مارکیت، کابل، افغانستان";
export const IN_PERSON_REPRESENTATIVE_PHONE = "0790810632";
export const SARAF_SUPPORT_PHONE = "0775146747";

export function generateInPersonCode() {
  if (globalThis.crypto?.getRandomValues) {
    const value = new Uint32Array(1);
    globalThis.crypto.getRandomValues(value);
    return String(1000 + (value[0] % 9000));
  }
  return String(Math.floor(1000 + Math.random() * 9000));
}
''')


# ---------------------------------------------------------------------------
# Telegram-native file download wrapper (Bot API 8.0+), browser fallback
# ---------------------------------------------------------------------------
replace_once(
    "webapp/src/lib/telegram.js",
    '''export function openTelegramChat(username, draftText = "") {
  const wa = getWebApp();
  const cleanUsername = String(username || "").replace(/^@/, "");
  const query = draftText ? `?text=${encodeURIComponent(draftText)}` : "";
  const url = `https://t.me/${cleanUsername}${query}`;
  if (wa?.openTelegramLink) {
    wa.openTelegramLink(url);
  } else {
    window.open(url, "_blank");
  }
}
''',
    '''export function openTelegramChat(username, draftText = "") {
  const wa = getWebApp();
  const cleanUsername = String(username || "").replace(/^@/, "");
  const query = draftText ? `?text=${encodeURIComponent(draftText)}` : "";
  const url = `https://t.me/${cleanUsername}${query}`;
  if (wa?.openTelegramLink) {
    wa.openTelegramLink(url);
  } else {
    window.open(url, "_blank");
  }
}

export function downloadTelegramFile(url, fileName) {
  const wa = getWebApp();
  if (wa?.downloadFile) {
    return new Promise((resolve) => {
      let settled = false;
      const finish = (value) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeoutId);
        resolve(Boolean(value));
      };
      const timeoutId = window.setTimeout(() => finish(false), 30000);
      try {
        wa.downloadFile({ url, file_name: fileName }, (accepted) => finish(accepted));
      } catch (_) {
        finish(false);
      }
    });
  }

  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    document.body.appendChild(link);
    link.click();
    link.remove();
    return Promise.resolve(true);
  } catch (_) {
    return Promise.resolve(false);
  }
}
'''
)


# ---------------------------------------------------------------------------
# API client: request a signed HTTPS download URL for the visit card
# ---------------------------------------------------------------------------
replace_once(
    "webapp/src/lib/api.js",
    '''  getStablecoinConfig: () => request("/stablecoins/config"),

  getCardPreview: async ({ action, asset, amount, exchange_name, network, wallet_address }) => {''',
    '''  getStablecoinConfig: () => request("/stablecoins/config"),

  getInPersonPassLink: ({ action, asset, code }) =>
    request("/stablecoins/in-person-pass-link", {
      method: "POST",
      body: { action, asset: normalizeAsset(asset), code: String(code || "") },
    }),

  getCardPreview: async ({ action, asset, amount, exchange_name, network, wallet_address }) => {'''
)


# ---------------------------------------------------------------------------
# WhatsApp action button: only where explicitly rendered, no global footer
# ---------------------------------------------------------------------------
write("webapp/src/components/WhatsAppSupport.jsx", r'''import { WhatsappLogo } from "@phosphor-icons/react";
import { normalizeAsset } from "../lib/brand";

const WHATSAPP_QR_URL = "https://wa.me/qr/25MA3IJZTGQPE1";

function preparedText(mode, asset, orderCode) {
  if (mode === "tracking") {
    return `سلام، برای رهگیری سفارش Saraf پیام می‌دهم. کد سفارش: ${orderCode || ""}`.trim();
  }
  return `سلام، برای خرید و فروش ${normalizeAsset(asset)} در Saraf به پشتیبانی واتسپ نیاز دارم.`;
}

async function copyText(text) {
  try {
    await navigator.clipboard?.writeText(text);
    return;
  } catch (_) {}

  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  } catch (_) {}
}

async function openWhatsApp(text) {
  await copyText(text);
  const wa = window.Telegram?.WebApp;
  if (wa?.openLink) {
    wa.openLink(WHATSAPP_QR_URL);
  } else {
    window.open(WHATSAPP_QR_URL, "_blank", "noopener,noreferrer");
  }
}

export function WhatsAppActionButton({
  mode = "support",
  asset = "USDT",
  orderCode = "",
  label,
  className = "btn btn-outline whatsapp-action-btn",
}) {
  const text = preparedText(mode, asset, orderCode);
  const resolvedLabel = label || (mode === "tracking" ? "رهگیری واتسپ" : "پشتیبانی واتسپ");
  return (
    <button type="button" className={className} onClick={() => openWhatsApp(text)}>
      <WhatsappLogo size={18} weight="fill" /> {resolvedLabel}
    </button>
  );
}
''')


# ---------------------------------------------------------------------------
# In-person pass UI: cyber code animation + Telegram native real file download
# ---------------------------------------------------------------------------
write("webapp/src/components/InPersonPass.jsx", r'''import { useEffect, useState } from "react";
import { CheckCircle, DownloadSimple, MapPin, Phone, Warning } from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { downloadTelegramFile } from "../lib/telegram";
import { SARAF_LOGO_URL, assetLogo, normalizeAsset } from "../lib/brand";
import {
  IN_PERSON_ADDRESS,
  IN_PERSON_REPRESENTATIVE_PHONE,
  SARAF_SUPPORT_PHONE,
} from "../lib/inPerson";

const SCRAMBLE_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function CyberCode({ code }) {
  const finalChars = String(code || "").padStart(4, "0").slice(-4).split("");
  const [chars, setChars] = useState(finalChars.map(() => "0"));

  useEffect(() => {
    setChars(finalChars.map(() => "0"));
    const intervals = [];
    const timeouts = [];

    finalChars.forEach((finalChar, index) => {
      const interval = window.setInterval(() => {
        setChars((prev) => {
          const next = [...prev];
          next[index] = SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)];
          return next;
        });
      }, 52 + index * 7);
      intervals.push(interval);

      const timeout = window.setTimeout(() => {
        window.clearInterval(interval);
        setChars((prev) => {
          const next = [...prev];
          next[index] = finalChar;
          return next;
        });
      }, 620 + index * 260);
      timeouts.push(timeout);
    });

    return () => {
      intervals.forEach((id) => window.clearInterval(id));
      timeouts.forEach((id) => window.clearTimeout(id));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  return (
    <div className="cyber-code num" aria-label={`کد مراجعه ${code}`}>
      {chars.map((char, index) => <span key={index}>{char}</span>)}
    </div>
  );
}

export default function InPersonPass({
  action,
  asset,
  code,
  onContinue,
  buttonClass = "btn-primary",
  showError,
}) {
  const selectedAsset = normalizeAsset(asset);
  const [downloaded, setDownloaded] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const actionFa = action === "buy" ? "پرداخت حضوری" : "دریافت حضوری";
  const coinLogo = assetLogo(selectedAsset);

  useEffect(() => setDownloaded(false), [action, selectedAsset, code]);

  async function download() {
    setDownloading(true);
    try {
      const result = await api.getInPersonPassLink({ action, asset: selectedAsset, code });
      const absoluteUrl = new URL(result.download_url, window.location.origin).toString();
      const accepted = await downloadTelegramFile(absoluteUrl, result.file_name);
      if (!accepted) {
        showError?.("دانلود کارت تایید نشد. لطفاً دوباره روی «دانلود کارت مراجعه» بزنید و دانلود را تایید کنید.");
        return;
      }
      setDownloaded(true);
    } catch (err) {
      showError?.(err instanceof ApiError ? err.message : "دانلود کارت مراجعه ناموفق بود.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="inperson-pass-wrap animate-in">
      <div className="inperson-pass">
        <div className="inperson-pass-head">
          <div className="inperson-brand-lockup">
            <img src={SARAF_LOGO_URL} alt="Saraf" />
            <div><b>صراف</b><span>کارت مراجعهٔ حضوری</span></div>
          </div>
          <div className="inperson-asset-lockup">
            <img src={coinLogo} alt={selectedAsset} />
            <b className="num">{selectedAsset}</b>
          </div>
        </div>

        <div className="inperson-action">{actionFa}</div>
        <div className="inperson-address"><MapPin size={18} weight="fill" /><span>{IN_PERSON_ADDRESS}</span></div>
        <div className="inperson-code"><span>کد مراجعه</span><CyberCode code={code} /></div>

        <div className="inperson-contact-grid">
          <div className="inperson-contact-item">
            <Phone size={17} weight="fill" />
            <span>شماره نماینده صراف</span>
            <strong className="num">{IN_PERSON_REPRESENTATIVE_PHONE}</strong>
          </div>
          <div className="inperson-contact-item">
            <Phone size={17} weight="fill" />
            <span>پشتیبانی صراف</span>
            <strong className="num">{SARAF_SUPPORT_PHONE}</strong>
          </div>
        </div>
      </div>

      <button className="btn btn-secondary" onClick={download} disabled={downloading}>
        {downloading ? <span className="spinner" /> : downloaded ? <CheckCircle size={18} weight="fill" /> : <DownloadSimple size={18} weight="bold" />}
        {downloading ? "در حال آماده‌سازی دانلود..." : downloaded ? "دانلود تایید شد" : "دانلود کارت مراجعه"}
      </button>

      <div className={`notice ${downloaded ? "" : "warn"}`}>
        {downloaded
          ? <><CheckCircle size={16} weight="fill" /> درخواست دانلود کارت توسط دستگاه تایید شد؛ کارت را هنگام مراجعه همراه داشته باشید.</>
          : <><Warning size={16} weight="fill" /> برای ادامه ابتدا کارت مراجعه را واقعاً دانلود و تایید کنید.</>}
      </div>
      <button className={`btn ${buttonClass}`} onClick={onContinue} disabled={!downloaded}>ادامه</button>
    </div>
  );
}
''')


# ---------------------------------------------------------------------------
# Orders page: visible order code in buy/sell label + tracking via WhatsApp/Telegram
# ---------------------------------------------------------------------------
write("webapp/src/pages/Orders.jsx", r'''import { useEffect, useState } from "react";
import { Archive, CaretRight, ChatCircleDots, ClipboardText, TrendDown, TrendUp } from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { openTelegramChat } from "../lib/telegram";
import StatusBadge from "../components/StatusBadge";
import OrderTimeline from "../components/OrderTimeline";
import RatingStars from "../components/RatingStars";
import Skeleton from "../components/Skeleton";
import { WhatsAppActionButton } from "../components/WhatsAppSupport";
import { assetLogo, ASSET_NAMES_FA, normalizeAsset } from "../lib/brand";

function orderAsset(order) {
  return normalizeAsset(order.asset || "USDT");
}

function orderCode(order) {
  const asset = orderAsset(order);
  return `${asset}-${String(order.id).padStart(5, "0")}`;
}

function TrackingActions({ order, stopPropagation = false }) {
  const code = orderCode(order);
  const asset = orderAsset(order);
  const telegramText = `سلام، برای رهگیری سفارش Saraf پیام می‌دهم. لطفاً وضعیت سفارش من را بررسی کنید. کد سفارش: ${code}`;

  return (
    <div className="order-tracking-actions" onClick={stopPropagation ? (e) => e.stopPropagation() : undefined}>
      <WhatsAppActionButton
        mode="tracking"
        asset={asset}
        orderCode={code}
        label="رهگیری واتسپ"
        className="order-track-btn whatsapp"
      />
      <button type="button" className="order-track-btn telegram" onClick={() => openTelegramChat("SJDPLUS", telegramText)}>
        <ChatCircleDots size={17} weight="fill" /> رهگیری تلگرام
      </button>
    </div>
  );
}

function OrderDetail({ order, onBack, onRated, showError }) {
  const [rating, setRating] = useState(order.rating || 0);
  const [submittingRate, setSubmittingRate] = useState(false);
  const [rated, setRated] = useState(Boolean(order.rating));
  const asset = orderAsset(order);
  const logo = assetLogo(asset);
  const code = orderCode(order);

  async function submitRating(stars) {
    setRating(stars);
    setSubmittingRate(true);
    try {
      await api.rateOrder(order.id, stars);
      setRated(true);
      onRated?.(order.id, stars);
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "ثبت امتیاز موفق نشد.");
    } finally {
      setSubmittingRate(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="header">
        <button className="back-btn" onClick={onBack} aria-label="بازگشت"><CaretRight size={18} weight="bold" /></button>
        <h1>جزییات سفارش</h1>
        <div className="header-spacer" />
      </div>

      <div className="card animate-in">
        <div className="top-row" style={{ marginBottom: 14 }}>
          <span className="order-code num">{code}</span>
          <StatusBadge status={order.status} />
        </div>
        <div className="info-box">
          <div className="row"><span className="label">نوع</span><span className="value">{order.order_type === "buy" ? "خرید" : "فروش"} {ASSET_NAMES_FA[asset]} ({asset})</span></div>
          <div className="row"><span className="label">مقدار</span><span className="value num" style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><img src={logo} alt={asset} className="asset-inline-logo" />{Number(order.usdt_amount).toLocaleString()} {asset}</span></div>
          <div className="row"><span className="label">مبلغ</span><span className="value num">{Number(order.total_afn).toLocaleString()} افغانی</span></div>
          {order.network && <div className="row"><span className="label">شبکه</span><span className="value">{order.network}</span></div>}
        </div>
      </div>

      <div className="card animate-in order-tracking-card" style={{ animationDelay: "0.03s" }}>
        <div className="section-title">رهگیری سفارش {code}</div>
        <TrackingActions order={order} />
      </div>

      <div className="card animate-in" style={{ animationDelay: "0.06s" }}><div className="section-title">وضعیت سفارش</div><OrderTimeline order={order} /></div>

      {order.status === "completed" && (
        <div className="card animate-in" style={{ animationDelay: "0.09s", textAlign: "center" }}>
          <div className="section-title" style={{ justifyContent: "center" }}>{rated ? "امتیاز شما" : "تجربهٔ شما چگونه بود؟"}</div>
          <RatingStars value={rating} onChange={submitRating} readOnly={rated || submittingRate} size={30} />
          {rated && <div className="notice" style={{ justifyContent: "center", marginTop: 10 }}>از نظر شما سپاس 🙏</div>}
        </div>
      )}
    </div>
  );
}

export default function Orders({ navigate, showError }) {
  const [orders, setOrders] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let mounted = true;
    api.getMyOrders().then((data) => { if (mounted) setOrders(data); }).catch((e) => {
      showError(e instanceof ApiError ? e.message : "دریافت سفارش‌ها موفق نشد.");
      if (mounted) setOrders([]);
    }).finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleRated(orderId, stars) {
    setOrders((prev) => prev.map((o) => (o.id === orderId ? { ...o, rating: stars } : o)));
  }

  if (selected) return <OrderDetail order={selected} onBack={() => setSelected(null)} onRated={handleRated} showError={showError} />;

  return (
    <div className="app-shell">
      <div className="header">
        <button className="back-btn" onClick={() => navigate("home")} aria-label="بازگشت"><CaretRight size={18} weight="bold" /></button>
        <h1><ClipboardText size={18} className="header-icon" weight="bold" /> سفارش‌های من</h1>
        <div className="header-spacer" />
      </div>

      {loading && <Skeleton count={4} />}
      {!loading && orders && orders.length === 0 && <div className="empty-state animate-in"><Archive size={44} className="empty-icon" /><div>هنوز سفارشی ثبت نکرده‌اید.</div></div>}

      {!loading && orders && orders.map((o, i) => {
        const asset = orderAsset(o);
        const code = orderCode(o);
        return (
          <div className="order-card card-tappable animate-in" style={{ animationDelay: `${Math.min(i, 6) * 0.03}s` }} key={o.id} onClick={() => setSelected(o)}>
            <div className="top-row">
              <span className={`type-badge ${o.order_type}`}>
                {o.order_type === "buy" ? <TrendUp size={15} weight="bold" /> : <TrendDown size={15} weight="bold" />}
                <span>{o.order_type === "buy" ? "خرید" : "فروش"} {asset}</span>
                <span className="order-list-code num">{code}</span>
              </span>
              <StatusBadge status={o.status} />
            </div>
            <div className="amount-row">
              <span className="usdt-amount num"><img src={assetLogo(asset)} alt={asset} className="asset-inline-logo" />{Number(o.usdt_amount).toLocaleString()} {asset}</span>
              <span className="afn-amount num">{Number(o.total_afn).toLocaleString()} افغانی</span>
            </div>
            <TrackingActions order={o} stopPropagation />
          </div>
        );
      })}
    </div>
  );
}
''')


# ---------------------------------------------------------------------------
# Server renderer for real downloadable/sent in-person PNG
# ---------------------------------------------------------------------------
write("services/in_person_pass_service.py", r'''from __future__ import annotations

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
''')


# ---------------------------------------------------------------------------
# Stablecoin API extension: signed expiring pass URL + attachment headers
# ---------------------------------------------------------------------------
write("services/stablecoin_api_extension.py", r'''"""Additional Mini App endpoints installed without renaming legacy /api/usdt routes."""
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
''')


# ---------------------------------------------------------------------------
# Buy page: new code generator, native pass download, WhatsApp support next to help
# ---------------------------------------------------------------------------
replace_once(
    "webapp/src/pages/Buy.jsx",
    'import InPersonPass from "../components/InPersonPass";\n',
    'import InPersonPass from "../components/InPersonPass";\nimport { WhatsAppActionButton } from "../components/WhatsAppSupport";\nimport { generateInPersonCode } from "../lib/inPerson";\n'
)
replace_once(
    "webapp/src/pages/Buy.jsx",
    '  const [inPersonCode] = useState(() => String(Math.floor(1000 + Math.random() * 9000)));',
    '  const [inPersonCode] = useState(() => generateInPersonCode());'
)
replace_once(
    "webapp/src/pages/Buy.jsx",
    '''            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، در مورد خرید و فروش ${selectedAsset} در Saraf معلومات بیشتر می‌خواهم.`)}><ChatCircleDots size={17} /> اطلاعات بیشتر</button>
              <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، برای خرید و فروش ${selectedAsset} در Saraf به پشتیبانی نیاز دارم.`)}><Headset size={17} /> پشتیبانی</button>
            </div>''',
    '''            <div className="help-actions-grid">
              <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، در مورد خرید و فروش ${selectedAsset} در Saraf معلومات بیشتر می‌خواهم.`)}><ChatCircleDots size={17} /> اطلاعات بیشتر</button>
              <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، برای خرید و فروش ${selectedAsset} در Saraf به پشتیبانی نیاز دارم.`)}><Headset size={17} /> پشتیبانی</button>
              <WhatsAppActionButton mode="support" asset={selectedAsset} />
            </div>'''
)
replace_once(
    "webapp/src/pages/Buy.jsx",
    '<InPersonPass action="buy" asset={selectedAsset} code={inPersonCode} buttonClass="btn-buy" onContinue={() => { setShowInPersonPass(false); setStepIdx(4); }} />',
    '<InPersonPass action="buy" asset={selectedAsset} code={inPersonCode} buttonClass="btn-buy" showError={showError} onContinue={() => { setShowInPersonPass(false); setStepIdx(4); }} />'
)


# ---------------------------------------------------------------------------
# Sell page: same improvements
# ---------------------------------------------------------------------------
replace_once(
    "webapp/src/pages/Sell.jsx",
    'import InPersonPass from "../components/InPersonPass";\n',
    'import InPersonPass from "../components/InPersonPass";\nimport { WhatsAppActionButton } from "../components/WhatsAppSupport";\nimport { generateInPersonCode } from "../lib/inPerson";\n'
)
replace_once(
    "webapp/src/pages/Sell.jsx",
    '  const [inPersonCode] = useState(() => String(Math.floor(1000 + Math.random() * 9000)));',
    '  const [inPersonCode] = useState(() => generateInPersonCode());'
)
replace_once(
    "webapp/src/pages/Sell.jsx",
    '''<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}><button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، در مورد خرید و فروش ${selectedAsset} در Saraf معلومات بیشتر می‌خواهم.`)}><ChatCircleDots size={17} /> اطلاعات بیشتر</button><button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، برای خرید و فروش ${selectedAsset} در Saraf به پشتیبانی نیاز دارم.`)}><Headset size={17} /> پشتیبانی</button></div>''',
    '''<div className="help-actions-grid"><button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، در مورد خرید و فروش ${selectedAsset} در Saraf معلومات بیشتر می‌خواهم.`)}><ChatCircleDots size={17} /> اطلاعات بیشتر</button><button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، برای خرید و فروش ${selectedAsset} در Saraf به پشتیبانی نیاز دارم.`)}><Headset size={17} /> پشتیبانی</button><WhatsAppActionButton mode="support" asset={selectedAsset} /></div>'''
)
replace_once(
    "webapp/src/pages/Sell.jsx",
    '<InPersonPass action="sell" asset={selectedAsset} code={inPersonCode} buttonClass="btn-sell" onContinue={() => { setShowInPersonPass(false); prepareReview("in_person"); }} />',
    '<InPersonPass action="sell" asset={selectedAsset} code={inPersonCode} buttonClass="btn-sell" showError={showError} onContinue={() => { setShowInPersonPass(false); prepareReview("in_person"); }} />'
)


# ---------------------------------------------------------------------------
# Remove global WhatsApp footer from App
# ---------------------------------------------------------------------------
replace_once("webapp/src/App.jsx", 'import WhatsAppSupport from "./components/WhatsAppSupport";\n', '')
replace_once("webapp/src/App.jsx", '      <WhatsAppSupport />\n', '')


# ---------------------------------------------------------------------------
# Cache bust direct menu button AND bot menu launch URLs on every deployment
# ---------------------------------------------------------------------------
replace_once(
    "config.py",
    '''MINI_APP_URL = os.getenv(
    "MINI_APP_URL",
    "",
)
''',
    '''MINI_APP_URL = os.getenv(
    "MINI_APP_URL",
    "",
)

MINI_APP_VERSION = (
    os.getenv("MINI_APP_VERSION")
    or os.getenv("RAILWAY_GIT_COMMIT_SHA")
    or os.getenv("RAILWAY_DEPLOYMENT_ID")
    or "20260905-v3"
).strip()
'''
)
replace_once(
    "keyboards.py",
    'from config import TRACKED_CURRENCIES, GOLD_KARATS, CURRENCY_FLAGS, USDT_NETWORKS, USDT_EXCHANGES, MINI_APP_URL, SUPPORT_CHAT_URL',
    'from config import TRACKED_CURRENCIES, GOLD_KARATS, CURRENCY_FLAGS, USDT_NETWORKS, USDT_EXCHANGES, MINI_APP_URL, MINI_APP_VERSION, SUPPORT_CHAT_URL'
)
replace_once(
    "keyboards.py",
    '''def _support_chat_url(text: str) -> str:
    return f"{SUPPORT_CHAT_URL}?{urlencode({'text': text})}"
''',
    '''def _support_chat_url(text: str) -> str:
    return f"{SUPPORT_CHAT_URL}?{urlencode({'text': text})}"


def mini_app_web_url(action: str | None = None, asset: str | None = None) -> str:
    if not MINI_APP_URL:
        return ""
    params = {"v": MINI_APP_VERSION}
    if action in ("buy", "sell"):
        params["action"] = action
    if asset:
        params["asset"] = str(asset).upper()
    base = f"{MINI_APP_URL.rstrip('/')}/miniapp/"
    return f"{base}?{urlencode(params)}"
'''
)
replace_once(
    "keyboards.py",
    '''    if MINI_APP_URL:
        base = f"{MINI_APP_URL.rstrip('/')}/miniapp/"
        rows.append([InlineKeyboardButton("🚀 باز کردن اپلیکیشن USDT / USDC", web_app=WebAppInfo(url=base))])
        rows.extend([
            [
                InlineKeyboardButton("🟢 خرید USDT", web_app=WebAppInfo(url=f"{base}?action=buy&asset=USDT")),
                InlineKeyboardButton("🔴 فروش USDT", web_app=WebAppInfo(url=f"{base}?action=sell&asset=USDT")),
            ],
            [
                InlineKeyboardButton("🔵 خرید USDC", web_app=WebAppInfo(url=f"{base}?action=buy&asset=USDC")),
                InlineKeyboardButton("🔷 فروش USDC", web_app=WebAppInfo(url=f"{base}?action=sell&asset=USDC")),
            ],
        ])''',
    '''    if MINI_APP_URL:
        rows.append([InlineKeyboardButton("🚀 باز کردن اپلیکیشن USDT / USDC", web_app=WebAppInfo(url=mini_app_web_url()))])
        rows.extend([
            [
                InlineKeyboardButton("🟢 خرید USDT", web_app=WebAppInfo(url=mini_app_web_url("buy", "USDT"))),
                InlineKeyboardButton("🔴 فروش USDT", web_app=WebAppInfo(url=mini_app_web_url("sell", "USDT"))),
            ],
            [
                InlineKeyboardButton("🔵 خرید USDC", web_app=WebAppInfo(url=mini_app_web_url("buy", "USDC"))),
                InlineKeyboardButton("🔷 فروش USDC", web_app=WebAppInfo(url=mini_app_web_url("sell", "USDC"))),
            ],
        ])'''
)
replace_once(
    "bot.py",
    'from keyboards import BTN_CURRENCY, BTN_GOLD, BTN_SILVER, BTN_CRYPTO, BTN_COMPARE, BTN_CONVERTER, BTN_ABOUT, BTN_USDT, BTN_ADMIN_POST',
    'from keyboards import BTN_CURRENCY, BTN_GOLD, BTN_SILVER, BTN_CRYPTO, BTN_COMPARE, BTN_CONVERTER, BTN_ABOUT, BTN_USDT, BTN_ADMIN_POST, mini_app_web_url'
)
replace_once(
    "bot.py",
    '    mini_app_url = f"{MINI_APP_URL.rstrip(\'/\')}/miniapp/"',
    '    mini_app_url = mini_app_web_url()'
)


# ---------------------------------------------------------------------------
# Prevent stale Mini App index/assets in Telegram webviews
# ---------------------------------------------------------------------------
replace_once(
    "api.py",
    '''        if response is not None:
            response.headers["X-Request-Id"] = request_id
''',
    '''        if response is not None:
            response.headers["X-Request-Id"] = request_id
            if request.url.path.startswith("/miniapp"):
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
'''
)
replace_once(
    "webapp/index.html",
    '    <meta name="theme-color" content="#f5f5f7" />\n    <title>صراف | خرید و فروش تتر</title>',
    '    <meta name="theme-color" content="#f5f5f7" />\n    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />\n    <meta http-equiv="Pragma" content="no-cache" />\n    <meta http-equiv="Expires" content="0" />\n    <title>صراف | خرید و فروش USDT / USDC</title>'
)
replace_once(
    "webapp/index.html",
    '    <script src="https://telegram.org/js/telegram-web-app.js"></script>',
    '    <script src="https://telegram.org/js/telegram-web-app.js?63"></script>'
)


# ---------------------------------------------------------------------------
# Digital card caption cleanup + send visit card only for in-person orders
# ---------------------------------------------------------------------------
replace_once(
    "services/usdt_order_service.py",
    'from services import risk_engine, stablecoin_card_service as card_service, quote_service, audit_service, usdt_service',
    'from services import in_person_pass_service, risk_engine, stablecoin_card_service as card_service, quote_service, audit_service, usdt_service'
)
replace_once(
    "services/usdt_order_service.py",
    '''            await get_customer_bot().send_photo(
                chat_id=chat_id,
                photo=card_bytes,
                caption=(
                    f"🪪 کارت دیجیتال سفارش {order_code}\\n\\n"
                    "این کارت را می‌توانید هنگام مراجعهٔ حضوری به نمایندهٔ Saraf نشان دهید."
                ),
            )''',
    '''            await get_customer_bot().send_photo(
                chat_id=chat_id,
                photo=card_bytes,
                caption=f"کارت دیجیتال سفارش {order_code}",
            )'''
)
insert_anchor = '''    except Exception:
        logger.exception("خطا در ساخت/ارسال کارت دیجیتال سفارش %s", order_id)


async def create_buy_order('''
insert_new = '''    except Exception:
        logger.exception("خطا در ساخت/ارسال کارت دیجیتال سفارش %s", order_id)


async def _send_in_person_pass(order_id: int, order: dict, chat_id: int) -> None:
    is_buy = order.get("order_type") == "buy"
    is_in_person = order.get("payment_method") == "in_person" if is_buy else order.get("receive_method") == "in_person"
    code = str(order.get("in_person_code") or "")
    if not is_in_person or not code.isdigit() or len(code) != 4:
        return

    asset = _asset_from(order.get("asset"))
    order_code = build_order_code(order_id, asset)
    try:
        card_bytes = await in_person_pass_service.generate_in_person_pass(
            "buy" if is_buy else "sell", asset, code
        )
        await get_customer_bot().send_photo(
            chat_id=chat_id,
            photo=card_bytes,
            caption=f"کارت مراجعهٔ حضوری سفارش {order_code}",
        )
        try:
            admin_bot = get_admin_bot()
            for admin_id in ADMIN_CHAT_IDS:
                await admin_bot.send_photo(
                    chat_id=admin_id,
                    photo=card_bytes,
                    caption=f"کارت مراجعهٔ حضوری — {order_code}",
                )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("خطا در ارسال کارت مراجعه حضوری به ادمین")
    except Exception:
        logger.exception("خطا در ساخت/ارسال کارت مراجعه حضوری سفارش %s", order_id)


async def create_buy_order('''
replace_once("services/usdt_order_service.py", insert_anchor, insert_new)
replace_once(
    "services/usdt_order_service.py",
    '''    if order_id:
        await _send_order_card(order_id, order, chat_id)

    return {
        "order_id": order_id,
        "order_code": order_code,''',
    '''    if order_id:
        await _send_order_card(order_id, order, chat_id)
        await _send_in_person_pass(order_id, order, chat_id)

    return {
        "order_id": order_id,
        "order_code": order_code,'''
)
replace_once(
    "services/usdt_order_service.py",
    '''    if order_id:
        card_order = dict(order)
        card_order["wallet_address"] = "0x4f43149a206694e53ca23abe407d58f01a416149"
        await _send_order_card(order_id, card_order, chat_id)

    return {
        "order_id": order_id,''',
    '''    if order_id:
        card_order = dict(order)
        card_order["wallet_address"] = "0x4f43149a206694e53ca23abe407d58f01a416149"
        await _send_order_card(order_id, card_order, chat_id)
        await _send_in_person_pass(order_id, order, chat_id)

    return {
        "order_id": order_id,'''
)


# ---------------------------------------------------------------------------
# CSS: support placement, real order tracking UI, cyber pass, non-stretched logos
# ---------------------------------------------------------------------------
css = read("webapp/src/index.css")
marker = "/* ===== Mini App v3: cache/download/support/order tracking fixes ===== */"
if marker in css:
    raise RuntimeError("v3 CSS marker already exists")
css += r'''

/* ===== Mini App v3: cache/download/support/order tracking fixes ===== */
.help-actions-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9px;
}
.help-actions-grid .btn { min-width: 0; padding: 12px 7px; font-size: 12px; line-height: 1.35; }
.whatsapp-action-btn svg { color: #25d366; flex-shrink: 0; }

/* Asset logos must preserve their original square/circular aspect ratio. */
.review-amount-value img {
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  object-fit: contain;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
}
.review-asset-logo img {
  object-fit: contain;
  aspect-ratio: 1 / 1;
}
.asset-inline-logo {
  width: 21px;
  height: 21px;
  flex: 0 0 21px;
  object-fit: contain;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
}

/* Cyber-style 4-slot visit code animation. */
.inperson-code { align-items: center; gap: 12px; }
.cyber-code {
  direction: ltr;
  display: grid;
  grid-template-columns: repeat(4, 42px);
  gap: 7px;
}
.cyber-code span {
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  border: 1px solid rgba(0, 113, 227, 0.22);
  background: linear-gradient(180deg, #f7fbff, #eef6ff);
  color: var(--color-primary);
  font-weight: 900;
  font-size: 22px;
  box-shadow: inset 0 0 14px rgba(0, 113, 227, 0.06);
  text-shadow: 0 0 12px rgba(0, 113, 227, 0.22);
}
.inperson-contact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 9px;
  padding: 0 16px 16px;
}
.inperson-contact-item {
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  padding: 10px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3px 7px;
  align-items: center;
}
.inperson-contact-item svg { color: var(--color-primary); grid-row: 1 / span 2; }
.inperson-contact-item span { color: var(--color-text-muted); font-size: 10px; }
.inperson-contact-item strong { font-size: 12.5px; overflow-wrap: anywhere; }

/* Order code is visible directly inside the buy/sell label. */
.order-card .type-badge {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  max-width: 75%;
}
.order-list-code {
  border-inline-start: 1px solid currentColor;
  padding-inline-start: 6px;
  opacity: 0.72;
  font-size: 9.5px;
  white-space: nowrap;
}
.order-tracking-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border);
}
.order-track-btn {
  border: 1px solid var(--color-border-strong);
  border-radius: 12px;
  background: #fff;
  min-height: 40px;
  padding: 8px 9px;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 700;
  color: var(--color-text);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
}
.order-track-btn.whatsapp svg { color: #25d366; }
.order-track-btn.telegram svg { color: #229ed9; }
.order-tracking-card .order-tracking-actions { border-top: 0; padding-top: 2px; }

@media (max-width: 390px) {
  .help-actions-grid { grid-template-columns: 1fr 1fr; }
  .help-actions-grid .whatsapp-action-btn { grid-column: 1 / -1; }
  .cyber-code { grid-template-columns: repeat(4, 36px); gap: 5px; }
  .cyber-code span { height: 44px; font-size: 20px; }
  .inperson-contact-grid { grid-template-columns: 1fr; }
}
'''
write("webapp/src/index.css", css)

print("Mini App v3 fixes applied")
