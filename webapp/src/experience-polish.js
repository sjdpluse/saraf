const EXCHANGE_LOGOS = {
  Binance: "https://cdn.simpleicons.org/binance/F3BA2F",
  Bybit: "https://cdn.simpleicons.org/bybit/F7A600",
  OKX: "https://cdn.simpleicons.org/okx/111111",
  KuCoin: "https://cdn.simpleicons.org/kucoin/24AE8F",
  JustMarkets: "https://i.postimg.cc/cJKXwgXS/ODF.png",
};

function rememberLastAction(event) {
  const button = event.target?.closest?.("button");
  if (!button) return;
  const rect = button.getBoundingClientRect();
  window.__sarafLastActionAnchor = {
    left: rect.left,
    right: rect.right,
    top: rect.top,
    bottom: rect.bottom,
    width: rect.width,
    height: rect.height,
    at: Date.now(),
  };
}

function enhanceExchangeChoices(root = document) {
  root.querySelectorAll?.(".choice-row").forEach((row) => {
    const buttons = Array.from(row.querySelectorAll(":scope > .choice-btn"));
    const hasExchange = buttons.some((button) => EXCHANGE_LOGOS[button.textContent.trim()]);
    if (!hasExchange) return;

    row.classList.add("exchange-choice-row");
    buttons.forEach((button) => {
      const label = button.textContent.trim();
      const logo = EXCHANGE_LOGOS[label];
      if (!logo) return;
      button.classList.add("exchange-option");
      button.style.setProperty("--exchange-logo", `url("${logo}")`);
      if (label === "JustMarkets") button.classList.add("broker-option");
    });
  });
}

function enhanceStageButtons(root = document) {
  root.querySelectorAll?.(".card .btn.btn-buy, .card .btn.btn-sell, .card .btn.btn-primary").forEach((button) => {
    const text = button.textContent.replace(/\s+/g, " ").trim();
    if (!text) return;
    if (/^(ادامه|محاسبه|بررسی|ثبت|شروع|تایید|تکمیل|ارسال)/.test(text)) {
      button.classList.add("flow-stage-btn");
    }
  });
}

function animateNumberElement(element) {
  if (!element || element.dataset.countAnimated === "1" || element.children.length) return;
  const raw = element.textContent.trim();
  const match = raw.match(/^([^0-9-]*)(-?[\d,]+(?:\.\d+)?)([^0-9]*)$/);
  if (!match) return;

  const target = Number(match[2].replace(/,/g, ""));
  if (!Number.isFinite(target) || Math.abs(target) === 0) return;

  const decimals = (match[2].split(".")[1] || "").length;
  const prefix = match[1];
  const suffix = match[3];
  const formatter = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  element.dataset.countAnimated = "1";
  const duration = 720;
  const start = performance.now();
  const tick = (now) => {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 4);
    element.textContent = `${prefix}${formatter.format(target * eased)}${suffix}`;
    if (progress < 1) requestAnimationFrame(tick);
    else element.textContent = raw;
  };
  requestAnimationFrame(tick);
}

function enhanceQuoteNumbers(root = document) {
  root.querySelectorAll?.(".quote-box .value.num, .quote-total .amount.num").forEach(animateNumberElement);
}

function enhance(root = document) {
  enhanceExchangeChoices(root);
  enhanceStageButtons(root);
  enhanceQuoteNumbers(root);
}

if (typeof document !== "undefined") {
  document.addEventListener("pointerdown", rememberLastAction, true);
  enhance();

  if (typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) enhance(node);
        }
      }
      enhance(document);
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
}
