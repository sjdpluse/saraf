import { getInitData } from "./telegram";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function newIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const bytes = new Uint8Array(16);
  globalThis.crypto?.getRandomValues?.(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("") || `${Date.now()}-${Math.random()}`;
}

async function request(path, { method = "GET", body, isForm = false, headers: extraHeaders = {} } = {}) {
  const headers = { "X-Telegram-Init-Data": getInitData(), ...extraHeaders };
  if (!isForm && body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    /* پاسخ بدون بدنه (مثلاً خطای شبکه) */
  }

  if (!res.ok) {
    const message = data?.detail || "خطایی رخ داد. لطفاً دوباره تلاش کنید.";
    throw new ApiError(message, res.status);
  }
  return data;
}

export const api = {
  getQuote: (action, amount) => request("/usdt/quote", { method: "POST", body: { action, amount } }),

  getProfile: () => request("/usdt/profile"),

  submitKyc: (fields) => {
    const form = new FormData();
    Object.entries(fields).forEach(([k, v]) => form.append(k, v));
    return request("/usdt/kyc", { method: "POST", body: form, isForm: true });
  },

  createBuyOrder: (payload, idempotencyKey = newIdempotencyKey()) =>
    request("/usdt/orders/buy", {
      method: "POST",
      body: payload,
      headers: { "Idempotency-Key": idempotencyKey },
    }),

  createSellOrder: (payload, idempotencyKey = newIdempotencyKey()) =>
    request("/usdt/orders/sell", {
      method: "POST",
      body: payload,
      headers: { "Idempotency-Key": idempotencyKey },
    }),

  getMyOrders: () => request("/usdt/orders/me"),

  getStats: () => request("/usdt/stats"),

  rateOrder: (orderId, rating, comment) =>
    request(`/usdt/orders/${orderId}/rate`, { method: "POST", body: { rating, comment } }),

  uploadReceipt: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/usdt/upload-receipt", { method: "POST", body: form, isForm: true });
  },
};

export { ApiError, newIdempotencyKey };
