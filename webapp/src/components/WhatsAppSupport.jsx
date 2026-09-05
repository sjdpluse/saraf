import { ChatCircleDots, MagnifyingGlass } from "@phosphor-icons/react";

const WHATSAPP_QR_URL = "https://wa.me/qr/25MA3IJZTGQPE1";
const SUPPORT_TEXT = "سلام، برای استفاده از خدمات خرید و فروش USDT / USDC در Saraf به پشتیبانی نیاز دارم.";
const TRACK_TEXT = "سلام، برای رهگیری سفارش Saraf پیام می‌دهم. لطفاً وضعیت سفارش من را بررسی کنید. کد سفارش: ";

function openWhatsApp(text) {
  // لینک QR داده‌شده مستقیماً چت را باز می‌کند؛ متن آماده در کلیپ‌بورد قرار می‌گیرد
  // تا حتی روی کلاینت‌هایی که query text را برای لینک QR پشتیبانی نمی‌کنند قابل استفاده باشد.
  navigator.clipboard?.writeText(text).catch(() => {});
  window.open(WHATSAPP_QR_URL, "_blank", "noopener,noreferrer");
}

export default function WhatsAppSupport() {
  return (
    <div className="whatsapp-support-bar" aria-label="پشتیبانی واتسپ">
      <button type="button" onClick={() => openWhatsApp(SUPPORT_TEXT)}><ChatCircleDots size={17} weight="fill" /> پشتیبانی واتسپ</button>
      <button type="button" onClick={() => openWhatsApp(TRACK_TEXT)}><MagnifyingGlass size={17} weight="bold" /> رهگیری سفارش</button>
    </div>
  );
}
