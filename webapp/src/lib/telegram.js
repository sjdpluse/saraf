/**
 * لایهٔ نازک روی window.Telegram.WebApp — همه‌جای اپ فقط از این فایل استفاده می‌کند
 * تا اگر روزی نیاز به تغییر رفتار شد، فقط همین‌جا ادیت شود.
 */

function getWebApp() {
  return typeof window !== "undefined" ? window.Telegram?.WebApp : null;
}

export function initTelegram() {
  const wa = getWebApp();
  if (!wa) return;
  wa.ready();
  wa.expand();
  try {
    wa.setHeaderColor?.("secondary_bg_color");
  } catch (_) {
    /* بعضی نسخه‌های قدیمی تلگرام این متد را ندارند */
  }
}

export function getInitData() {
  const wa = getWebApp();
  return wa?.initData || "";
}

export function getTelegramUser() {
  const wa = getWebApp();
  return wa?.initDataUnsafe?.user || null;
}

export function isInsideTelegram() {
  return Boolean(getWebApp()?.initData);
}

export function hapticSuccess() {
  getWebApp()?.HapticFeedback?.notificationOccurred?.("success");
}

export function hapticError() {
  getWebApp()?.HapticFeedback?.notificationOccurred?.("error");
}

export function showConfirm(message) {
  return new Promise((resolve) => {
    const wa = getWebApp();
    if (wa?.showConfirm) {
      wa.showConfirm(message, (ok) => resolve(ok));
    } else {
      resolve(window.confirm(message));
    }
  });
}

export function closeApp() {
  getWebApp()?.close?.();
}
