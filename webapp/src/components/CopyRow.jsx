import { useState } from "react";
import { Copy, Check } from "@phosphor-icons/react";

export default function CopyRow({ label, value }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (_) {
      /* در محیط‌های بدون دسترسی به clipboard API، بی‌صدا نادیده گرفته می‌شود */
    }
  }

  return (
    <div className="row">
      {label && <span className="label">{label}</span>}
      <span className="value">
        {value}
        <button type="button" className={`copy-btn ${copied ? "copied" : ""}`} onClick={handleCopy}>
          {copied ? <Check size={14} weight="bold" /> : <Copy size={14} />}
        </button>
      </span>
    </div>
  );
}
