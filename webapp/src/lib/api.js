import { getInitData } from "./telegram";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, isForm = false } = {}) {
  const headers = { "X-Telegram-Init-Data": getInitData() };
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

  createBuyOrder: (payload) => request("/usdt/orders/buy", { method: "POST", body: payload }),

  createSellOrder: (payload) => request("/usdt/orders/sell", { method: "POST", body: payload }),

  getMyOrders: () => request("/usdt/orders/me"),

  uploadReceipt: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/usdt/upload-receipt", { method: "POST", body: form, isForm: true });
  },
};

export { ApiError };
