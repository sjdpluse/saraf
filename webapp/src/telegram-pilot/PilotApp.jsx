// The existing Saraf card carousel and branded assets are reused in the REAL React build.
// Deliberately *no* imports of Buy, Sell, KYC, Remittance, or the production api.js.
import { useEffect, useState } from "react";
import {
  ArrowClockwise, Bank, CurrencyCircleDollar, Coins, CurrencyBtc,
  ShieldCheck, WarningCircle, Info, CaretDown,
} from "@phosphor-icons/react";
import CardCarousel from "../components/CardCarousel";
import { getMarket, getTelegramWebApp, isTelegramServerlessAvailable } from "./market";

const tabs = [
  { kind: "currencies", title: "ارزها", icon: CurrencyCircleDollar },
  { kind: "gold", title: "طلا", icon: Coins },
  { kind: "silver", title: "نقره", icon: Coins },
  { kind: "crypto", title: "رمزارزها", icon: CurrencyBtc },
];
const nf = (value, digits = 2) => Number(value).toLocaleString("en-US", {
  minimumFractionDigits: digits, maximumFractionDigits: digits,
});
function formatItem(kind, item) {
  switch (kind) {
    case "currencies": return {
      name: `${item.flag ?? ""} ${item.name ?? item.code}`,
      desc: `۱ ${item.code} به افغانی`,
      value: `${nf(item.afnPerUnit, 4)} AFN`,
    };
    case "gold":
    case "silver": return {
      name: kind === "gold" ? `طلای عیار ${item.karat}` : "نقره خالص",
      desc: `هر مثقال: ${nf(item.afnMethqal, 1)} افغانی`,
      value: `${nf(item.afnGram, 1)} AFN / g`,
    };
    default: return {
      name: item.code,
      desc: "قیمت مرجع جهانی به دالر",
      value: `$${nf(item.usd, item.usd < 0.001 ? 8 : 4)}`,
    };
  }
}
function MarketCard({ kind, item }) {
  const value = formatItem(kind, item);
  return <article className="pilot-market-card">
    <div className="pilot-market-copy">
      <strong>{value.name}</strong><small>{value.desc}</small>
    </div>
    <span className="pilot-market-value" dir="ltr">{value.value}</span>
  </article>;
}

export default function PilotApp() {
  const [kind, setKind] = useState("currencies");
  const [state, setState] = useState({ loading: false, error: "", data: null });
  const [refresh, setRefresh] = useState(0);
  const [cardStep, setCardStep] = useState(0);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const available = isTelegramServerlessAvailable();

  useEffect(() => {
    const wa = getTelegramWebApp();
    if (!wa) return;
    try {
      wa.ready();
      wa.expand();
      wa.setBackgroundColor?.("#f7f9f9");
      wa.setHeaderColor?.("#f7f9f9");
    } catch (_) { /* Telegram client support varies. */ }
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setCardStep(s => s + 1), 2300);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!available) return;
    let cancelled = false;
    setState({ loading: true, error: "", data: null });
    getMarket(kind)
      .then(data => { if (!cancelled) setState({ loading: false, error: "", data }); })
      .catch(error => { if (!cancelled) setState({ loading: false, error: error.message, data: null }); });
    return () => { cancelled = true; };
  }, [kind, refresh, available]);

  return (
    <main className="pilot-app" dir="rtl">
      <div className="pilot-banner"><ShieldCheck size={17} weight="fill" /> آزمایش میزبانی React روی Telegram Serverless</div>
      <section className="pilot-hero">
        <div className="pilot-kicker"><Bank size={19} /> صراف | SARAF</div>
        <div className="home-card-carousel-shell pilot-carousel">
          <CardCarousel activeStep={cardStep} />
        </div>
        <h1>بازارها، به زبان شما</h1>
        <p>نسخهٔ آزمایشی رابط React صراف؛ بدون وابستگی به Railway برای نمایش نرخ مرجع.</p>
        <div className="pilot-hero-badges"><span>🇦🇫 مخصوص افغانستان</span><span>☁️ Telegram Native</span></div>
      </section>
      {!available && <div role="alert" className="pilot-alert pilot-alert-error">
        <WarningCircle size={22} /> این نسخه تنها از طریق Mini App ربات آزمایشی در تلگرام کار می‌کند.
      </div>}
      <section className="pilot-market" aria-labelledby="market-title">
        <div className="pilot-heading">
          <div><small>داده‌های جهانی – فقط برای اطلاع‌رسانی</small><h2 id="market-title">نرخ‌های مرجع</h2></div>
          <button className="pilot-refresh" type="button" disabled={!available || state.loading}
            onClick={() => setRefresh(value => value + 1)} aria-label="بروزرسانی نرخ‌ها">
            <ArrowClockwise size={20} />
          </button>
        </div>
        <div className="pilot-tabs" role="tablist" aria-label="انتخاب بازار">
          {tabs.map(({ kind: nextKind, title, icon: Icon }) =>
            <button type="button" role="tab" aria-selected={kind === nextKind}
              className={kind === nextKind ? "selected" : ""} key={nextKind}
              onClick={() => setKind(nextKind)}><Icon size={19} />{title}</button>)}
        </div>
        {state.loading && <div className="pilot-info" role="status">در حال دریافت اطلاعات از Telegram Serverless…</div>}
        {state.error && <div role="alert" className="pilot-alert pilot-alert-error">{state.error}</div>}
        {!state.loading && !state.error && state.data?.items?.length === 0 &&
          <div className="pilot-info" role="status">نرخی در دسترس نیست.</div>}
        <div className="pilot-items">
          {(state.data?.items ?? []).map(item =>
            <MarketCard key={item.code ?? item.karat} kind={kind} item={item} />)}
        </div>
        {state.data && <p className="pilot-source">
          منبع: {state.data.source || "نامشخص"} · زمان دریافت: {state.data.fetchedAt ? new Date(state.data.fetchedAt).toLocaleString("fa-AF") : "نامشخص"}
        </p>}
      </section>
      <section className="pilot-trading-placeholder">
        <div className="pilot-heading"><div><small>مرحلهٔ بعدی توسعه</small><h2>خدمات مالی صراف</h2></div></div>
        <div className="pilot-disabled-list">
          <div><CurrencyCircleDollar size={20} /><span>خرید و فروش USDT / USDC</span><b>غیرفعال در آزمایش</b></div>
          <div><Bank size={20} /><span>حواله‌های بین‌المللی</span><b>غیرفعال در آزمایش</b></div>
          <div><ShieldCheck size={20} /><span>تأیید هویت و سفارش‌ها</span><b>غیرفعال در آزمایش</b></div>
        </div>
      </section>
      <footer className="pilot-footer">
        <button type="button" className="pilot-disclaimer" onClick={() => setShowDisclaimer(v => !v)}
          aria-expanded={showDisclaimer}><Info size={18} /> توضیحات مهم <CaretDown size={15}/></button>
        {showDisclaimer && <p>این نرخ‌ها صرفاً اطلاعات مرجع جهانی هستند و ممکن است با بازار سرای شهزاده و قیمت معامله تفاوت داشته باشند. این نسخه هیچ پرداخت، ثبت سفارش، ذخیرهٔ مدارک هویت یا تغییر در پایگاه دادهٔ کاربران انجام نمی‌دهد.</p>}
        <p>© 2026 Saraf · نسخه آزمایشی React / Telegram Serverless</p>
      </footer>
    </main>
  );
}
