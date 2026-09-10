import { useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, ArrowsLeftRight, CaretLeft, ClipboardText, PaperPlaneTilt, Star } from "@phosphor-icons/react";
import { api } from "../lib/api";
import { SARAF_LOGO_URL } from "../lib/brand";
import AppMenu from "../components/AppMenu";
import MarketMap from "../components/MarketMap";

const LOCATIONS = [
  ["افغانستان", 2000],
  ["کابل", 1000],
  ["بامیان", 1000],
  ["مزار شریف", 1000],
  ["هرات", 1000],
  ["کندهار", 1000],
  ["ننگرهار", 1000],
  ["کندز", 1000],
  ["بدخشان", 1000],
  ["غزنی", 1000],
  ["هلمند", 1000],
  ["فراه", 1000],
  ["تخار", 1000],
  ["بغلان", 1000],
  ["پروان", 1000],
  ["پنجشیر", 1000],
  ["دایکندی", 1000],
  ["غور", 1000],
  ["فاریاب", 1000],
  ["جوزجان", 1000],
  ["سمنگان", 1000],
  ["سرپل", 1000],
  ["بادغیس", 1000],
  ["نیمروز", 1000],
  ["زابل", 1000],
  ["پکتیا", 1000],
  ["پکتیکا", 1000],
  ["خوست", 1000],
  ["لغمان", 1000],
  ["نورستان", 1000],
  ["کنر", 1000],
  ["کاپیسا", 1000],
  ["میدان وردک", 1000],
  ["لوگر", 1000],
  ["ارزگان", 1000],
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
        <h1 id="home-title">
          <span className="home-title-copy">مرجع مطمئن خرید و فروش رمز ارز</span>
          <span className="home-location-line">در <span className="home-location-window"><span key={locationIndex} className="home-location-word" style={{ "--location-duration": `${locationDuration}ms` }}>{location}</span></span></span>
        </h1>
        <MarketMap />
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
