import { useEffect, useState } from "react";
import { CaretRight, ClipboardText, TrendUp, TrendDown, Archive } from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import StatusBadge from "../components/StatusBadge";
import OrderTimeline from "../components/OrderTimeline";
import RatingStars from "../components/RatingStars";
import Skeleton from "../components/Skeleton";
import { assetLogo, ASSET_NAMES_FA, normalizeAsset } from "../lib/brand";

function orderAsset(order) {
  return normalizeAsset(order.asset || "USDT");
}

function OrderDetail({ order, onBack, onRated, showError }) {
  const [rating, setRating] = useState(order.rating || 0);
  const [submittingRate, setSubmittingRate] = useState(false);
  const [rated, setRated] = useState(Boolean(order.rating));
  const asset = orderAsset(order);
  const logo = assetLogo(asset);

  async function submitRating(stars) {
    setRating(stars);
    setSubmittingRate(true);
    try {
      await api.rateOrder(order.id, stars);
      setRated(true);
      onRated?.(order.id, stars);
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "ثبت امتیاز موفق نشد.");
    } finally {
      setSubmittingRate(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="header">
        <button className="back-btn" onClick={onBack} aria-label="بازگشت"><CaretRight size={18} weight="bold" /></button>
        <h1>جزییات سفارش</h1>
        <div className="header-spacer" />
      </div>

      <div className="card animate-in">
        <div className="top-row" style={{ marginBottom: 14 }}>
          <span className="order-code num">{asset}-{String(order.id).padStart(5, "0")}</span>
          <StatusBadge status={order.status} />
        </div>
        <div className="info-box">
          <div className="row"><span className="label">نوع</span><span className="value">{order.order_type === "buy" ? "خرید" : "فروش"} {ASSET_NAMES_FA[asset]} ({asset})</span></div>
          <div className="row"><span className="label">مقدار</span><span className="value num" style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><img src={logo} alt={asset} className="tether-badge" style={{ borderRadius: "50%" }} />{Number(order.usdt_amount).toLocaleString()} {asset}</span></div>
          <div className="row"><span className="label">مبلغ</span><span className="value num">{Number(order.total_afn).toLocaleString()} افغانی</span></div>
          {order.network && <div className="row"><span className="label">شبکه</span><span className="value">{order.network}</span></div>}
        </div>
      </div>

      <div className="card animate-in" style={{ animationDelay: "0.04s" }}><div className="section-title">وضعیت سفارش</div><OrderTimeline order={order} /></div>

      {order.status === "completed" && (
        <div className="card animate-in" style={{ animationDelay: "0.08s", textAlign: "center" }}>
          <div className="section-title" style={{ justifyContent: "center" }}>{rated ? "امتیاز شما" : "تجربهٔ شما چگونه بود؟"}</div>
          <RatingStars value={rating} onChange={submitRating} readOnly={rated || submittingRate} size={30} />
          {rated && <div className="notice" style={{ justifyContent: "center", marginTop: 10 }}>از نظر شما سپاس 🙏</div>}
        </div>
      )}
    </div>
  );
}

export default function Orders({ navigate, showError }) {
  const [orders, setOrders] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let mounted = true;
    api.getMyOrders().then((data) => { if (mounted) setOrders(data); }).catch((e) => {
      showError(e instanceof ApiError ? e.message : "دریافت سفارش‌ها موفق نشد.");
      if (mounted) setOrders([]);
    }).finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleRated(orderId, stars) {
    setOrders((prev) => prev.map((o) => (o.id === orderId ? { ...o, rating: stars } : o)));
  }

  if (selected) return <OrderDetail order={selected} onBack={() => setSelected(null)} onRated={handleRated} showError={showError} />;

  return (
    <div className="app-shell">
      <div className="header">
        <button className="back-btn" onClick={() => navigate("home")} aria-label="بازگشت"><CaretRight size={18} weight="bold" /></button>
        <h1><ClipboardText size={18} className="header-icon" weight="bold" /> سفارش‌های من</h1>
        <div className="header-spacer" />
      </div>

      {loading && <Skeleton count={4} />}
      {!loading && orders && orders.length === 0 && <div className="empty-state animate-in"><Archive size={44} className="empty-icon" /><div>هنوز سفارشی ثبت نکرده‌اید.</div></div>}

      {!loading && orders && orders.map((o, i) => {
        const asset = orderAsset(o);
        return (
          <div className="order-card card-tappable animate-in" style={{ animationDelay: `${Math.min(i, 6) * 0.03}s` }} key={o.id} onClick={() => setSelected(o)}>
            <div className="top-row">
              <span className={`type-badge ${o.order_type}`}>{o.order_type === "buy" ? <TrendUp size={15} weight="bold" /> : <TrendDown size={15} weight="bold" />}{o.order_type === "buy" ? "خرید" : "فروش"} {asset}</span>
              <StatusBadge status={o.status} />
            </div>
            <div className="amount-row">
              <span className="usdt-amount num"><img src={assetLogo(asset)} alt={asset} className="tether-badge" style={{ borderRadius: "50%" }} />{Number(o.usdt_amount).toLocaleString()} {asset}</span>
              <span className="afn-amount num">{Number(o.total_afn).toLocaleString()} افغانی</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
