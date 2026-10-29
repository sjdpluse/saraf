import { getInitData } from "./telegram";
import { normalizeAsset } from "./brand";
import { IS_TELEGRAM_NATIVE, NATIVE_UNAVAILABLE_MESSAGE } from "./runtime";
import { nativeCall } from "./nativeApi";
import { canonicalCall } from "./supabaseBridge";
import { uploadOriginalIdentity } from "./legacyKycBridge";

class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function newIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const bytes = new Uint8Array(16);
  globalThis.crypto?.getRandomValues?.(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("") || `${Date.now()}-${Math.random()}`;
}

const latestQuotes = new Map();
const orderRetryKeys = new Map();
const remittanceRetryKeys = new Map();

async function request(path, { method = "GET", body, isForm = false, headers: extraHeaders = {} } = {}) {
  if (IS_TELEGRAM_NATIVE) {
    // Only explicitly migrated reads are routed to native Telegram Serverless.
    // No financial API call can silently fall back to Railway or expose initData.
    if (path === '/market/snapshot' && method === 'GET') return nativeCall('getMarketSnapshot');
    if (path === '/usdt/stats' && method === 'GET') return canonicalCall('stats.get');
    if (path === '/usdt/profile' && method === 'GET') return canonicalCall('profile.get');
    if (path === '/usdt/profile' && method === 'POST') {
      if (!isForm || !body) throw new ApiError('معلومات پروفایل معتبر نیست.', 400);
      return canonicalCall('profile.save', {
        first_name: body.get('first_name'),
        last_name: body.get('last_name'),
        phone: body.get('phone'),
      });
    }
    if (path === '/usdt/kyc' && method === 'POST') return uploadOriginalIdentity(body);
    if (path === '/usdt/orders/me' && method === 'GET') return canonicalCall('orders.me');
    if (path === '/usdt/payment-info' && method === 'GET') return nativeCall('getNativePaymentInfo');
    if (path === '/stablecoins/config' && method === 'GET') return nativeCall('getNativeStablecoinConfig');
    if (path === '/remittances/config' && method === 'GET') return nativeCall('getNativeRemittanceConfig');
    if (path === '/remittances/me' && method === 'GET') return canonicalCall('remittances.me');
    // Preserve the ORIGINAL Python pricing/payment semantics. Until those
    // routes have been ported exactly, do NOT call new speculative money logic
    // or fall back to the offline Railway service.
    const originalWritePaths=new Set([
      '/remittances/quote','/remittances',
      '/usdt/quote','/usdt/orders/buy','/usdt/orders/sell',
    ]);
    if(method==='POST' && originalWritePaths.has(path))
      throw new ApiError(NATIVE_UNAVAILABLE_MESSAGE,503,'NOT_MIGRATED');
    let match=path.match(/^\/usdt\/orders\/(\d+)\/rate$/);
    if (match && method==='POST') return canonicalCall('orders.rate', {
      order_id:Number(match[1]),...body,
    });
    match=path.match(/^\/remittances\/(\d+)\/tx$/);
    if(match&&method==='POST')
      throw new ApiError(NATIVE_UNAVAILABLE_MESSAGE,503,'NOT_MIGRATED');
    match=path.match(/^\/reviews(?:\?limit=(\d+)&offset=(\d+))?$/);
    if (match && method==='GET') return canonicalCall('reviews.list', {
      limit:Number(match[1])||20,offset:Number(match[2])||0,
    });
    if (path==='/reviews' && method==='POST') return canonicalCall('reviews.create',body);
    match=path.match(/^\/reviews\/(\d+)\/(reply|vote)$/);
    if (match && method==='POST') return canonicalCall(
      match[2]==='vote'?'reviews.vote':'reviews.reply',
      {review_id:Number(match[1]),...body},
    );
    throw new ApiError(NATIVE_UNAVAILABLE_MESSAGE, 503, 'NOT_MIGRATED');
  }
  const headers = { "X-Telegram-Init-Data": getInitData(), ...extraHeaders };
  if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) throw new ApiError(data?.detail || data?.error?.message || "خطایی رخ داد. لطفاً دوباره تلاش کنید.", res.status, data?.error?.code);
  return data;
}

async function requestBlob(path, body) {
  if (IS_TELEGRAM_NATIVE) throw new ApiError(NATIVE_UNAVAILABLE_MESSAGE, 503, 'NOT_MIGRATED');
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "X-Telegram-Init-Data": getInitData(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let data = null;
    try { data = await res.json(); } catch (_) {}
    throw new ApiError(data?.detail || data?.error?.message || "ساخت پیش‌نمایش ناموفق بود.", res.status, data?.error?.code);
  }
  return res.blob();
}

function quoteKey(action, asset) { return `${action}:${normalizeAsset(asset)}`; }
function quoteFor(action, amount, asset) {
  const selectedAsset = normalizeAsset(asset);
  const q = latestQuotes.get(quoteKey(action, selectedAsset));
  if (!q || !q.quote_id || Number(q.amount) !== Number(amount) || normalizeAsset(q.asset) !== selectedAsset) {
    throw new ApiError(`نرخ ${selectedAsset} پیدا نشد؛ لطفاً دوباره نرخ بگیرید.`, 409);
  }
  return q;
}
function retryKey(action, asset, quoteId) {
  const key = `${action}:${normalizeAsset(asset)}:${quoteId}`;
  if (!orderRetryKeys.has(key)) orderRetryKeys.set(key, newIdempotencyKey());
  return orderRetryKeys.get(key);
}
function remittanceRetryKey(payload) {
  const key = JSON.stringify([
    payload.sender_full_name,
    payload.sender_country,
    payload.beneficiary_phone,
    payload.beneficiary_id_document_path,
    payload.amount,
    payload.asset,
    payload.network,
  ]);
  if (!remittanceRetryKeys.has(key)) remittanceRetryKeys.set(key, newIdempotencyKey());
  return remittanceRetryKeys.get(key);
}
function onlineProvider(method) {
  if (method === "online_hesabpay") return "hesabpay";
  if (method === "online_azizi") return "azizi";
  return null;
}
function onlineProviderLabel(method) {
  if (method === "online_hesabpay") return "حساب‌پی";
  if (method === "online_azizi") return "عزیزی بانک";
  return null;
}

export const api = {
  getMarketSnapshot: () => request("/market/snapshot"),
  getQuote: async (action, amount, asset = "USDT") => {
    const selectedAsset = normalizeAsset(asset);
    const quote = await request("/usdt/quote", { method: "POST", body: { action, amount, asset: selectedAsset } });
    latestQuotes.set(quoteKey(action, selectedAsset), { ...quote, asset: selectedAsset });
    return { ...quote, asset: selectedAsset };
  },
  getStablecoinConfig: () => request("/stablecoins/config"),
  getInPersonPassLink: ({ action, asset, code }) => request("/stablecoins/in-person-pass-link", { method: "POST", body: { action, asset: normalizeAsset(asset), code: String(code || "") } }),
  getCardPreview: async ({ action, asset, amount, exchange_name, network, wallet_address }) => {
    const selectedAsset = normalizeAsset(asset);
    const q = quoteFor(action, amount, selectedAsset);
    return requestBlob("/stablecoins/card-preview", { action, asset: selectedAsset, amount: Number(amount), quote_id: q.quote_id, exchange_name, network, wallet_address: wallet_address || null });
  },
  getProfile: () => request("/usdt/profile"),
  submitBasicProfile: (fields) => {
    const form = new FormData();
    Object.entries(fields).forEach(([k, v]) => form.append(k, v));
    return request("/usdt/profile", { method: "POST", body: form, isForm: true });
  },
  submitIdentityVerification: (fields) => {
    const form = new FormData();
    Object.entries(fields).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== "") form.append(k, v); });
    return request("/usdt/kyc", { method: "POST", body: form, isForm: true });
  },
  createBuyOrder: async (payload) => {
    const asset = normalizeAsset(payload.asset);
    const q = quoteFor("buy", payload.amount, asset);
    const provider = onlineProvider(payload.payment_method);
    const providerLabel = onlineProviderLabel(payload.payment_method);
    const exchangeName = providerLabel ? `${payload.exchange_name || "-"} | پرداخت: ${providerLabel}` : payload.exchange_name;
    return request("/usdt/orders/buy", { method: "POST", body: { ...payload, asset, payment_method: provider ? "online" : payload.payment_method, payment_provider: provider, exchange_name: exchangeName, quote_id: q.quote_id }, headers: { "Idempotency-Key": retryKey("buy", asset, q.quote_id) } });
  },
  createSellOrder: async (payload) => {
    const asset = normalizeAsset(payload.asset);
    const q = quoteFor("sell", payload.amount, asset);
    const provider = onlineProvider(payload.receive_method);
    const providerLabel = onlineProviderLabel(payload.receive_method);
    const bankInfo = providerLabel ? `${providerLabel} — ${payload.bank_info || ""}`.trim() : payload.bank_info;
    return request("/usdt/orders/sell", { method: "POST", body: { ...payload, asset, receive_method: provider ? "online" : payload.receive_method, receive_provider: provider, bank_info: bankInfo, quote_id: q.quote_id }, headers: { "Idempotency-Key": retryKey("sell", asset, q.quote_id) } });
  },
  getMyOrders: () => request("/usdt/orders/me"),
  getStats: () => request("/usdt/stats"),
  getReviews: (limit = 20, offset = 0) => request(`/reviews?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`),
  createReview: (body) => request("/reviews", { method: "POST", body: { body } }),
  replyToReview: (reviewId, body) => request(`/reviews/${reviewId}/reply`, { method: "POST", body: { body } }),
  voteReview: (reviewId, vote) => request(`/reviews/${reviewId}/vote`, { method: "POST", body: { vote } }),
  getPaymentInfo: () => request("/usdt/payment-info"),
  rateOrder: (orderId, rating, comment) => request(`/usdt/orders/${orderId}/rate`, { method: "POST", body: { rating, comment } }),
  uploadReceipt: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/usdt/upload-receipt", { method: "POST", body: form, isForm: true });
  },

  getRemittanceConfig: () => request("/remittances/config"),
  getRemittanceQuote: (payload) => request("/remittances/quote", { method: "POST", body: payload }),
  uploadRemittanceBeneficiaryId: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/remittances/upload-beneficiary-id", { method: "POST", body: form, isForm: true });
  },
  createRemittance: (payload) => request("/remittances", { method: "POST", body: payload, headers: { "Idempotency-Key": remittanceRetryKey(payload) } }),
  submitRemittanceTx: (orderId, txHash) => request(`/remittances/${orderId}/tx`, { method: "POST", body: { tx_hash: txHash } }),
  getMyRemittances: () => request("/remittances/me"),
};

export { ApiError, newIdempotencyKey };
