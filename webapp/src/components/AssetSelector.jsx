import { CheckCircle } from "@phosphor-icons/react";
import { TETHER_LOGO_URL, USDC_LOGO_URL, normalizeAsset } from "../lib/brand";

const ITEMS = [
  {
    code: "USDT",
    name: "Tether",
    detail: "تتر",
    logo: TETHER_LOGO_URL,
  },
  {
    code: "USDC",
    name: "USD Coin",
    detail: "Circle",
    logo: USDC_LOGO_URL,
  },
];

export default function AssetSelector({ value = "USDT", onChange }) {
  const selected = normalizeAsset(value);
  return (
    <div className="card animate-in" style={{ padding: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 12 }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 14 }}>دارایی معامله</div>
          <div style={{ color: "var(--color-text-muted)", fontSize: 11.5, marginTop: 2 }}>
            کوین مورد نظر را انتخاب کنید
          </div>
        </div>
        <div className="num" style={{ fontSize: 11, fontWeight: 700, color: "var(--color-primary)", background: "var(--color-info-bg)", padding: "5px 9px", borderRadius: 999 }}>
          {selected}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {ITEMS.map((item) => {
          const active = selected === item.code;
          return (
            <button
              key={item.code}
              type="button"
              onClick={() => onChange?.(item.code)}
              aria-pressed={active}
              style={{
                position: "relative",
                minHeight: 82,
                borderRadius: 18,
                border: active ? "1.5px solid var(--color-primary)" : "1px solid var(--color-border-strong)",
                background: active ? "rgba(0,113,227,0.055)" : "#fff",
                boxShadow: active ? "0 8px 22px rgba(0,113,227,0.10)" : "none",
                padding: 12,
                fontFamily: "inherit",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 10,
                textAlign: "right",
                transition: "all .18s var(--ease-ios)",
              }}
            >
              <span style={{ width: 42, height: 42, borderRadius: 14, background: "#fff", display: "grid", placeItems: "center", flexShrink: 0, boxShadow: "0 2px 10px rgba(0,0,0,.06)" }}>
                <img src={item.logo} alt={item.code} style={{ width: 32, height: 32, objectFit: "contain", borderRadius: "50%" }} />
              </span>
              <span style={{ minWidth: 0, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                <span className="num" style={{ fontWeight: 800, fontSize: 15 }}>{item.code}</span>
                <span style={{ color: "var(--color-text-muted)", fontSize: 11.5 }}>{item.name}</span>
                <span style={{ color: "var(--color-text-faint)", fontSize: 10.5 }}>{item.detail}</span>
              </span>
              {active && (
                <CheckCircle
                  size={19}
                  weight="fill"
                  style={{ position: "absolute", top: 9, left: 9, color: "var(--color-primary)" }}
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
