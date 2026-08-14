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
  // چون تم روشن یک تصمیم برند ثابت است (نه وابسته به تم تاریک/روشن خود
  // تلگرام کاربر)، رنگ واقعی پس‌زمینه را مستقیم می‌دهیم، نه کلید تم
  // ("secondary_bg_color") که در حالت تاریک تلگرام می‌تواند تیره برگردد.
  try {
    wa.setHeaderColor?.("#f5f5f7");
  } catch (_) {
    /* بعضی نسخه‌های قدیمی تلگرام رنگ دلخواه (غیر از کلید تم) را نمی‌پذیرند */
  }
  try {
    wa.setBackgroundColor?.("#f5f5f7");
  } catch (_) {
    /* نسخه‌های قدیمی‌تر این متد را ندارند */
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

export function openTelegramChat(username) {
  const wa = getWebApp();
  const url = `https://t.me/${username}`;
  if (wa?.openTelegramLink) {
    wa.openTelegramLink(url);
  } else {
    window.open(url, "_blank");
  }
}
