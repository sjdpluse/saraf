import { useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, ArrowsLeftRight, CaretLeft, ClipboardText, PaperPlaneTilt, Star } from "@phosphor-icons/react";
import { api } from "../lib/api";
import { SARAF_LOGO_URL } from "../lib/brand";
import AppMenu from "../components/AppMenu";
import MarketMap from "../components/MarketMap";

export default function Home({ navigate, startTransaction }) {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    let mounted = true;
    api.getStats().then((value) => mounted && setStats(value)).catch(() => {});
    return () => { mounted = false; };
  }, []);

  return (
    <main className="app-shell home-shell">
      <header className="home-header">
        <div className="home-brand"><img src={SARAF_LOGO_URL} alt="" /><span>صراف<small>دنیای کریپتو، به افغانی</small></span></div>
        <AppMenu navigate={navigate} />
      </header>
      <section className="home-intro" aria-labelledby="home-title">
        <span className="home-eyebrow">از کریپتو تا افغانی</span>
        <h1 id="home-title">خرید، فروش و حواله<br /><span>ساده‌تر با صراف.</span></h1>
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
