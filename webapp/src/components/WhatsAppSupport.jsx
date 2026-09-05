import { WhatsappLogo } from "@phosphor-icons/react";
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
