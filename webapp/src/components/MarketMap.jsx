import { useEffect, useState } from "react";
import { Pause, Play } from "@phosphor-icons/react";
import { api } from "../lib/api";
import { marketChange } from "../lib/market";
import { TETHER_LOGO_URL, USDC_LOGO_URL } from "../lib/brand";
import afghanistanMap from "../assets/afghanistan-dots.webp";

// Decorative anchors on the supplied map, not locations of customer activity.
const COINS = [
  { symbol: "USDT", name: "تتر", logo: TETHER_LOGO_URL, x: "27%", y: "52%", delay: "-1s", color: "#14977b" },
  { symbol: "USDC", name: "یو‌اس‌دی کوین", logo: USDC_LOGO_URL, x: "61%", y: "47%", delay: "-8s", color: "#2775ca" },
  { symbol: "BTC", name: "بیت‌کوین", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/btc.png", x: "41%", y: "76%", delay: "-5s", color: "#c87b1c" },
  { symbol: "SOL", name: "سولانا", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/sol.png", x: "47%", y: "30%", delay: "-11s", color: "#7861bd" },
];

function CoinLogo({ coin }) {
  const [failed, setFailed] = useState(false);
  return failed ? <span className="map-coin-fallback">{coin.symbol}</span> : <img src={coin.logo} alt="" onError={() => setFailed(true)} />;
}

export default function MarketMap() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const [hidden, setHidden] = useState(document.hidden);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    let mounted = true;
    let pending = false;
    async function refresh() {
      if (document.hidden || pending) return;
      pending = true;
      try {
        const value = await api.getMarketSnapshot();
        if (mounted) setSnapshot(value);
      } catch (_) {
        if (mounted) setSnapshot(null);
      } finally {
        pending = false;
        if (mounted) { setLoading(false); setNow(Date.now()); }
      }
    }
    function visibility() { setHidden(document.hidden); if (!document.hidden) { setNow(Date.now()); refresh(); } }
    refresh();
    const timer = window.setInterval(refresh, 90000);
    const clock = window.setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 15000);
    document.addEventListener("visibilitychange", visibility);
    return () => { mounted = false; window.clearInterval(timer); window.clearInterval(clock); document.removeEventListener("visibilitychange", visibility); };
  }, []);
  const available = COINS.some((coin) => marketChange(snapshot, coin.symbol, now) !== null);
  return <figure className={"market-map " + (paused || hidden ? "is-paused" : "")}>
    <div className="map-stage" style={{ "--map-image": 'url("' + afghanistanMap + '")' }}>
      <div className="afghanistan-dots" role="img" aria-label="نقشهٔ نقطه‌یی افغانستان" />
      {COINS.map((coin) => {
        const change = marketChange(snapshot, coin.symbol, now);
        const rounded = change === null ? null : Number(change.toFixed(2));
        const tone = rounded === null || rounded === 0 ? "neutral" : rounded > 0 ? "positive" : "negative";
        return <div key={coin.symbol} className="map-anchor" style={{ left: coin.x, top: coin.y, "--coin-color": coin.color, "--delay": coin.delay }}>
          <span className="map-pulse" aria-hidden="true" />
          <div className="map-token" aria-label={coin.name + "، تغییر ۲۴ ساعته: " + (rounded === null ? "در دسترس نیست" : rounded + " درصد")}>
            <span className={"map-change num " + tone}>{rounded === null ? coin.symbol : (rounded > 0 ? "+" : "") + rounded.toFixed(2) + "%"}</span>
            <span className="map-coin"><CoinLogo coin={coin} /></span>
          </div>
        </div>;
      })}
    </div>
    <figcaption>
      <span>{loading ? "دریافت تغییرات بازار…" : available ? <>تغییرات ۲۴ ساعتهٔ بازار · <a href="https://www.coingecko.com/" target="_blank" rel="noreferrer">CoinGecko</a></> : "تغییرات بازار فعلاً در دسترس نیست"}</span>
      <button className="map-motion-button" aria-label={paused ? "ادامهٔ انیمیشن نقشه" : "توقف انیمیشن نقشه"} aria-pressed={paused} onClick={() => setPaused((value) => !value)}>{paused ? <Play size={14} weight="fill" /> : <Pause size={14} weight="fill" />}</button>
    </figcaption>
  </figure>;
}
