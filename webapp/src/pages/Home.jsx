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
import { SARAF_LOGO_URL, TETHER_LOGO_URL } from "../lib/brand";

export default function Home({ navigate, startTransaction }) {
  const [stats, setStats] = useState(null);
  const [rate, setRate] = useState(null);
  const [rateError, setRateError] = useState(false);

  useEffect(() => {
    let mounted = true;
    api
      .getStats()
      .then((s) => mounted && setStats(s))
      .catch(() => {
        /* آمار غیربحرانی است؛ در صورت خطا فقط نمایش داده نمی‌شود */
      });
    api
      .getRateTicker()
      .then((r) => mounted && setRate(r))
      .catch(() => {
        if (mounted) setRateError(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="app-shell">
      {/* --- کارت اصلی: گرادیانت آبی + نرخ لحظه‌یی + داک شیشه‌یی خرید/فروش --- */}
      <div className="hero-card animate-in">
        <div className="hero-top">
          <div className="hero-row">
            <div className="hero-brand">
              <div className="hero-logo">
                <img src={SARAF_LOGO_URL} alt="Saraf" />
              </div>
              <span className="hero-brand-name">Saraf</span>
            </div>
            <div className="live-pill">
              <span className="live-dot" />
              نرخ لحظه‌یی
            </div>
          </div>

          <div className="hero-rate-label">قیمت هر ۱ USDT برای خرید (تقریبی)</div>
          {rate ? (
            <div className="hero-rate-value num">
              {Number(rate.buy_rate).toLocaleString()}
              <span className="unit">افغانی</span>
            </div>
          ) : rateError ? (
            <div className="hero-rate-value" style={{ fontSize: 15, fontWeight: 600, opacity: 0.85 }}>
              نرخ لحظه‌یی موقتاً در دسترس نیست
            </div>
          ) : (
            <div className="hero-rate-value num" style={{ opacity: 0.6 }}>
              …
            </div>
          )}

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

        <div className="hero-dock">
          <button className="hero-dock-btn buy" onClick={() => startTransaction("buy")}>
            <span className="dock-icon">
              <ArrowDown size={16} weight="bold" />
            </span>
            خرید تتر
          </button>
          <button className="hero-dock-btn sell" onClick={() => startTransaction("sell")}>
            <span className="dock-icon">
              <ArrowUp size={16} weight="bold" />
            </span>
            فروش تتر
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
            <div className="stat-value num">
              {stats.average_rating ? stats.average_rating.toFixed(1) : "—"}
            </div>
            <div className="stat-label">میانگین امتیاز کاربران</div>
          </div>
        </div>
      )}

      <div className="card card-tappable animate-in" style={{ animationDelay: "0.09s" }} onClick={() => navigate("orders")}>
        <div className="list-row">
          <div className="row-icon">
            <ClipboardText size={20} />
          </div>
          <div className="row-text">
            <div className="row-title">سفارش‌های من</div>
            <div className="row-subtitle">پیگیری وضعیت خرید/فروش‌های قبلی</div>
          </div>
          <div className="row-chevron">
            <CaretLeft size={18} />
          </div>
        </div>
      </div>

      <div className="card animate-in" style={{ animationDelay: "0.12s" }}>
        <div className="section-title">
          <img src={TETHER_LOGO_URL} alt="" className="tether-badge" style={{ width: 16, height: 16 }} />
          چرا Saraf؟
        </div>
        <div className="trust-list">
          <div className="trust-item">
            <ShieldCheck size={18} className="trust-icon" weight="fill" />
            نرخ لحظه‌یی بر مبنای بازار واقعی صرافی‌های کابل، نه نرخ تخمینی
          </div>
          <div className="trust-item">
            <Clock size={18} className="trust-icon" weight="fill" />
            هر سفارش پیش از پردازش، توسط تیم ما به‌صورت دستی بررسی و تایید می‌شود
          </div>
          <div className="trust-item">
            <HandCoins size={18} className="trust-icon" weight="fill" />
            پرداخت حضوری یا بانکی — هرچه برایتان راحت‌تر است
          </div>
          <div className="trust-item">
            <Headset size={18} className="trust-icon" weight="fill" />
            پشتیبانی مستقیم و پاسخ‌گو: @SJDPLUS
          </div>
        </div>
      </div>

      <div className="card card-tappable animate-in" style={{ animationDelay: "0.15s" }} onClick={() => navigate("terms")}>
        <div className="list-row">
          <div className="row-icon">
            <FileText size={20} />
          </div>
          <div className="row-text">
            <div className="row-title">قوانین و شرایط استفاده</div>
            <div className="row-subtitle">کارمزدها، زمان تحویل و مسئولیت‌ها</div>
          </div>
          <div className="row-chevron">
            <CaretLeft size={18} />
          </div>
        </div>
      </div>
    </div>
  );
}
