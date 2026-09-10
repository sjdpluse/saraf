import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { marketChange } from "../lib/market";
import { TETHER_LOGO_URL, USDC_LOGO_URL } from "../lib/brand";
import afghanistanMap from "../assets/afghanistan-dots.webp";

const ICON_BASE = "https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color";
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

const PROVINCE_POINTS = {
  "کابل": [61, 44], "بامیان": [50, 44], "مزار شریف": [42, 26], "بلخ": [42, 26],
  "هرات": [15, 49], "کندهار": [38, 75], "ننگرهار": [69, 46], "کندز": [58, 25],
  "بدخشان": [69, 18], "غزنی": [56, 57], "هلمند": [28, 73], "فراه": [17, 64],
  "تخار": [61, 19], "بغلان": [55, 31], "پروان": [58, 39], "پنجشیر": [61, 34],
  "دایکندی": [43, 56], "غور": [32, 50], "فاریاب": [33, 26], "جوزجان": [38, 23],
  "سمنگان": [47, 28], "سرپل": [39, 33], "بادغیس": [22, 37], "نیمروز": [17, 80],
  "زابل": [47, 70], "پکتیا": [62, 61], "پکتیکا": [58, 68], "خوست": [67, 61],
  "لغمان": [65, 42], "نورستان": [68, 34], "کنر": [72, 39], "کاپیسا": [61, 38],
  "میدان وردک": [57, 49], "لوگر": [61, 52], "ارزگان": [44, 64],
};

const PROVINCE_NAME_MAP = {
  "کابل": ["Kabul"], "بامیان": ["Bamyan", "Bamiyan"], "مزار شریف": ["Balkh"], "بلخ": ["Balkh"],
  "هرات": ["Herat", "Hirat"], "کندهار": ["Kandahar"], "ننگرهار": ["Nangarhar"], "کندز": ["Kunduz"],
  "بدخشان": ["Badakhshan"], "غزنی": ["Ghazni"], "هلمند": ["Helmand", "Hilmand"], "فراه": ["Farah"],
  "تخار": ["Takhar"], "بغلان": ["Baghlan"], "پروان": ["Parwan", "Parvan"], "پنجشیر": ["Panjshir", "Panjshīr"],
  "دایکندی": ["Daykundi", "Daykundi Province", "Daikundi"], "غور": ["Ghor"], "فاریاب": ["Faryab"], "جوزجان": ["Jowzjan", "Jawzjan"],
  "سمنگان": ["Samangan"], "سرپل": ["Sar-e Pol", "Sar-e Pul", "Sari Pul"], "بادغیس": ["Badghis"], "نیمروز": ["Nimruz", "Nimroz"],
  "زابل": ["Zabul"], "پکتیا": ["Paktia", "Paktya"], "پکتیکا": ["Paktika"], "خوست": ["Khost"],
  "لغمان": ["Laghman"], "نورستان": ["Nuristan"], "کنر": ["Kunar"], "کاپیسا": ["Kapisa"],
  "میدان وردک": ["Wardak", "Maidan Wardak"], "لوگر": ["Logar"], "ارزگان": ["Urozgan", "Uruzgan", "Oruzgan"],
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
  if (geometry.type === "GeometryCollection") return (geometry.geometries || []).flatMap(geometryPolygons);
  return [];
}

function buildProvincePaths(data) {
  const features = Array.isArray(data?.features) ? data.features : [];
  let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;

  features.forEach((feature) => {
    geometryPolygons(feature.geometry).forEach((polygon) => {
      walkCoordinates(polygon, (lon, lat) => {
        minLon = Math.min(minLon, lon); maxLon = Math.max(maxLon, lon);
        minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat);
      });
    });
  });

  if (![minLon, maxLon, minLat, maxLat].every(Number.isFinite) || maxLon === minLon || maxLat === minLat) return {};

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

  const aliases = PROVINCE_NAME_MAP[activeLocation] || [];
  const sourceName = aliases.find((name) => provincePaths[name]);
  const path = sourceName ? provincePaths[sourceName] : null;
  if (!path) return null;

  return (
    <svg className="province-boundary-overlay" viewBox="0 0 1000 666.6667" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <clipPath id="active-province-clip"><path d={path} /></clipPath>
        <filter id="province-blue-filter" colorInterpolationFilters="sRGB">
          <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0.4  0 0 0 0 0.8  0 0 0 1 0" />
        </filter>
      </defs>
      <image
        href={afghanistanMap}
        x="0" y="0" width="1000" height="666.6667"
        preserveAspectRatio="none"
        clipPath="url(#active-province-clip)"
        filter="url(#province-blue-filter)"
        className="province-dot-image"
      />
    </svg>
  );
}

export default function MarketMap({ activeLocation, activeDuration = 1700 }) {
  const [snapshot, setSnapshot] = useState(null);
  const [hidden, setHidden] = useState(document.hidden);
  const [now, setNow] = useState(Date.now());
  const [coinIndex, setCoinIndex] = useState(() => Math.floor(Math.random() * COINS.length));

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
    setCoinIndex((current) => {
      if (COINS.length < 2) return 0;
      let next = current;
      while (next === current) next = Math.floor(Math.random() * COINS.length);
      return next;
    });
  }, [activeLocation]);

  const point = PROVINCE_POINTS[activeLocation] || PROVINCE_POINTS["کابل"];
  const coin = COINS[coinIndex];
  const change = marketChange(snapshot, coin.symbol, now);
  const rounded = change === null ? null : Number(change.toFixed(2));
  const sign = rounded === null ? "" : rounded > 0 ? "+" : rounded < 0 ? "−" : "";
  const value = rounded === null ? null : Math.abs(rounded).toFixed(2);
  const markerKey = `${activeLocation}-${coin.symbol}`;

  return (
    <figure className={"market-map " + (hidden ? "is-paused" : "")} aria-label="نمای زندهٔ رمزارزها روی نقشهٔ افغانستان">
      <div className="map-stage" style={{ "--map-image": `url("${afghanistanMap}")` }}>
        <div className="afghanistan-dots" role="img" aria-label="نقشهٔ نقطه‌یی افغانستان" />
        <ProvinceOverlay activeLocation={activeLocation} />
        <div className="map-market-flow" aria-hidden="true">
          <div
            className="map-floater"
            key={markerKey}
            style={{
              left: `${point[0]}%`,
              top: `${point[1]}%`,
              "--float-scale": .96,
              "--coin-accent": coin.accent,
              "--coin-duration": `${activeDuration}ms`,
            }}
          >
            <div className="map-token">
              <span className={`map-change num ${value === null ? "is-waiting" : ""}`}>
                <span className="map-change-sign">{sign}</span>
                <span className="map-change-value">{value ?? "··"}</span>
              </span>
              <span className="map-coin-shell"><span className="map-coin"><CoinLogo coin={coin} /></span></span>
            </div>
          </div>
        </div>
      </div>
    </figure>
  );
}
