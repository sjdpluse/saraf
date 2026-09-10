import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { marketChange } from "../lib/market";
import { TETHER_LOGO_URL, USDC_LOGO_URL } from "../lib/brand";
import afghanistanMap from "../assets/afghanistan-dots.webp";

const MARKER_CYCLE_SECONDS = 5.2;
const ICON_BASE = "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color";

const COINS = [
  { symbol: "USDT", logo: TETHER_LOGO_URL, accent: "#26a17b" },
  { symbol: "USDC", logo: USDC_LOGO_URL, accent: "#2775ca" },
  { symbol: "BTC", logo: `${ICON_BASE}/btc.png`, accent: "#f7931a" },
  { symbol: "ETH", logo: `${ICON_BASE}/eth.png`, accent: "#627eea" },
  { symbol: "SOL", logo: `${ICON_BASE}/sol.png`, accent: "#8b5cf6" },
  { symbol: "BNB", logo: `${ICON_BASE}/bnb.png`, accent: "#d59b00" },
  { symbol: "XRP", logo: `${ICON_BASE}/xrp.png`, accent: "#23292f" },
  { symbol: "TON", logo: `${ICON_BASE}/ton.png`, accent: "#0098ea" },
  { symbol: "ADA", logo: `${ICON_BASE}/ada.png`, accent: "#2a71d0" },
  { symbol: "DOGE", logo: `${ICON_BASE}/doge.png`, accent: "#c2a633" },
  { symbol: "TRX", logo: `${ICON_BASE}/trx.png`, accent: "#ef0027" },
  { symbol: "AVAX", logo: `${ICON_BASE}/avax.png`, accent: "#e84142" },
  { symbol: "DOT", logo: `${ICON_BASE}/dot.png`, accent: "#e6007a" },
  { symbol: "LINK", logo: `${ICON_BASE}/link.png`, accent: "#2a5ada" },
  { symbol: "LTC", logo: `${ICON_BASE}/ltc.png`, accent: "#345d9d" },
  { symbol: "BCH", logo: `${ICON_BASE}/bch.png`, accent: "#8dc351" },
  { symbol: "XLM", logo: `${ICON_BASE}/xlm.png`, accent: "#141414" },
  { symbol: "SHIB", logo: `${ICON_BASE}/shib.png`, accent: "#f16b31" },
  { symbol: "UNI", logo: `${ICON_BASE}/uni.png`, accent: "#ff007a" },
  { symbol: "ATOM", logo: `${ICON_BASE}/atom.png`, accent: "#2e3148" },
];

// 20 evenly phase-shifted markers: with a 5.2s cycle and 0.26s spacing,
// several markers are always in their visible/fading phase. This removes the
// blank period that happened when a smaller set happened to be off together.
const FLOATERS = [
  { province: "هرات", coin: 0, x: 15, y: 49, delay: 0, scale: .98 },
  { province: "بلخ", coin: 2, x: 42, y: 26, delay: -.26, scale: .92 },
  { province: "کابل", coin: 1, x: 61, y: 44, delay: -.52, scale: .96 },
  { province: "قندهار", coin: 4, x: 38, y: 75, delay: -.78, scale: .9 },
  { province: "ننگرهار", coin: 5, x: 69, y: 46, delay: -1.04, scale: .94 },
  { province: "کندز", coin: 6, x: 58, y: 25, delay: -1.30, scale: .9 },
  { province: "بامیان", coin: 3, x: 50, y: 44, delay: -1.56, scale: .94 },
  { province: "غزنی", coin: 7, x: 56, y: 57, delay: -1.82, scale: .86 },
  { province: "هلمند", coin: 8, x: 28, y: 73, delay: -2.08, scale: .88 },
  { province: "بدخشان", coin: 9, x: 69, y: 18, delay: -2.34, scale: .9 },
  { province: "فراه", coin: 10, x: 17, y: 64, delay: -2.60, scale: .9 },
  { province: "تخار", coin: 11, x: 61, y: 19, delay: -2.86, scale: .9 },
  { province: "بغلان", coin: 12, x: 55, y: 31, delay: -3.12, scale: .9 },
  { province: "پروان", coin: 13, x: 58, y: 39, delay: -3.38, scale: .88 },
  { province: "دایکندی", coin: 14, x: 43, y: 56, delay: -3.64, scale: .9 },
  { province: "غور", coin: 15, x: 32, y: 50, delay: -3.90, scale: .88 },
  { province: "فاریاب", coin: 16, x: 33, y: 26, delay: -4.16, scale: .9 },
  { province: "پکتیا", coin: 17, x: 62, y: 61, delay: -4.42, scale: .88 },
  { province: "خوست", coin: 18, x: 67, y: 61, delay: -4.68, scale: .88 },
  { province: "نیمروز", coin: 19, x: 17, y: 80, delay: -4.94, scale: .9 },
];

// Approximate visual centres on the supplied 3:2 dotted map. The highlight is
// clipped by the same Afghanistan mask, so only map dots brighten. These are
// visual hotspots, not administrative-boundary polygons.
const PROVINCE_HOTSPOTS = {
  "کابل": [61, 44, 13, 11], "بامیان": [50, 44, 14, 12], "مزار شریف": [42, 26, 15, 10],
  "هرات": [15, 49, 16, 14], "کندهار": [38, 75, 17, 13], "ننگرهار": [69, 46, 12, 10],
  "کندز": [58, 25, 12, 9], "بدخشان": [69, 18, 16, 12], "غزنی": [56, 57, 13, 11],
  "هلمند": [28, 73, 18, 14], "فراه": [17, 64, 17, 15], "تخار": [61, 19, 13, 9],
  "بغلان": [55, 31, 13, 10], "پروان": [58, 39, 11, 9], "پنجشیر": [61, 34, 9, 7],
  "دایکندی": [43, 56, 14, 11], "غور": [32, 50, 17, 13], "فاریاب": [33, 26, 15, 10],
  "جوزجان": [38, 23, 13, 9], "سمنگان": [47, 28, 13, 10], "سرپل": [39, 33, 14, 11],
  "بادغیس": [22, 37, 15, 12], "نیمروز": [17, 80, 18, 13], "زابل": [47, 70, 14, 11],
  "پکتیا": [62, 61, 11, 9], "پکتیکا": [58, 68, 15, 11], "خوست": [67, 61, 10, 8],
  "لغمان": [65, 42, 9, 8], "نورستان": [68, 34, 12, 10], "کنر": [72, 39, 9, 9],
  "کاپیسا": [61, 38, 9, 7], "میدان وردک": [57, 49, 12, 10], "لوگر": [61, 52, 10, 9],
  "ارزگان": [44, 64, 14, 11],
};

function CoinLogo({ coin }) {
  const [failed, setFailed] = useState(false);
  return failed
    ? <span className="map-coin-fallback">{coin.symbol}</span>
    : <img src={coin.logo} alt="" onError={() => setFailed(true)} />;
}

export default function MarketMap({ activeLocation }) {
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

  const hotspot = PROVINCE_HOTSPOTS[activeLocation] || PROVINCE_HOTSPOTS["کابل"];

  return (
    <figure className={"market-map " + (hidden ? "is-paused" : "")} aria-label="نمای زندهٔ رمزارزها روی نقشهٔ افغانستان">
      <div className="map-stage" style={{ "--map-image": `url("${afghanistanMap}")` }}>
        <div className="afghanistan-dots" role="img" aria-label="نقشهٔ نقطه‌یی افغانستان" />
        <div
          key={activeLocation}
          className="province-highlight"
          style={{
            "--province-x": `${hotspot[0]}%`,
            "--province-y": `${hotspot[1]}%`,
            "--province-w": `${hotspot[2]}%`,
            "--province-h": `${hotspot[3]}%`,
          }}
          aria-hidden="true"
        />
        <div className="map-market-flow" aria-hidden="true">
          {FLOATERS.map((floater, index) => {
            const coin = COINS[floater.coin];
            const change = marketChange(snapshot, coin.symbol, now);
            const rounded = change === null ? null : Number(change.toFixed(2));
            const sign = rounded === null ? null : rounded > 0 ? "+" : rounded < 0 ? "−" : "";
            const value = rounded === null ? null : Math.abs(rounded).toFixed(2);

            return (
              <div
                className="map-floater"
                data-province={floater.province}
                key={`${floater.province}-${coin.symbol}-${index}`}
                style={{
                  left: `${floater.x}%`, top: `${floater.y}%`,
                  "--float-delay": `${floater.delay}s`, "--float-duration": `${MARKER_CYCLE_SECONDS}s`,
                  "--float-scale": floater.scale, "--coin-accent": coin.accent,
                }}
              >
                <div className="map-token">
                  {value !== null && (
                    <span className="map-change num">
                      <span className="map-change-sign">{sign}</span><span className="map-change-value">{value}</span>
                    </span>
                  )}
                  <span className="map-coin-shell"><span className="map-coin"><CoinLogo coin={coin} /></span></span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </figure>
  );
}
