import { useEffect, useMemo, useRef } from "react";
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

const CARD_MS = 1850;
const MAX_VISIBLE_DISTANCE = 2.45;

function buildLoop(cards) {
  if (!cards.length) return [];
  if (cards.length >= 5) return cards;

  const loop = [];
  while (loop.length < 6) {
    cards.forEach((card) => {
      if (loop.length < 6) loop.push(card);
    });
  }
  return loop;
}

function wrappedDistance(value, count) {
  const half = count / 2;
  return ((((value + half) % count) + count) % count) - half;
}

export default function CardCarousel() {
  const rootRef = useRef(null);
  const phaseRef = useRef(0);
  const frameRef = useRef(0);
  const lastFrameRef = useRef(null);

  const cards = useMemo(() => buildLoop(sourceCards), []);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || !cards.length) return undefined;

    const cardNodes = Array.from(root.querySelectorAll(".saraf-card-carousel__card"));
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)");

    const paint = (now) => {
      const width = root.clientWidth || window.innerWidth || 390;
      const cardWidth = Math.min(292, Math.max(214, width * 0.61));
      const gap = Math.min(34, Math.max(20, width * 0.055));
      const step = cardWidth + gap;

      root.style.setProperty("--carousel-card-width", `${cardWidth}px`);

      if (lastFrameRef.current == null) lastFrameRef.current = now;
      const elapsed = Math.min(64, Math.max(0, now - lastFrameRef.current));
      lastFrameRef.current = now;

      if (!document.hidden && !reducedMotion?.matches && cards.length > 1) {
        phaseRef.current = (phaseRef.current + elapsed / CARD_MS) % cards.length;
      }

      cardNodes.forEach((node, index) => {
        const position = wrappedDistance(index - phaseRef.current, cards.length);
        const distance = Math.abs(position);
        const visible = distance <= MAX_VISIBLE_DISTANCE;
        const x = position * step;
        const rotateY = Math.max(-12, Math.min(12, -position * 6.8));
        const z = -distance * 52;
        const scale = Math.max(0.91, 1 - distance * 0.027);
        const opacity = visible ? Math.max(0.2, 1 - Math.max(0, distance - 1.75) * 0.7) : 0;

        node.style.setProperty("--card-x", `${x}px`);
        node.style.setProperty("--card-rotate-y", `${rotateY}deg`);
        node.style.setProperty("--card-z", `${z}px`);
        node.style.setProperty("--card-scale", scale.toFixed(4));
        node.style.opacity = opacity.toFixed(3);
        node.style.zIndex = String(Math.max(1, 100 - Math.round(distance * 20)));
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
    };
  }, [cards]);

  if (!cards.length) return null;

  return (
    <section
      ref={rootRef}
      className="saraf-card-carousel"
      aria-label="کارت‌های صراف"
    >
      <div className="saraf-card-carousel__stage">
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
    </section>
  );
}
