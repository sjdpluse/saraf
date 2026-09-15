const EXCHANGE_LOGOS = {
  Binance: "https://cdn.simpleicons.org/binance/F3BA2F",
  Bybit: "https://i.postimg.cc/26yGrqLK/ODF-(1).png",
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

function setReactInputValue(input, value) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  if (setter) setter.call(input, value);
  else input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function chooseInjectedSellBroker(button) {
  const card = button.closest(".card");
  if (!card) return;

  const otherButton = Array.from(card.querySelectorAll(".choice-btn")).find((item) =>
    /صرافی\s*\/\s*کیف پول دیگر|کیف پول شخصی|صرافی دیگر/.test(item.textContent.trim())
  );
  if (!otherButton) return;

  otherButton.click();
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      const input = card.querySelector('input[placeholder="نام صرافی یا کیف پول"]');
      if (!input) return;
      setReactInputValue(input, "JustMarkets");
      setTimeout(() => {
        const continueButton = Array.from(card.querySelectorAll(".btn.btn-sell")).find((item) =>
          item.textContent.replace(/\s+/g, " ").trim().startsWith("ادامه")
        );
        continueButton?.click();
      }, 0);
    });
  });
}

function ensureSellJustMarkets(row, buttons) {
  const card = row.closest(".card");
  const label = card?.querySelector(".field-label")?.textContent || "";
  const isSellExchangeStep = label.includes("از کدام صرافی") || label.includes("ارسال می‌کنید");
  if (!isSellExchangeStep) return buttons;
  if (buttons.some((button) => button.textContent.trim() === "JustMarkets")) return buttons;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "choice-btn";
  button.textContent = "JustMarkets";
  button.dataset.injectedBroker = "1";
  button.addEventListener("click", () => chooseInjectedSellBroker(button));
  row.appendChild(button);
  return [...buttons, button];
}

function enhanceExchangeChoices(root = document) {
  root.querySelectorAll?.(".choice-row").forEach((row) => {
    let buttons = Array.from(row.querySelectorAll(":scope > .choice-btn"));
    const hasKnownExchange = buttons.some((button) => EXCHANGE_LOGOS[button.textContent.trim()]);
    const card = row.closest(".card");
    const label = card?.querySelector(".field-label")?.textContent || "";
    const looksLikeExchangeStep = hasKnownExchange || label.includes("صرافی یا کیف پول");
    if (!looksLikeExchangeStep) return;

    buttons = ensureSellJustMarkets(row, buttons);
    row.classList.add("exchange-choice-row");

    buttons.forEach((button) => {
      const labelText = button.textContent.trim();
      const logo = EXCHANGE_LOGOS[labelText];
      if (!logo) return;
      button.classList.add("exchange-option");
      button.style.setProperty("--exchange-logo", `url("${logo}")`);
      if (labelText === "JustMarkets") button.classList.add("broker-option");
    });
  });
}

function buttonShouldUseExactGradient(button) {
  if (!button?.matches?.(".card .btn.btn-buy, .card .btn.btn-sell, .card .btn.btn-primary")) return false;
  const text = button.textContent.replace(/\s+/g, " ").trim();
  if (!text) return false;
  return /^(ادامه|محاسبه|بررسی|ثبت|شروع|تایید|تکمیل|ارسال)/.test(text);
}

function syncAmountVisibility(source, wrapper) {
  const text = source.textContent.replace(/\s+/g, " ").trim();
  const isCalculate = text.startsWith("محاسبه");
  wrapper.classList.toggle("amount-reveal-button", isCalculate);
  if (!isCalculate) {
    wrapper.classList.remove("is-amount-hidden", "is-amount-visible");
    return;
  }

  const card = source.closest(".card");
  const amountInput = card?.querySelector('input[type="number"]');
  const hasAmount = Boolean(amountInput?.value?.trim());
  wrapper.classList.toggle("is-amount-hidden", !hasAmount);
  wrapper.classList.toggle("is-amount-visible", hasAmount);
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
  syncAmountVisibility(source, wrapper);
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
  document.addEventListener("input", (event) => {
    if (event.target?.matches?.('input[type="number"]')) {
      requestAnimationFrame(() => enhanceStageButtons(document));
    }
  }, true);
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
