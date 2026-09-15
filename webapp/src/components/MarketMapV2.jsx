import { useEffect, useState } from "react";
import afghanistanMap from "../assets/afghanistan-map.webp";

const PROVINCE_DATA_URL = "https://raw.githubusercontent.com/periodo/periodo-places/1563735c333174952541241c7c9640b346387533/gazetteers/afghan-provinces.json";
const MAP_WIDTH = 600;
const MAP_HEIGHT = 473;
const MAP_BOUNDS = { left: 33, top: 35, right: 567, bottom: 438 };

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

function MapLoader() {
  return (
    <div className="map-loader-shell" role="status" aria-label="در حال بارگذاری نقشه">
      <div className="map-crystal-loader" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => <span className="map-loader-crystal" key={index} />)}
      </div>
    </div>
  );
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
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
      });
    });
  });

  if (![minLon, maxLon, minLat, maxLat].every(Number.isFinite) || maxLon === minLon || maxLat === minLat) return {};

  const usableWidth = MAP_BOUNDS.right - MAP_BOUNDS.left;
  const usableHeight = MAP_BOUNDS.bottom - MAP_BOUNDS.top;
  const project = ([lon, lat]) => [
    MAP_BOUNDS.left + ((lon - minLon) / (maxLon - minLon)) * usableWidth,
    MAP_BOUNDS.top + ((maxLat - lat) / (maxLat - minLat)) * usableHeight,
  ];

  const paths = {};
  features.forEach((feature) => {
    const title = feature?.properties?.title;
    if (!title) return;
    const parts = geometryPolygons(feature.geometry)
      .flatMap((polygon) => polygon.map((ring) => {
        if (!Array.isArray(ring) || ring.length < 3) return "";
        const points = ring.map(project);
        return `M${points.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join("L")}Z`;
      }))
      .filter(Boolean);
    if (parts.length) paths[title] = parts.join("");
  });
  return paths;
}

function ProvinceOverlay({ activeLocation, provincePaths }) {
  const aliases = PROVINCE_NAME_MAP[activeLocation] || [];
  const sourceName = aliases.find((name) => provincePaths[name]);
  const path = sourceName ? provincePaths[sourceName] : null;
  if (!path) return null;

  return (
    <svg
      className="province-boundary-overlay province-boundary-overlay-static"
      viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <clipPath id="active-province-clip-static"><path d={path} /></clipPath>
        <filter id="province-highlight-blue" colorInterpolationFilters="sRGB">
          <feColorMatrix
            type="matrix"
            values="0 0 0 0 0  0 0 0 0 0.298  0 0 0 0 1  0 0 0 1 0"
          />
        </filter>
      </defs>
      <image
        href={afghanistanMap}
        x="0"
        y="0"
        width={MAP_WIDTH}
        height={MAP_HEIGHT}
        preserveAspectRatio="none"
        clipPath="url(#active-province-clip-static)"
        filter="url(#province-highlight-blue)"
        className="province-highlight-image-static"
      />
    </svg>
  );
}

export default function MarketMap({ activeLocation }) {
  const [mapReady, setMapReady] = useState(false);
  const [provincePaths, setProvincePaths] = useState({});

  useEffect(() => {
    let cancelled = false;
    const image = new Image();

    const revealMap = async () => {
      try {
        if (typeof image.decode === "function") await image.decode();
      } catch (_) {
        // onload is sufficient for older Telegram WebViews.
      }
      if (!cancelled) setMapReady(true);
    };

    image.onload = revealMap;
    image.onerror = () => { if (!cancelled) setMapReady(true); };
    image.src = afghanistanMap;
    if (image.complete && image.naturalWidth > 0) revealMap();

    return () => {
      cancelled = true;
      image.onload = null;
      image.onerror = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch(PROVINCE_DATA_URL, { cache: "force-cache" })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("province data unavailable")))
      .then((data) => { if (!cancelled) setProvincePaths(buildProvincePaths(data)); })
      .catch(() => { if (!cancelled) setProvincePaths({}); });
    return () => { cancelled = true; };
  }, []);

  return (
    <figure className="market-map market-map-static" aria-label="نقشهٔ افغانستان">
      <div
        className={`map-stage map-stage-new ${mapReady ? "is-ready" : "is-loading"}`}
        style={{ "--map-image": `url("${afghanistanMap}")` }}
      >
        {!mapReady && <MapLoader />}
        <div className="map-visual-content map-visual-content-new" aria-hidden={!mapReady}>
          <div className="afghanistan-map-new" role="img" aria-label="نقشهٔ نقطه‌یی افغانستان" />
          <ProvinceOverlay activeLocation={activeLocation} provincePaths={provincePaths} />
        </div>
      </div>
    </figure>
  );
}
