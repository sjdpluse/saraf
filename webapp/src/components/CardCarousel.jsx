import { useEffect, useMemo, useState } from "react";
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

function wrappedDistance(activeIndex, cardIndex, count) {
  if (!count) return 0;
  const half = count / 2;
  return ((((activeIndex - cardIndex + half) % count) + count) % count) - half;
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

function slotStyle(distance) {
  if (distance <= -2) {
    return {
      "--card-left": "-34%",
      "--card-y": "6px",
      "--card-rotate": "16deg",
      "--card-scale": ".88",
      "--card-opacity": "0",
      "--card-blur": "7px",
      "--card-z": "1",
    };
  }

  if (distance === -1) {
    return {
      "--card-left": "0%",
      "--card-y": "3px",
      "--card-rotate": "10deg",
      "--card-scale": ".93",
      "--card-opacity": ".62",
      "--card-blur": "3px",
      "--card-z": "2",
    };
  }

  if (distance === 0) {
    return {
      "--card-left": "50%",
      "--card-y": "0px",
      "--card-rotate": "0deg",
      "--card-scale": "1",
      "--card-opacity": "1",
      "--card-blur": "0px",
      "--card-z": "4",
    };
  }

  if (distance === 1) {
    return {
      "--card-left": "100%",
      "--card-y": "3px",
      "--card-rotate": "-10deg",
      "--card-scale": ".93",
      "--card-opacity": ".62",
      "--card-blur": "3px",
      "--card-z": "2",
    };
  }

  return {
    "--card-left": "134%",
    "--card-y": "6px",
    "--card-rotate": "-16deg",
    "--card-scale": ".88",
    "--card-opacity": "0",
    "--card-blur": "7px",
    "--card-z": "1",
  };
}

export default function CardCarousel({ activeStep = 0 }) {
  const [assetsReady, setAssetsReady] = useState(false);
  const cards = useMemo(() => sourceCards, []);

  useEffect(() => {
    let cancelled = false;
    setAssetsReady(false);

    if (!cards.length) {
      setAssetsReady(true);
      return () => { cancelled = true; };
    }

    Promise.all(cards.map((card) => preloadImage(card.src))).then(() => {
      if (!cancelled) setAssetsReady(true);
    });

    return () => { cancelled = true; };
  }, [cards]);

  if (!cards.length) return null;

  const activeIndex = ((activeStep % cards.length) + cards.length) % cards.length;

  return (
    <div
      className={`saraf-card-carousel ${assetsReady ? "is-ready" : "is-loading"}`}
      aria-label="کارت‌های صراف"
    >
      {!assetsReady && <CardLoader />}
      <div className="saraf-card-carousel__stage" aria-hidden={!assetsReady}>
        {cards.map((card, index) => {
          const distance = wrappedDistance(activeIndex, index, cards.length);
          const visible = Math.abs(distance) <= 1;

          return (
            <div
              className={`saraf-card-carousel__card${visible ? " is-visible" : ""}`}
              key={card.path}
              style={slotStyle(distance)}
              aria-hidden="true"
            >
              <img src={card.src} alt="" draggable="false" loading="eager" />
            </div>
          );
        })}
      </div>
    </div>
  );
}
