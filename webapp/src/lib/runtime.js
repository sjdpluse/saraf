// Build-time switch: Railway's normal Vite build remains unchanged.
// The Telegram native build replaces Python/FastAPI with Telegram endpoints.
export const IS_TELEGRAM_NATIVE =
  typeof __SARAF_NATIVE__ !== 'undefined' && __SARAF_NATIVE__ === true;

export const NATIVE_UNAVAILABLE_MESSAGE =
  'ثبت معامله یا حوالهٔ جدید تا تأیید نهایی سیستم مالی غیرفعال است؛ سوابق قبلی پس از اتصال امن Supabase نمایش داده می‌شوند.';
