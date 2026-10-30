// Native Telegram Serverless adapter for the ORIGINAL React Saraf UI.
// Never fall back to Railway for auth, private data, money, or user actions.
import { getInitData } from './telegram';

export class NativeEndpointError extends Error {
  constructor(message, code = 'NATIVE_ENDPOINT_ERROR') {
    super(message);
    this.code = code;
  }
}
const AVAILABLE_ENDPOINTS = new Set([
  'getMarketSnapshot','getSarafCapabilities','getReadOnlyMarket','getLocalMarket',
  'getNativeStats','getNativeProfile','saveBasicProfile','submitNativeIdentity',
  'getNativeMediaStatus','getNativeOrders','rateNativeOrder',
  'getNativePaymentInfo','getNativeStablecoinConfig','getNativeQuote',
  'getNativeRemittanceConfig','getNativeRemittanceQuote','createNativeRemittance',
  'getNativeRemittances','submitNativeRemittanceTx','createNativeOrder',
  'getNativeReviews','createNativeReview','voteNativeReview','replyNativeReview',
]);
export function nativeCall(name, input = {}) {
  if (!AVAILABLE_ENDPOINTS.has(name)) {
    return Promise.reject(new NativeEndpointError('این خدمت هنوز در Serverless فعال نیست.', 'NOT_MIGRATED'));
  }
  const webapp = typeof window !== 'undefined' ? window.Telegram?.WebApp : null;
  if (!getInitData() || typeof webapp?.Serverless?.call !== 'function') {
    return Promise.reject(new NativeEndpointError('این بخش را از داخل ربات تلگرام باز کنید.', 'UNAUTHORIZED'));
  }
  return new Promise((resolve, reject) => {
    let completed = false;
    const finish = (error, result) => {
      if (completed) return;
      completed = true;
      clearTimeout(timer);
      if (error) reject(error);
      else resolve(result);
    };
    const timer = window.setTimeout(
      () => finish(new NativeEndpointError('زمان پاسخ سرور به پایان رسید.', 'TIMEOUT')),
      20000,
    );
    try {
      webapp.Serverless.call(name, input, (error, result) => {
        if (error) finish(new NativeEndpointError(error.message || 'پاسخ سرور ناموفق بود.', error.type || 'ENDPOINT_ERROR'));
        else finish(null, result);
      });
    } catch (_) {
      finish(new NativeEndpointError('ارتباط با تلگرام برقرار نشد.', 'NETWORK_ERROR'));
    }
  });
}
