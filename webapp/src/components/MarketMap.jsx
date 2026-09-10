import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { marketChange } from "../lib/market";
import { TETHER_LOGO_URL, USDC_LOGO_URL } from "../lib/brand";
import afghanistanMap from "../assets/afghanistan-dots.webp";

const ICON_BASE = "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color";
const SLOT_INTERVAL_MS = 300;
const ACTIVE_SLOTS = 4;
const PROVINCE_DATA_URL = "https://raw.githubusercontent.com/periodo/periodo-places/1563735c333174952541241c7c9640b346387533/gazetteers/afghan-provinces.json";

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

const MARKERS = [
  { province: "هرات", coin: 0, x: 15, y: 49, scale: .98 },
  { province: "بلخ", coin: 2, x: 42, y: 26, scale: .92 },
  { province: "کابل", coin: 1, x: 61, y: 44, scale: .96 },
  { province: "قندهار", coin: 4, x: 38, y: 75, scale: .9 },
  { province: "ننگرهار", coin: 5, x: 69, y: 46, scale: .94 },
  { province: "کندز", coin: 6, x: 58, y: 25, scale: .9 },
  { province: "بامیان", coin: 3, x: 50, y: 44, scale: .94 },
  { province: "غزنی", coin: 7, x: 56, y: 57, scale: .86 },
  { province: "هلمند", coin: 8, x: 28, y: 73, scale: .88 },
  { province: "بدخشان", coin: 9, x: 69, y: 18, scale: .9 },
  { province: "فراه", coin: 10, x: 17, y: 64, scale: .9 },
  { province: "تخار", coin: 11, x: 61, y: 19, scale: .9 },
  { province: "بغلان", coin: 12, x: 55, y: 31, scale: .9 },
  { province: "پروان", coin: 13, x: 58, y: 39, scale: .88 },
  { province: "دایکندی", coin: 14, x: 43, y: 56, scale: .9 },
  { province: "غور", coin: 15, x: 32, y: 50, scale: .88 },
  { province: "فاریاب", coin: 16, x: 33, y: 26, scale: .9 },
  { province: "پکتیا", coin: 17, x: 62, y: 61, scale: .88 },
  { province: "خوست", coin: 18, x: 67, y: 61, scale: .88 },
  { province: "نیمروز", coin: 19, x: 17, y: 80, scale: .9 },
];

const PROVINCE_NAME_MAP = {
  "کابل": "Kabul", "بامیان": "Bamyan", "مزار شریف": "Balkh", "بلخ": "Balkh",
  "هرات": "Herat", "کندهار": "Kandahar", "ننگرهار": "Nangarhar", "کندز": "Kunduz",
  "بدخشان": "Badakhshan", "غزنی": "Ghazni", "هلمند": "Helmand", "فراه": "Farah",
  "تخار": "Takhar", "بغلان": "Baghlan", "پروان": "Parwan", "پنجشیر": "Panjshir",
  "دایکندی": "Daykundi", "غور": "Ghor", "فاریاب": "Faryab", "جوزجان": "Jowzjan",
  "سمنگان": "Samangan", "سرپل": "Sar-e Pol", "بادغیس": "Badghis", "نیمروز": "Nimruz",
  "زابل": "Zabul", "پکتیا": "Paktia", "پکتیکا": "Paktika", "خوست": "Khost",
  "لغمان": "Laghman", "نورستان": "Nuristan", "کنر": "Kunar", "کاپیسا": "Kapisa",
  "میدان وردک": "Wardak", "لوگر": "Logar", "ارزگان": "Urozgan",
};

function CoinLogo({ coin }) {
  const [failed, setFailed] = useState(false);
  return failed
    ? <span className="map-coin-fallback">{coin.symbol}</span>
    : <img src={coin.logo} alt="" onError={() => setFailed(true)} />;
}

function walkCoordinates(node, visit) {
  if (!Array.isArray(node)) return;
  if (node.length >= 2 && typeof node[0] === "number" && typeof node[1] === "number") {
    visit(node[0], node[1]);
    return;
  }
  node.forEach((child) => walkCoordinates(child, visit));
}

function geometryPolygons(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Polygon") return [geometry.coordinates];
  if (geometry.type === "MultiPolygon") return geometry.coordinates;
  if (geometry.type === "GeometryCollection") {
    return (geometry.geometries || []).flatMap(geometryPolygons);
  }
  return [];
}

function buildProvincePaths(data) {
  const features = Array.isArray(data?.features) ? data.features : [];
  let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
  features.forEach((feature) => walkCoordinates(feature.geometry?.coordinates || feature.geometry?.geometries, (lon, lat) => {
    minLon = Math.min(minLon, lon); maxLon = Math.max(maxLon, lon);
    minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat);
  }));
  if (![minLon, maxLon, minLat, maxLat].every(Number.isFinite)) return {};

  const width = 1000, height = 666.6667;
  const project = ([lon, lat]) => [
    ((lon - minLon) / (maxLon - minLon)) * width,
    ((maxLat - lat) / (maxLat - minLat)) * height,
  ];

  const paths = {};
  features.forEach((feature) => {
    const title = feature?.properties?.title;
    if (!title) return;
    const parts = geometryPolygons(feature.geometry).flatMap((polygon) => polygon.map((ring) => {
      if (!Array.isArray(ring) || ring.length < 3) return "";
      const points = ring.map(project);
      return `M${points.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join("L")}Z`;
    })).filter(Boolean);
    if (parts.length) paths[title] = parts.join("");
  });
  return paths;
}

function ProvinceOverlay({ activeLocation }) {
  const [provincePaths, setProvincePaths] = useState({});

  useEffect(() => {
    let cancelled = false;
    fetch(PROVINCE_DATA_URL, { cache: "force-cache" })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("province data unavailable")))
      .then((data) => { if (!cancelled) setProvincePaths(buildProvincePaths(data)); })
      .catch(() => { if (!cancelled) setProvincePaths({}); });
    return () => { cancelled = true; };
  }, []);

  const sourceName = PROVINCE_NAME_MAP[activeLocation];
  const path = sourceName ? provincePaths[sourceName] : null;
  if (!path) return null;

  return (
    <svg className="province-boundary-overlay" viewBox="0 0 1000 666.6667" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <clipPath id="active-province-clip"><path d={path} /></clipPath>
      </defs>
      <image
        href={afghanistanMap}
        x="0" y="0" width="1000" height="666.6667"
        preserveAspectRatio="none"
        clipPath="url(#active-province-clip)"
        className="province-dot-image"
      />
      <path d={path} className="province-boundary-line" />
    </svg>
  );
}

export default function MarketMap({ activeLocation }) {
  const [snapshot, setSnapshot] = useState(null);
  const [hidden, setHidden] = useState(document.hidden);
  const [now, setNow] = useState(Date.now());
  const [sequence, setSequence] = useState(ACTIVE_SLOTS);
  const [activeMarkers, setActiveMarkers] = useState(() =>
    Array.from({ length: ACTIVE_SLOTS }, (_, i) => ({ markerIndex: i, instance: i }))
  );

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
      window.clearInterval(timer); window.clearInterval(clock);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  useEffect(() => {
    if (hidden) return undefined;
    const timer = window.setInterval(() => {
      setSequence((current) => {
        const next = current + 1;
        setActiveMarkers((items) => [
          ...items.slice(-(ACTIVE_SLOTS - 1)),
          { markerIndex: current % MARKERS.length, instance: next },
        ]);
        return next;
      });
    }, SLOT_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [hidden]);

  const rendered = useMemo(() => activeMarkers.map((item) => ({ ...item, marker: MARKERS[item.markerIndex] })), [activeMarkers]);

  return (
    <figure className={"market-map " + (hidden ? "is-paused" : "")} aria-label="نمای زندهٔ رمزارزها روی نقشهٔ افغانستان">
      <div className="map-stage" style={{ "--map-image": `url("${afghanistanMap}")` }}>
        <div className="afghanistan-dots" role="img" aria-label="نقشهٔ نقطه‌یی افغانستان" />
        <ProvinceOverlay activeLocation={activeLocation} />
        <div className="map-market-flow" aria-hidden="true">
          {rendered.map(({ marker, instance }) => {
            const coin = COINS[marker.coin];
            const change = marketChange(snapshot, coin.symbol, now);
            const rounded = change === null ? null : Number(change.toFixed(2));
            const sign = rounded === null ? null : rounded > 0 ? "+" : rounded < 0 ? "−" : "";
            const value = rounded === null ? null : Math.abs(rounded).toFixed(2);
            return (
              <div
                className="map-floater"
                key={instance}
                style={{ left: `${marker.x}%`, top: `${marker.y}%`, "--float-scale": marker.scale, "--coin-accent": coin.accent }}
              >
                <div className="map-token">
                  {value !== null && (
                    <span className="map-change num">
                      <span className="map-change-sign">{sign}</span>
                      <span className="map-change-value">{value}</span>
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
