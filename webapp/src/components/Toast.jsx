import { useEffect, useMemo } from "react";
import { WarningCircle } from "@phosphor-icons/react";

export default function Toast({ message, onClose }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = window.setTimeout(() => onClose?.(), 3400);
    return () => window.clearTimeout(timer);
  }, [message, onClose]);

  const placement = useMemo(() => {
    if (!message || typeof window === "undefined") return null;
    const anchor = window.__sarafLastActionAnchor;
    const recent = anchor && Date.now() - anchor.at < 1800;
    if (!recent) return { className: "toast-centered", style: {} };

    const preferredLeft = anchor.left + anchor.width / 2;
    const minLeft = 16 + Math.min(390, window.innerWidth - 32) / 2;
    const maxLeft = window.innerWidth - minLeft;
    const left = Math.min(maxLeft, Math.max(minLeft, preferredLeft));
    let top = anchor.bottom + 10;
    if (top + 90 > window.innerHeight) top = Math.max(16, anchor.top - 76);

    return {
      className: "toast-anchored",
      style: { left: `${left}px`, top: `${top}px` },
    };
  }, [message]);

  if (!message) return null;

  return (
    <div
      className={`toast saraf-toast ${placement?.className || "toast-centered"}`}
      style={placement?.style}
      role="alert"
      aria-live="assertive"
    >
      <WarningCircle size={19} weight="fill" />
      <span>{message}</span>
    </div>
  );
}
