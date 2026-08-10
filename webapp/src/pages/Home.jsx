import { useEffect, useState } from "react";
import {
  Wallet,
  TrendUp,
  TrendDown,
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

export default function Home({ navigate, startTransaction }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let mounted = true;
    api
      .getStats()
      .then((s) => mounted && setStats(s))
      .catch(() => {
        /* آمار غیربحرانی است؛ در صورت خطا فقط نمایش داده نمی‌شود */
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="app-shell">
      <div className="brand-hero animate-in">
        <div className="logo-badge">
          <Wallet size={24} weight="fill" />
        </div>
        <div className="titles">
          <h1>Saraf</h1>
          <div className="subtitle">خرید و فروش مطمئن تتر (USDT)</div>
        </div>
      </div>

      <div className="menu-grid animate-in" style={{ animationDelay: "0.03s" }}>
        <div className="menu-tile buy" onClick={() => startTransaction("buy")}>
          <div className="tile-icon">
            <TrendUp size={22} weight="bold" />
          </div>
          <div className="title">خرید تتر</div>
          <div className="subtitle num">AFN → USDT</div>
        </div>
        <div className="menu-tile sell" onClick={() => startTransaction("sell")}>
          <div className="tile-icon">
            <TrendDown size={22} weight="bold" />
          </div>
          <div className="title">فروش تتر</div>
          <div className="subtitle num">USDT → AFN</div>
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
          <ShieldCheck size={16} />
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
