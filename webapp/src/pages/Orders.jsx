import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";

const STATUS_LABEL = {
  pending: "در انتظار بررسی",
  confirmed: "تایید شده",
  cancelled: "رد شده",
  completed: "تکمیل شده",
};

const STATUS_CLASS = {
  pending: "status-pending",
  confirmed: "status-confirmed",
  completed: "status-confirmed",
  cancelled: "status-cancelled",
};

export default function Orders({ navigate, showError }) {
  const [orders, setOrders] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    api
      .getMyOrders()
      .then((data) => {
        if (mounted) setOrders(data);
      })
      .catch((e) => {
        showError(e instanceof ApiError ? e.message : "خطا در دریافت سفارش‌ها.");
        if (mounted) setOrders([]);
      })
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app-shell">
      <div className="header">
        <button className="back-btn" onClick={() => navigate("home")}>
          › بازگشت
        </button>
        <h1>📋 سفارش‌های من</h1>
      </div>

      {loading && (
        <div className="empty-state">
          <div className="spinner" style={{ margin: "0 auto", borderTopColor: "var(--saraf-accent)" }} />
        </div>
      )}

      {!loading && orders && orders.length === 0 && (
        <div className="empty-state">
          <div className="icon">🗂️</div>
          <div>هنوز سفارشی ثبت نکرده‌اید.</div>
        </div>
      )}

      {!loading &&
        orders &&
        orders.map((o) => (
          <div className="order-card" key={o.id}>
            <div className="top-row">
              <span className="order-code">USDT-{String(o.id).padStart(5, "0")}</span>
              <span className={`status-badge ${STATUS_CLASS[o.status] || "status-pending"}`}>
                {STATUS_LABEL[o.status] || o.status}
              </span>
            </div>
            <div className="meta">
              <span>{o.order_type === "buy" ? "🟢 خرید" : "🔴 فروش"}</span>
              <span>{Number(o.usdt_amount).toLocaleString()} USDT</span>
            </div>
            <div className="meta">
              <span>مبلغ</span>
              <span>{Number(o.total_afn).toLocaleString()} افغانی</span>
            </div>
          </div>
        ))}
    </div>
  );
}
