import { useEffect, useState } from "react";
import { ArrowClockwise, CaretRight, PaperPlaneTilt, Plus, CaretDown, Headset } from "@phosphor-icons/react";
import { api } from "../lib/api";
import { openTelegramChat } from "../lib/telegram";
import { REMITTANCE_STATUS, remittanceStatusClass, formatAmount } from "../lib/remittance";
import CopyRow from "../components/CopyRow";
import Skeleton from "../components/Skeleton";

export default function Remittances({ navigate, onContinue }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [filter, setFilter] = useState("all");
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api.getMyRemittances().then((list) => { if (active) setOrders(list || []); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);
  const visible = orders.filter((order) => filter === "all" || (filter === "active" ? !["completed", "cancelled"].includes(order.status) : order.status === "completed"));
  return <main className="app-shell remittance-history">
    <header className="header">
      <button className="back-btn" aria-label="بازگشت به خانه" onClick={() => navigate("home")}><CaretRight size={20} /></button>
      <h1>حواله‌های من</h1>
      <button className="icon-button" aria-label="تازه‌سازی حواله‌ها" disabled={loading} onClick={() => setAttempt((value) => value + 1)}><ArrowClockwise size={21} /></button>
    </header>
    <button className="btn btn-primary" onClick={() => navigate("remittance")}><Plus size={20} /> حوالهٔ جدید</button>
    <div className="history-filters" aria-label="فیلتر حواله‌ها">
      {[["all", "همه"], ["active", "در جریان"], ["completed", "تکمیل‌شده"]].map(([value, label]) => <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</button>)}
    </div>
    {loading ? <div className="card" role="status" aria-label="در حال دریافت حواله‌ها"><Skeleton count={2} /></div> : error ? <div className="card history-empty" role="alert"><p>{error}</p><button className="btn btn-outline" onClick={() => setAttempt((value) => value + 1)}>تلاش دوباره</button></div> : visible.length === 0 ? <div className="card history-empty"><PaperPlaneTilt size={38} /><h2>{orders.length ? "حواله‌ای در این بخش نیست" : "هنوز حواله‌ای ثبت نکرده‌اید"}</h2><p>حواله‌های ثبت‌شده و وضعیت دریافت آن‌ها در اینجا نمایش داده می‌شوند.</p></div> : visible.map((order) => <article key={order.id} className="card history-order">
      <div className="history-order-top"><span className="num">{order.order_code}</span><span className={"status-badge status-" + remittanceStatusClass(order.status)}>{REMITTANCE_STATUS[order.status] || order.status}</span></div>
      <h2>{order.beneficiary_full_name}</h2>
      <div className="history-order-amount"><strong>{formatAmount(order.payout_afn, 0)} <small>افغانی</small></strong><span className="num">{order.crypto_amount} {order.asset}</span></div>
      {["payout_ready", "completed"].includes(order.status) && order.pickup_code && <div className="remit-pickup-code"><CopyRow label="کد دریافت" value={order.pickup_code} /></div>}
      <details className="history-details"><summary>جزئیات حواله<CaretDown size={17} /></summary><div>
        <CopyRow label="کد حواله" value={order.order_code} />
        <div className="quote-row"><span>شبکه</span><bdi>{order.network}</bdi></div>
        <div className="quote-row"><span>موقعیت گیرنده</span><span>{[order.beneficiary_province, order.beneficiary_city].filter(Boolean).join(" / ") || "—"}</span></div>
        {order.tx_hash && <CopyRow label="شناسهٔ تراکنش" value={order.tx_hash} />}
        <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", "سلام، برای پیگیری حواله " + order.order_code + " به راهنمایی نیاز دارم.")}><Headset size={18} /> پیگیری از پشتیبانی</button>
      </div></details>
      {order.status === "awaiting_transfer" && <button className="btn btn-primary" onClick={() => onContinue(order)}>ادامهٔ انتقال و ثبت تراکنش</button>}
    </article>)}
  </main>;
}
