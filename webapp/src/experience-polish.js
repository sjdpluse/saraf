const EXCHANGE_LOGOS = {
  Binance: "https://cdn.simpleicons.org/binance/F3BA2F",
  Bybit: "https://logo.svgcdn.com/token-branded/bybit.svg",
  OKX: "https://cdn.simpleicons.org/okx/111111",
  KuCoin: "https://cdn.simpleicons.org/kucoin/24AE8F",
  JustMarkets: "https://i.postimg.cc/cJKXwgXS/ODF.png",
};

const EXACT_GRADIENT_LAYERS = [
  ["0s", "25s"],
  ["0.15s", "15.9s"],
  ["0.53s", "26.4s"],
  ["0.45s", "17.8s"],
  ["1.6s", "19.2s"],
  ["1.6s", "29.2s"],
  ["1.6s", "20.2s"],
];

function rememberLastAction(event) {
  const button = event.target?.closest?.("button, .exact-flow-wrapper");
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

function buttonShouldUseExactGradient(button) {
  if (!button?.matches?.(".card .btn.btn-buy, .card .btn.btn-sell, .card .btn.btn-primary")) return false;
  const text = button.textContent.replace(/\s+/g, " ").trim();
  if (!text) return false;
  return /^(ادامه|محاسبه|بررسی|ثبت|شروع|تایید|تکمیل|ارسال)/.test(text);
}

function syncExactGradientButton(source, wrapper) {
  if (!source || !wrapper) return;
  const proxy = wrapper.querySelector(".gradient-btn");
  const overlay = wrapper.querySelector(".text-overlay");
  if (!proxy || !overlay) return;

  const html = source.innerHTML;
  if (proxy.dataset.sourceHtml !== html) {
    proxy.innerHTML = html;
    overlay.innerHTML = html;
    proxy.dataset.sourceHtml = html;
  }

  const disabled = Boolean(source.disabled);
  proxy.disabled = disabled;
  wrapper.classList.toggle("is-disabled", disabled);
  wrapper.classList.toggle("exact-flow-buy", source.classList.contains("btn-buy"));
  wrapper.classList.toggle("exact-flow-sell", source.classList.contains("btn-sell"));
  wrapper.classList.toggle("exact-flow-primary", source.classList.contains("btn-primary"));
}

function buildExactGradientButton(source) {
  if (!source || source.__sarafExactWrapper?.isConnected) {
    syncExactGradientButton(source, source.__sarafExactWrapper);
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "btn-wrapper exact-flow-wrapper";
  wrapper.__sarafSource = source;

  const light = document.createElement("div");
  light.className = "light";
  light.setAttribute("aria-hidden", "true");
  wrapper.appendChild(light);

  EXACT_GRADIENT_LAYERS.forEach(([delay, duration]) => {
    const layer = document.createElement("div");
    layer.className = "gradient-layer";
    layer.style.animationDelay = delay;
    layer.style.animationDuration = duration;
    layer.setAttribute("aria-hidden", "true");
    wrapper.appendChild(layer);
  });

  const proxy = document.createElement("button");
  proxy.type = "button";
  proxy.className = "gradient-btn";
  proxy.addEventListener("click", () => {
    if (!source.isConnected || source.disabled) return;
    source.click();
  });
  wrapper.appendChild(proxy);

  const overlay = document.createElement("div");
  overlay.className = "text-overlay";
  overlay.setAttribute("aria-hidden", "true");
  wrapper.appendChild(overlay);

  source.classList.add("flow-stage-source");
  source.__sarafExactWrapper = wrapper;
  source.insertAdjacentElement("afterend", wrapper);
  syncExactGradientButton(source, wrapper);
}

function enhanceStageButtons(root = document) {
  root.querySelectorAll?.(".card .btn.btn-buy, .card .btn.btn-sell, .card .btn.btn-primary").forEach((button) => {
    if (!buttonShouldUseExactGradient(button)) return;
    button.classList.remove("flow-stage-btn");
    buildExactGradientButton(button);
  });

  document.querySelectorAll?.(".exact-flow-wrapper").forEach((wrapper) => {
    const source = wrapper.__sarafSource;
    if (!source?.isConnected) {
      wrapper.remove();
      return;
    }
    syncExactGradientButton(source, wrapper);
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
    let enhancing = false;
    const observer = new MutationObserver(() => {
      if (enhancing) return;
      enhancing = true;
      requestAnimationFrame(() => {
        enhance(document);
        enhancing = false;
      });
    });
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["disabled", "class"],
    });
  }
}
