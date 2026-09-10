import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { marketChange } from "../lib/market";
import { TETHER_LOGO_URL, USDC_LOGO_URL } from "../lib/brand";
import afghanistanMap from "../assets/afghanistan-dots.webp";

const COINS = [
  { symbol: "USDT", name: "تتر", logo: TETHER_LOGO_URL, color: "#26A17B" },
  { symbol: "USDC", name: "یو‌اس‌دی کوین", logo: USDC_LOGO_URL, color: "#2775CA" },
  { symbol: "BTC", name: "بیت‌کوین", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/btc.png", color: "#F7931A" },
  { symbol: "SOL", name: "سولانا", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/sol.png", color: "#9945FF" },
  { symbol: "BNB", name: "بی‌ان‌بی", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/bnb.png", color: "#F3BA2F" },
  { symbol: "XRP", name: "ایکس‌آرپی", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/xrp.png", color: "#23292F" },
  { symbol: "TON", name: "تون", logo: "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color/ton.png", color: "#0098EA" },
];

const MAP_POSITIONS = [
  [18, 50], [25, 65], [31, 39], [37, 73], [43, 50], [49, 30],
  [54, 62], [60, 43], [66, 58], [71, 34], [77, 49], [83, 41],
];

function CoinLogo({ coin }) {
  const [failed, setFailed] = useState(false);
  return failed ? <span className="map-coin-fallback">{coin.symbol}</span> : <img src={coin.logo} alt="" onError={() => setFailed(true)} />;
}

function randomPosition(previous) {
  const choices = MAP_POSITIONS.filter((_, index) => index !== previous);
  const selected = choices[Math.floor(Math.random() * choices.length)];
  return { x: selected[0], y: selected[1], index: MAP_POSITIONS.indexOf(selected) };
}

export default function MarketMap() {
  const [snapshot, setSnapshot] = useState(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [cycle, setCycle] = useState(0);
  const [position, setPosition] = useState(() => randomPosition(-1));
  const positionIndex = useRef(position.index);
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
      if (!document.hidden) { setNow(Date.now()); refresh(); }
    }
    refresh();
    const timer = window.setInterval(refresh, 90000);
    const clock = window.setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 15000);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      mounted = false;
      window.clearInterval(timer);
      window.clearInterval(clock);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  useEffect(() => {
    if (hidden) return undefined;
    const timer = window.setInterval(() => {
      setActiveIndex((index) => (index + 1) % COINS.length);
      setCycle((value) => value + 1);
      const next = randomPosition(positionIndex.current);
      positionIndex.current = next.index;
      setPosition(next);
    }, 500);
    return () => window.clearInterval(timer);
  }, [hidden]);

  const coin = COINS[activeIndex];
  const change = marketChange(snapshot, coin.symbol, now);
  const rounded = change === null ? null : Number(change.toFixed(2));

  return (
    <figure className={"market-map " + (hidden ? "is-paused" : "")}>
      <div className="map-stage" style={{ "--map-image": `url("${afghanistanMap}")` }}>
        <div className="afghanistan-dots" role="img" aria-label="نقشهٔ نقطه‌یی افغانستان" />
        <div
          key={`${coin.symbol}-${cycle}`}
          className="map-anchor map-anchor-active"
          style={{ left: `${position.x}%`, top: `${position.y}%`, "--coin-color": coin.color }}
        >
          <div className="map-token" aria-label={`${coin.name}، تغییر ۲۴ ساعته: ${rounded === null ? "در دسترس نیست" : `${rounded} درصد`}`}>
            <span className="map-coin"><CoinLogo coin={coin} /></span>
            {rounded !== null && <span className="map-change num" style={{ color: coin.color }}>{(rounded > 0 ? "+" : "") + rounded.toFixed(2) + "%"}</span>}
          </div>
        </div>
      </div>
    </figure>
  );
}
