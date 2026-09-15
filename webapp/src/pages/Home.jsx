import { useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, CaretLeft, ClipboardText, PaperPlaneTilt, Star } from "@phosphor-icons/react";
import { api } from "../lib/api";
import { marketChange } from "../lib/market";
import { TETHER_LOGO_URL, USDC_LOGO_URL } from "../lib/brand";
import MarketMap from "../components/MarketMapV2";

const ICON_BASE = "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color";
const HEADLINE_COINS = [
  { symbol: "USDT", logo: TETHER_LOGO_URL },
  { symbol: "USDC", logo: USDC_LOGO_URL },
  { symbol: "BTC", logo: `${ICON_BASE}/btc.png` },
  { symbol: "ETH", logo: `${ICON_BASE}/eth.png` },
  { symbol: "SOL", logo: `${ICON_BASE}/sol.png` },
  { symbol: "BNB", logo: `${ICON_BASE}/bnb.png` },
  { symbol: "XRP", logo: `${ICON_BASE}/xrp.png` },
  { symbol: "TON", logo: `${ICON_BASE}/ton.png` },
];

const LOCATIONS = [
  ["کابل", 1700], ["بامیان", 1700], ["مزار شریف", 1900], ["هرات", 1700],
  ["کندهار", 1700], ["ننگرهار", 1800], ["کندز", 1700], ["بدخشان", 1800],
  ["غزنی", 1700], ["هلمند", 1700], ["فراه", 1700], ["تخار", 1700],
  ["بغلان", 1700], ["پروان", 1700], ["پنجشیر", 1800], ["دایکندی", 1800],
  ["غور", 1700], ["فاریاب", 1700], ["جوزجان", 1700], ["سمنگان", 1700],
  ["سرپل", 1700], ["بادغیس", 1700], ["نیمروز", 1700], ["زابل", 1700],
  ["پکتیا", 1700], ["پکتیکا", 1700], ["خوست", 1700], ["لغمان", 1700],
  ["نورستان", 1800], ["کنر", 1700], ["کاپیسا", 1700], ["میدان وردک", 1900],
  ["لوگر", 1700], ["ارزگان", 1700],
];

function HeadlineCrypto({ location, duration, snapshot, now }) {
  const [coinIndex, setCoinIndex] = useState(() => Math.floor(Math.random() * HEADLINE_COINS.length));

  useEffect(() => {
    setCoinIndex((current) => {
      if (HEADLINE_COINS.length < 2) return 0;
      let next = current;
      while (next === current) next = Math.floor(Math.random() * HEADLINE_COINS.length);
      return next;
    });
  }, [location]);

  const coin = HEADLINE_COINS[coinIndex];
  const change = marketChange(snapshot, coin.symbol, now);
  const rounded = change == null ? null : Number(change.toFixed(2));
  const sign = rounded == null ? "" : rounded > 0 ? "+" : rounded < 0 ? "−" : "";
  const value = rounded == null ? "··" : `${sign}${Math.abs(rounded).toFixed(2)}%`;

  return (
    <span
      key={`${location}-${coin.symbol}`}
      className="headline-crypto"
      style={{ "--headline-coin-duration": `${duration}ms` }}
      aria-label={`${coin.symbol} ${value}`}
    >
      <img src={coin.logo} alt="" />
      <span className="num">{value}</span>
    </span>
  );
}

export default function Home({ navigate, startTransaction }) {
  const [stats, setStats] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [now, setNow] = useState(Date.now());
  const [locationIndex, setLocationIndex] = useState(0);

  useEffect(() => {
    let mounted = true;
    api.getStats().then((value) => mounted && setStats(value)).catch(() => {});
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    let mounted = true;
    let pending = false;
    async function refresh() {
      if (pending || document.hidden) return;
      pending = true;
      try {
        const value = await api.getMarketSnapshot();
        if (mounted) setSnapshot(value);
      } catch (_) {
        if (mounted) setSnapshot(null);
      } finally {
        pending = false;
        if (mounted) setNow(Date.now());
      }
    }
    refresh();
    const timer = window.setInterval(refresh, 90000);
    const clock = window.setInterval(() => setNow(Date.now()), 15000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
      window.clearInterval(clock);
    };
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
      <section className="home-intro" aria-labelledby="home-title">
        <MarketMap activeLocation={location} />
        <h1 id="home-title" className="home-title-stack">
          <span className="home-title-copy home-title-copy-market">
            <span>مرجع خرید و فروش</span>
            <HeadlineCrypto location={location} duration={locationDuration} snapshot={snapshot} now={now} />
            <span>رمز ارز در</span>
          </span>
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

      <section className="trade-panel trade-panel-actions-only" aria-label="خرید و فروش رمز ارز">
        <div className="trade-actions trade-actions-premium">
          <button className="trade-cart-btn purchase" onClick={() => startTransaction("buy")}>
            <span className="trade-cart-icon" aria-hidden="true"><ArrowDownLeft size={18} weight="bold" /></span>
            <span className="trade-cart-text">خرید رمز ارز</span>
          </button>
          <button className="trade-cart-btn sale" onClick={() => startTransaction("sell")}>
            <span className="trade-cart-icon" aria-hidden="true"><ArrowUpRight size={18} weight="bold" /></span>
            <span className="trade-cart-text">فروش رمز ارز</span>
          </button>
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
