import { getInitData } from "./telegram";

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

const latestQuotes = { buy: null, sell: null };
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
    throw new ApiError(data?.detail || "خطایی رخ داد. لطفاً دوباره تلاش کنید.", res.status, data?.error?.code);
  }
  return data;
}

function quoteFor(action, amount) {
  const q = latestQuotes[action];
  if (!q || !q.quote_id || Number(q.amount) !== Number(amount)) {
    throw new ApiError("نرخ سفارش پیدا نشد؛ لطفاً دوباره نرخ بگیرید.", 409);
  }
  return q;
}

function retryKey(action, quoteId) {
  const key = `${action}:${quoteId}`;
  if (!orderRetryKeys.has(key)) orderRetryKeys.set(key, newIdempotencyKey());
  return orderRetryKeys.get(key);
}

export const api = {
  getQuote: async (action, amount) => {
    const quote = await request("/usdt/quote", { method: "POST", body: { action, amount } });
    latestQuotes[action] = quote;
    return quote;
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
    const q = quoteFor("buy", payload.amount);
    return request("/usdt/orders/buy", {
      method: "POST",
      body: { ...payload, quote_id: q.quote_id },
      headers: { "Idempotency-Key": retryKey("buy", q.quote_id) },
    });
  },

  createSellOrder: async (payload) => {
    const q = quoteFor("sell", payload.amount);
    return request("/usdt/orders/sell", {
      method: "POST",
      body: { ...payload, quote_id: q.quote_id },
      headers: { "Idempotency-Key": retryKey("sell", q.quote_id) },
    });
  },

  getMyOrders: () => request("/usdt/orders/me"),
  getStats: () => request("/usdt/stats"),
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
