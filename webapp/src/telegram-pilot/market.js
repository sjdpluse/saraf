// Browser-side interface to Telegram's native authenticated endpoints.
// Only the dedicated read-only pilot endpoint is allowed here.
// No use of the production FastAPI /api/* routes or Railway domain.
const ALLOWED_KINDS = new Set(["currencies", "gold", "silver", "crypto", "local"]);

export function getTelegramWebApp() {
  return typeof window === "undefined" ? null : window.Telegram?.WebApp ?? null;
}

export function isTelegramServerlessAvailable() {
  const wa = getTelegramWebApp();
  return Boolean(wa?.initData && typeof wa?.Serverless?.call === "function");
}

export function getMarket(kind, { timeoutMs = 18000 } = {}) {
  if (!ALLOWED_KINDS.has(kind)) return Promise.reject(new Error("نوع بازار نامعتبر است."));
  if (!isTelegramServerlessAvailable())
    return Promise.reject(new Error("Mini App را از داخل ربات آزمایشی تلگرام باز کنید."));

  return new Promise((resolve, reject) => {
    const wa = getTelegramWebApp();
    let done = false;
    const settle = (error, value) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (error) reject(error);
      else resolve(value);
    };
    const timer = setTimeout(() => settle(new Error("درخواست سرور بیش از حد طول کشید.")), timeoutMs);
    try {
      wa.Serverless.call(kind === "local" ? "getLocalMarket" : "getReadOnlyMarket", kind === "local" ? {} : { kind }, (error, result) => {
        if (error) return settle(new Error("دریافت اطلاعات بازار ناموفق بود."));
        if (!result || result.kind !== kind || result.isReferenceOnly !== true ||
            !Array.isArray(result.items))
          return settle(new Error("پاسخ سرور معتبر نیست."));
        settle(null, result);
      });
    } catch (error) {
      settle(new Error("امکان اتصال به Telegram Serverless وجود ندارد."));
    }
  });
}
