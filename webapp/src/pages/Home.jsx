import { useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, ArrowsLeftRight, CaretLeft, ClipboardText, PaperPlaneTilt, Star } from "@phosphor-icons/react";
import { api } from "../lib/api";
import { SARAF_LOGO_URL } from "../lib/brand";
import AppMenu from "../components/AppMenu";
import MarketMap from "../components/MarketMap";

const LOCATIONS = [
  ["کابل", 1700],
  ["بامیان", 1700],
  ["مزار شریف", 1900],
  ["هرات", 1700],
  ["کندهار", 1700],
  ["ننگرهار", 1800],
  ["کندز", 1700],
  ["بدخشان", 1800],
  ["غزنی", 1700],
  ["هلمند", 1700],
  ["فراه", 1700],
  ["تخار", 1700],
  ["بغلان", 1700],
  ["پروان", 1700],
  ["پنجشیر", 1800],
  ["دایکندی", 1800],
  ["غور", 1700],
  ["فاریاب", 1700],
  ["جوزجان", 1700],
  ["سمنگان", 1700],
  ["سرپل", 1700],
  ["بادغیس", 1700],
  ["نیمروز", 1700],
  ["زابل", 1700],
  ["پکتیا", 1700],
  ["پکتیکا", 1700],
  ["خوست", 1700],
  ["لغمان", 1700],
  ["نورستان", 1800],
  ["کنر", 1700],
  ["کاپیسا", 1700],
  ["میدان وردک", 1900],
  ["لوگر", 1700],
  ["ارزگان", 1700],
];

export default function Home({ navigate, startTransaction }) {
  const [stats, setStats] = useState(null);
  const [locationIndex, setLocationIndex] = useState(0);

  useEffect(() => {
    let mounted = true;
    api.getStats().then((value) => mounted && setStats(value)).catch(() => {});
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    const duration = LOCATIONS[locationIndex][1];
    const timer = window.setTimeout(() => {
      setLocationIndex((index) => (index + 1) % LOCATIONS.length);
    }, duration);
    return () => window.clearTimeout(timer);
  }, [locationIndex]);

  const [location, locationDuration] = LOCATIONS[locationIndex];

  return (
    <main className="app-shell home-shell">
      <header className="home-header">
        <AppMenu navigate={navigate} />
        <div className="home-brand"><img src={SARAF_LOGO_URL} alt="صراف" /></div>
      </header>
      <section className="home-intro" aria-labelledby="home-title">
        <MarketMap />
        <h1 id="home-title" className="home-title-stack">
          <span className="home-title-copy">مرجع خرید و فروش رمز ارز در</span>
          <span className="home-afghanistan-line" aria-label={`افغانستان، ${location}`}>
            <span className="home-afghanistan-prefix">افغانســــــــــــــ</span>
            <span className="home-location-window">
              <span
                key={locationIndex}
                className="home-location-word"
                style={{ "--location-duration": `${locationDuration}ms` }}
              >
                {location}
              </span>
            </span>
            <span className="home-afghanistan-suffix">ــــــــــــتان</span>
          </span>
        </h1>
      </section>
      <section className="trade-panel" aria-labelledby="trade-title">
        <div className="trade-panel-heading"><div><h2 id="trade-title">خرید و فروش</h2><p>تتر و یو‌اس‌دی کوین <bdi>USDT / USDC</bdi></p></div><ArrowsLeftRight size={23} /></div>
        <div className="trade-actions">
          <button className="trade-action purchase" onClick={() => startTransaction("buy")}><ArrowDownLeft size={21} weight="bold" /> خرید رمزارز</button>
          <button className="trade-action sale" onClick={() => startTransaction("sell")}><ArrowUpRight size={21} weight="bold" /> فروش رمزارز</button>
        </div>
      </section>
      <button className="remittance-entry" onClick={() => navigate("remittance")}>
        <span className="remittance-entry-icon"><PaperPlaneTilt size={25} /></span>
        <span><strong>حواله از طریق کریپتو</strong><small>ارسال رمزارز؛ دریافت افغانی در افغانستان</small></span>
        <CaretLeft size={18} />
      </button>
      <nav className="home-shortcuts" aria-label="پیگیری درخواست‌ها">
        <button onClick={() => navigate("orders")}><ClipboardText size={20} /><span>سفارش‌های من</span><CaretLeft size={15} /></button>
        <button onClick={() => navigate("remittances")}><PaperPlaneTilt size={20} /><span>حواله‌های من</span><CaretLeft size={15} /></button>
      </nav>
      <button className="home-social-proof" onClick={() => navigate("reviews")}>
        <Star size={17} weight="fill" />
        <span>{stats?.average_rating > 0 ? <><b className="num">{Number(stats.average_rating).toFixed(1)}</b> امتیاز کاربران</> : "نظرات کاربران"}</span>
        {Number.isFinite(Number(stats?.completed_orders)) && stats?.completed_orders != null && <small>{Number(stats.completed_orders).toLocaleString("fa-AF")} معاملهٔ تکمیل‌شده</small>}
        <CaretLeft size={15} />
      </button>
    </main>
  );
}
