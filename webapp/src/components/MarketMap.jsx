import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { marketChange } from "../lib/market";
import { TETHER_LOGO_URL, USDC_LOGO_URL } from "../lib/brand";
import afghanistanMap from "../assets/afghanistan-dots.webp";

const MARKER_CYCLE_SECONDS = 4.8;

const COINS = [
  { symbol: "USDT", name: "تتر", logo: TETHER_LOGO_URL, accent: "#26a17b" },
  { symbol: "USDC", name: "یو‌اس‌دی کوین", logo: USDC_LOGO_URL, accent: "#2775ca" },
  { symbol: "BTC", name: "بیت‌کوین", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/btc.png", accent: "#f7931a" },
  { symbol: "SOL", name: "سولانا", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/sol.png", accent: "#8b5cf6" },
  { symbol: "BNB", name: "بی‌ان‌بی", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/bnb.png", accent: "#d59b00" },
  { symbol: "XRP", name: "ایکس‌آرپی", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/xrp.png", accent: "#23292f" },
  { symbol: "TON", name: "تون", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/ton.png", accent: "#0098ea" },
];

// Percentage anchors are tied to recognizable province centers on the exact
// 3:2 Afghanistan silhouette used by the Mini App. Keeping them relative to
// the map stage means the markers remain over the same provinces at every
// mobile width instead of drifting with viewport pixels.
const FLOATERS = [
  { province: "هرات", coin: 0, x: 15, y: 49, delay: 0, scale: 0.98 },
  { province: "بلخ", coin: 2, x: 42, y: 26, delay: -0.48, scale: 0.92 },
  { province: "کابل", coin: 1, x: 61, y: 44, delay: -0.96, scale: 0.96 },
  { province: "قندهار", coin: 3, x: 38, y: 75, delay: -1.44, scale: 0.9 },
  { province: "ننگرهار", coin: 4, x: 69, y: 46, delay: -1.92, scale: 0.94 },
  { province: "کندز", coin: 5, x: 58, y: 25, delay: -2.4, scale: 0.9 },
  { province: "بامیان", coin: 6, x: 50, y: 44, delay: -2.88, scale: 0.94 },
  { province: "غزنی", coin: 2, x: 56, y: 57, delay: -3.36, scale: 0.86 },
  { province: "هلمند", coin: 0, x: 28, y: 73, delay: -3.84, scale: 0.88 },
  { province: "بدخشان", coin: 1, x: 69, y: 18, delay: -4.32, scale: 0.9 },
];

function CoinLogo({ coin }) {
  const [failed, setFailed] = useState(false);
  return failed
    ? <span className="map-coin-fallback">{coin.symbol}</span>
    : <img src={coin.logo} alt="" onError={() => setFailed(true)} />;
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
                data-province={floater.province}
                key={`${floater.province}-${coin.symbol}-${index}`}
                style={{
                  left: `${floater.x}%`,
                  top: `${floater.y}%`,
                  "--float-delay": `${floater.delay}s`,
                  "--float-duration": `${MARKER_CYCLE_SECONDS}s`,
                  "--float-scale": floater.scale,
                  "--coin-accent": coin.accent,
                }}
              >
                <div className="map-token">
                  {rounded !== null && (
                    <span className="map-change num">
                      {(rounded > 0 ? "+" : "") + rounded.toFixed(2) + "%"}
                    </span>
                  )}
                  <span className="map-coin-shell">
                    <span className="map-coin"><CoinLogo coin={coin} /></span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </figure>
  );
}
