import { useEffect, useMemo, useRef, useState } from "react";
import "./CardCarousel.css";

const rootCards = import.meta.glob("../assets/card-*.{png,jpg,jpeg,webp,avif,svg}", {
  eager: true,
  import: "default",
});

const folderCards = import.meta.glob("../assets/cards/*.{png,jpg,jpeg,webp,avif,svg}", {
  eager: true,
  import: "default",
});

const sourceCards = Object.entries({ ...rootCards, ...folderCards })
  .sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }))
  .map(([path, src]) => ({ path, src }));

const SLOT_MS = 1880;
const ANGLE_STEP = 36;
const MAX_VISIBLE_ANGLE = 96;

function buildLoop(cards) {
  if (!cards.length) return [];
  if (cards.length >= 8) return cards;

  const loop = [];
  while (loop.length < 8) {
    cards.forEach((card) => {
      if (loop.length < 8) loop.push(card);
    });
  }
  return loop;
}

function wrappedDistance(value, count) {
  const half = count / 2;
  return ((((value + half) % count) + count) % count) - half;
}

function CardLoader() {
  return (
    <div className="map-loader-shell saraf-card-carousel__loader" role="status" aria-label="در حال بارگذاری کارت‌ها">
      <div className="map-crystal-loader" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => <span className="map-loader-crystal" key={index} />)}
      </div>
    </div>
  );
}

function preloadImage(src) {
  return new Promise((resolve) => {
    const image = new Image();
    let settled = false;

    const finish = async () => {
      if (settled) return;
      settled = true;
      try {
        if (typeof image.decode === "function") await image.decode();
      } catch (_) {
        // onload is enough for older Telegram WebViews.
      }
      resolve();
    };

    image.onload = finish;
    image.onerror = finish;
    image.src = src;
    if (image.complete && image.naturalWidth > 0) finish();
  });
}

export default function CardCarousel() {
  const rootRef = useRef(null);
  const phaseRef = useRef(0);
  const frameRef = useRef(0);
  const lastFrameRef = useRef(null);
  const [assetsReady, setAssetsReady] = useState(false);

  const cards = useMemo(() => buildLoop(sourceCards), []);

  useEffect(() => {
    let cancelled = false;
    setAssetsReady(false);

    if (!sourceCards.length) {
      setAssetsReady(true);
      return () => { cancelled = true; };
    }

    Promise.all(sourceCards.map((card) => preloadImage(card.src))).then(() => {
      if (!cancelled) setAssetsReady(true);
    });

    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !cards.length || !assetsReady) return undefined;

    const cardNodes = Array.from(root.querySelectorAll(".saraf-card-carousel__card"));
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)");

    const paint = (now) => {
      const width = root.clientWidth || window.innerWidth || 390;
      const cardWidth = Math.min(164, Math.max(126, width * 0.38));
      const radius = Math.min(300, Math.max(190, width * 0.6));

      root.style.setProperty("--carousel-card-width", `${cardWidth}px`);

      if (lastFrameRef.current == null) lastFrameRef.current = now;
      const elapsed = Math.min(64, Math.max(0, now - lastFrameRef.current));
      lastFrameRef.current = now;

      if (!document.hidden && !reducedMotion?.matches && cards.length > 1) {
        phaseRef.current = (phaseRef.current + elapsed / SLOT_MS) % cards.length;
      }

      cardNodes.forEach((node, index) => {
        const position = wrappedDistance(index - phaseRef.current, cards.length);
        const angle = position * ANGLE_STEP;
        const radians = angle * Math.PI / 180;
        const absAngle = Math.abs(angle);
        const visible = absAngle <= MAX_VISIBLE_ANGLE;

        const x = Math.sin(radians) * radius;
        const z = (Math.cos(radians) - 1) * radius;
        const rotateY = -angle;
        const scale = 1 - Math.min(0.045, Math.abs(position) * 0.012);
        const opacity = !visible ? 0 : absAngle > 82 ? Math.max(0, (MAX_VISIBLE_ANGLE - absAngle) / 14) : 1;
        const depth = Math.cos(radians);

        node.style.setProperty("--card-x", `${x.toFixed(2)}px`);
        node.style.setProperty("--card-z", `${z.toFixed(2)}px`);
        node.style.setProperty("--card-rotate-y", `${rotateY.toFixed(2)}deg`);
        node.style.setProperty("--card-scale", scale.toFixed(4));
        node.style.opacity = opacity.toFixed(3);
        node.style.zIndex = String(Math.round(1000 + depth * 100));
        node.style.visibility = visible ? "visible" : "hidden";
      });

      frameRef.current = window.requestAnimationFrame(paint);
    };

    const handleVisibility = () => {
      lastFrameRef.current = null;
    };

    document.addEventListener("visibilitychange", handleVisibility);
    reducedMotion?.addEventListener?.("change", handleVisibility);
    frameRef.current = window.requestAnimationFrame(paint);

    return () => {
      window.cancelAnimationFrame(frameRef.current);
      document.removeEventListener("visibilitychange", handleVisibility);
      reducedMotion?.removeEventListener?.("change", handleVisibility);
      lastFrameRef.current = null;
    };
  }, [assetsReady, cards]);

  if (!cards.length) return null;

  return (
    <div
      ref={rootRef}
      className={`saraf-card-carousel ${assetsReady ? "is-ready" : "is-loading"}`}
      aria-label="کارت‌های صراف"
    >
      {!assetsReady && <CardLoader />}
      <div className="saraf-card-carousel__stage" aria-hidden={!assetsReady}>
        {cards.map((card, index) => (
          <div
            className="saraf-card-carousel__card"
            key={`${card.path}-${index}`}
            aria-hidden="true"
          >
            <img src={card.src} alt="" draggable="false" loading="eager" />
          </div>
        ))}
      </div>
    </div>
  );
}
