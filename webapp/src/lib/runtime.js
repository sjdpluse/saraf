// Build-time switch: Railway's normal Vite build remains unchanged.
// The Telegram native build replaces Python/FastAPI with Telegram endpoints.
export const IS_TELEGRAM_NATIVE =
  typeof __SARAF_NATIVE__ !== 'undefined' && __SARAF_NATIVE__ === true;

export const NATIVE_UNAVAILABLE_MESSAGE =
  'خدمات خریدوفروش، حواله و اطلاعات حساب در حال انتقال امن به Telegram Serverless است. فعلاً از ربات اصلی صراف استفاده کنید.';
