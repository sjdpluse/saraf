import { getInitData } from "./telegram";
import { normalizeAsset } from "./brand";

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

async function request(path, { method = "GET", body, isForm = false, headers: extraHeaders = {} } = {}) {
  const headers = { "X-Telegram-Init-Data": getInitData(), ...extraHeaders };
  if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch (_) {}

  if (!res.ok) {
    throw new ApiError(data?.detail || data?.error?.message || "خطایی رخ داد. لطفاً دوباره تلاش کنید.", res.status, data?.error?.code);
  }
  return data;
}

async function requestBlob(path, body) {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: {
      "X-Telegram-Init-Data": getInitData(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let data = null;
    try { data = await res.json(); } catch (_) {}
    throw new ApiError(data?.detail || data?.error?.message || "ساخت پیش‌نمایش ناموفق بود.", res.status, data?.error?.code);
  }
  return res.blob();
}

function quoteKey(action, asset) {
  return `${action}:${normalizeAsset(asset)}`;
}

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

function onlineProviderLabel(method) {
  if (method === "online_hesabpay") return "حساب‌پی";
  if (method === "online_azizi") return "عزیزی بانک";
  return null;
}

export const api = {
  getQuote: async (action, amount, asset = "USDT") => {
    const selectedAsset = normalizeAsset(asset);
    const quote = await request("/usdt/quote", {
      method: "POST",
      body: { action, amount, asset: selectedAsset },
    });
    latestQuotes.set(quoteKey(action, selectedAsset), { ...quote, asset: selectedAsset });
    return { ...quote, asset: selectedAsset };
  },

  getStablecoinConfig: () => request("/stablecoins/config"),

  getInPersonPassLink: ({ action, asset, code }) =>
    request("/stablecoins/in-person-pass-link", {
      method: "POST",
      body: { action, asset: normalizeAsset(asset), code: String(code || "") },
    }),

  getCardPreview: async ({ action, asset, amount, exchange_name, network, wallet_address }) => {
    const selectedAsset = normalizeAsset(asset);
    const q = quoteFor(action, amount, selectedAsset);
    return requestBlob("/stablecoins/card-preview", {
      action,
      asset: selectedAsset,
      amount: Number(amount),
      quote_id: q.quote_id,
      exchange_name,
      network,
      wallet_address: wallet_address || null,
    });
  },

  getProfile: () => request("/usdt/profile"),

  submitBasicProfile: (fields) => {
    const form = new FormData();
    Object.entries(fields).forEach(([k, v]) => form.append(k, v));
    return request("/usdt/profile", { method: "POST", body: form, isForm: true });
  },

  submitIdentityVerification: (fields) => {
    const form = new FormData();
    Object.entries(fields).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== "") form.append(k, v);
    });
    return request("/usdt/kyc", { method: "POST", body: form, isForm: true });
  },

  createBuyOrder: async (payload) => {
    const asset = normalizeAsset(payload.asset);
    const q = quoteFor("buy", payload.amount, asset);
    const provider = onlineProviderLabel(payload.payment_method);
    const exchangeName = provider
      ? `${payload.exchange_name || "-"} | پرداخت: ${provider}`
      : payload.exchange_name;

    return request("/usdt/orders/buy", {
      method: "POST",
      body: {
        ...payload,
        asset,
        payment_method: provider ? "online" : payload.payment_method,
        exchange_name: exchangeName,
        quote_id: q.quote_id,
      },
      headers: { "Idempotency-Key": retryKey("buy", asset, q.quote_id) },
    });
  },

  createSellOrder: async (payload) => {
    const asset = normalizeAsset(payload.asset);
    const q = quoteFor("sell", payload.amount, asset);
    const provider = onlineProviderLabel(payload.receive_method);
    const bankInfo = provider
      ? `${provider} — ${payload.bank_info || ""}`.trim()
      : payload.bank_info;

    return request("/usdt/orders/sell", {
      method: "POST",
      body: {
        ...payload,
        asset,
        receive_method: provider ? "online" : payload.receive_method,
        bank_info: bankInfo,
        quote_id: q.quote_id,
      },
      headers: { "Idempotency-Key": retryKey("sell", asset, q.quote_id) },
    });
  },

  getMyOrders: () => request("/usdt/orders/me"),
  getStats: () => request("/usdt/stats"),
  getReviews: (limit = 20, offset = 0) => request(`/reviews?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`),
  createReview: (body) => request("/reviews", { method: "POST", body: { body } }),
  replyToReview: (reviewId, body) => request(`/reviews/${reviewId}/reply`, { method: "POST", body: { body } }),
  getPaymentInfo: () => request("/usdt/payment-info"),

  rateOrder: (orderId, rating, comment) =>
    request(`/usdt/orders/${orderId}/rate`, { method: "POST", body: { rating, comment } }),

  uploadReceipt: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/usdt/upload-receipt", { method: "POST", body: form, isForm: true });
  },
};

export { ApiError, newIdempotencyKey };
