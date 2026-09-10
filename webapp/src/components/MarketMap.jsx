import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { marketChange } from "../lib/market";
import { TETHER_LOGO_URL, USDC_LOGO_URL } from "../lib/brand";
import afghanistanMap from "../assets/afghanistan-dots.webp";

const COINS = [
  { symbol: "USDT", name: "تتر", logo: TETHER_LOGO_URL },
  { symbol: "USDC", name: "یو‌اس‌دی کوین", logo: USDC_LOGO_URL },
  { symbol: "BTC", name: "بیت‌کوین", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/btc.png" },
  { symbol: "SOL", name: "سولانا", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/sol.png" },
  { symbol: "BNB", name: "بی‌ان‌بی", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/bnb.png" },
  { symbol: "XRP", name: "ایکس‌آرپی", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/xrp.png" },
  { symbol: "TON", name: "تون", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/ton.png" },
];

// A deliberately staggered field instead of one random token every 500ms.
// Multiple compact tickers can coexist, creating the continuous market-flow
// effect used by modern exchange hero maps without covering the map itself.
const FLOATERS = [
  { coin: 0, x: 18, y: 68, delay: -0.4, duration: 5.4, scale: 0.92 },
  { coin: 2, x: 28, y: 48, delay: -2.7, duration: 5.8, scale: 0.84 },
  { coin: 1, x: 38, y: 72, delay: -4.1, duration: 6.1, scale: 0.88 },
  { coin: 3, x: 47, y: 42, delay: -1.5, duration: 5.2, scale: 0.78 },
  { coin: 4, x: 56, y: 63, delay: -3.6, duration: 5.9, scale: 0.9 },
  { coin: 5, x: 66, y: 48, delay: -0.9, duration: 6.3, scale: 0.8 },
  { coin: 6, x: 76, y: 66, delay: -4.8, duration: 5.6, scale: 0.86 },
  { coin: 2, x: 82, y: 38, delay: -2.2, duration: 6.4, scale: 0.74 },
  { coin: 0, x: 43, y: 56, delay: -5.1, duration: 6.6, scale: 0.72 },
  { coin: 1, x: 62, y: 76, delay: -1.9, duration: 6.0, scale: 0.76 },
];

function CoinLogo({ coin }) {
  const [failed, setFailed] = useState(false);
  return failed
    ? <span className="map-coin-fallback">{coin.symbol}</span>
    : <img src={coin.logo} alt="" onError={() => setFailed(true)} />;
}

function changeClass(value) {
  if (value === null || value === 0) return "neutral";
  return value > 0 ? "positive" : "negative";
}

export default function MarketMap() {
  const [snapshot, setSnapshot] = useState(null);
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
        if (mounted) setNow(Date.now());
      }
    }

    function visibility() {
      setHidden(document.hidden);
      if (!document.hidden) {
        setNow(Date.now());
        refresh();
      }
    }

    refresh();
    const timer = window.setInterval(refresh, 90000);
    const clock = window.setInterval(() => {
      if (!document.hidden) setNow(Date.now());
    }, 15000);
    document.addEventListener("visibilitychange", visibility);

    return () => {
      mounted = false;
      window.clearInterval(timer);
      window.clearInterval(clock);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  return (
    <figure
      className={"market-map " + (hidden ? "is-paused" : "")}
      aria-label="نمای زندهٔ رمزارزها روی نقشهٔ افغانستان"
    >
      <div className="map-stage" style={{ "--map-image": `url("${afghanistanMap}")` }}>
        <div className="afghanistan-dots" role="img" aria-label="نقشهٔ نقطه‌یی افغانستان" />
        <div className="map-market-flow" aria-hidden="true">
          {FLOATERS.map((floater, index) => {
            const coin = COINS[floater.coin];
            const change = marketChange(snapshot, coin.symbol, now);
            const rounded = change === null ? null : Number(change.toFixed(2));

            return (
              <div
                className="map-floater"
                key={`${coin.symbol}-${index}`}
                style={{
                  left: `${floater.x}%`,
                  top: `${floater.y}%`,
                  "--float-delay": `${floater.delay}s`,
                  "--float-duration": `${floater.duration}s`,
                  "--float-scale": floater.scale,
                }}
              >
                <div className="map-token">
                  <span className="map-coin"><CoinLogo coin={coin} /></span>
                  {rounded !== null && (
                    <span className={`map-change num ${changeClass(rounded)}`}>
                      {(rounded > 0 ? "+" : "") + rounded.toFixed(2) + "%"}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </figure>
  );
}
