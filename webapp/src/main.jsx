import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import "./remittance.css";
import "./ui.css";
import "./brand-refresh.css";
import "./peyda-font.css";
import "./ux-effects.css";
import "./home-refine.css";
import "./footer-map-v3.css";
import "./experience-polish.css";
import "./experience-polish.js";

function normalizeSellAmountPlaceholder(root = document) {
  const candidates = [];
  if (root?.matches?.('input[placeholder="مثال: 100"]')) candidates.push(root);
  root?.querySelectorAll?.('input[placeholder="مثال: 100"]').forEach((input) => candidates.push(input));

  candidates.forEach((input) => {
    const field = input.closest(".field");
    const label = field?.querySelector(".field-label")?.textContent || "";
    if (label.includes("می‌خواهید بفروشید")) input.placeholder = "0.00";
  });
}

if (typeof MutationObserver !== "undefined") {
  normalizeSellAmountPlaceholder();
  const uiObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) normalizeSellAmountPlaceholder(node);
      });
    });
  });
  uiObserver.observe(document.documentElement, { childList: true, subtree: true });
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
