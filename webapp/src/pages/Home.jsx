import { useEffect, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ClipboardText,
  FileText,
  CaretLeft,
  ShieldCheck,
  Clock,
  HandCoins,
  Headset,
  Users,
  Star,
} from "@phosphor-icons/react";
import { api } from "../lib/api";
import { SARAF_LOGO_URL, TETHER_LOGO_URL, USDC_LOGO_URL, normalizeAsset } from "../lib/brand";

const ASSETS = [
  { code: "USDT", name: "تتر", logo: TETHER_LOGO_URL },
  { code: "USDC", name: "USD Coin", logo: USDC_LOGO_URL },
];

export default function Home({ navigate, startTransaction, selectedAsset = "USDT", onSelectAsset }) {
  const [stats, setStats] = useState(null);
  const asset = normalizeAsset(selectedAsset);

  useEffect(() => {
    let mounted = true;
    api
      .getStats()
      .then((s) => mounted && setStats(s))
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="app-shell">
      <div className="hero-card animate-in">
        <div className="hero-top">
          <div className="hero-row">
            <div className="hero-brand">
              <div className="hero-logo">
                <img src={SARAF_LOGO_URL} alt="صراف" />
              </div>
              <span className="hero-brand-name">صراف</span>
            </div>
          </div>

          <div className="hero-tagline">خرید و فروش USDT و USDC با نرخ منصفانه و پرداخت آسان</div>

          <div className="hero-chip-row">
            <div className="hero-chip">
              <ShieldCheck size={13} weight="fill" />
              بررسی دستی هر سفارش
            </div>
            <div className="hero-chip">
              <Clock size={13} weight="fill" />
              تحویل زیر ۱ ساعت
            </div>
          </div>
        </div>

        <div style={{ padding: "0 16px 14px" }}>
          <div className="field-label" style={{ marginBottom: 8 }}>دارایی مورد نظر را انتخاب کنید</div>
          <div className="choice-row">
            {ASSETS.map((item) => (
              <button
                key={item.code}
                className={`choice-btn ${asset === item.code ? "selected" : ""}`}
                onClick={() => onSelectAsset?.(item.code)}
                type="button"
              >
                <img
                  src={item.logo}
                  alt={item.code}
                  style={{ width: 28, height: 28, objectFit: "contain", borderRadius: "50%" }}
                />
                <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", lineHeight: 1.15 }}>
                  <b>{item.code}</b>
                  <small style={{ opacity: 0.65 }}>{item.name}</small>
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="hero-dock">
          <button className="hero-dock-btn buy" onClick={() => startTransaction("buy", asset)}>
            <span className="dock-icon"><ArrowDown size={16} weight="bold" /></span>
            خرید {asset}
          </button>
          <button className="hero-dock-btn sell" onClick={() => startTransaction("sell", asset)}>
            <span className="dock-icon"><ArrowUp size={16} weight="bold" /></span>
            فروش {asset}
          </button>
        </div>
      </div>

      {stats && stats.completed_orders > 0 && (
        <div className="stats-row animate-in" style={{ animationDelay: "0.06s" }}>
          <div className="stat-box">
            <Users size={20} className="stat-icon" weight="fill" />
            <div className="stat-value num">{stats.completed_orders.toLocaleString()}</div>
            <div className="stat-label">معاملهٔ تکمیل‌شده</div>
          </div>
          <div className="stat-box">
            <Star size={20} className="stat-icon" weight="fill" />
            <div className="stat-value num">{stats.average_rating ? stats.average_rating.toFixed(1) : "—"}</div>
            <div className="stat-label">میانگین امتیاز کاربران</div>
          </div>
        </div>
      )}

      <div className="card card-tappable animate-in" style={{ animationDelay: "0.09s" }} onClick={() => navigate("orders")}>
        <div className="list-row">
          <div className="row-icon"><ClipboardText size={20} /></div>
          <div className="row-text">
            <div className="row-title">سفارش‌های من</div>
            <div className="row-subtitle">پیگیری خرید و فروش‌های USDT / USDC</div>
          </div>
          <div className="row-chevron"><CaretLeft size={18} /></div>
        </div>
      </div>

      <div className="card animate-in" style={{ animationDelay: "0.12s" }}>
        <div className="section-title">
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <img src={TETHER_LOGO_URL} alt="USDT" className="tether-badge" style={{ width: 16, height: 16 }} />
            <img src={USDC_LOGO_URL} alt="USDC" className="tether-badge" style={{ width: 16, height: 16, borderRadius: "50%" }} />
          </span>
          چرا صراف؟
        </div>
        <div className="trust-list">
          <div className="trust-item">
            <ShieldCheck size={18} className="trust-icon" weight="fill" />
            نرخ لحظه‌یی بازار برای تصمیم‌گیری روشن‌تر
          </div>
          <div className="trust-item">
            <Clock size={18} className="trust-icon" weight="fill" />
            هر سفارش پیش از اجرا توسط تیم ما به‌صورت دستی بررسی و تایید می‌شود
          </div>
          <div className="trust-item">
            <HandCoins size={18} className="trust-icon" weight="fill" />
            پرداخت حضوری یا آنلاین — هرکدام که برایتان آسان‌تر است
          </div>
          <div className="trust-item">
            <Headset size={18} className="trust-icon" weight="fill" />
            پشتیبانی مستقیم و پاسخ‌گو: @SJDPLUS
          </div>
        </div>
      </div>

      <div className="card card-tappable animate-in" style={{ animationDelay: "0.15s" }} onClick={() => navigate("terms")}>
        <div className="list-row">
          <div className="row-icon"><FileText size={20} /></div>
          <div className="row-text">
            <div className="row-title">قوانین و شرایط استفاده</div>
            <div className="row-subtitle">کارمزدها، زمان تحویل و مسئولیت‌ها</div>
          </div>
          <div className="row-chevron"><CaretLeft size={18} /></div>
        </div>
      </div>
    </div>
  );
}
