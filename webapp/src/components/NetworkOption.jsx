import { CheckCircle } from "@phosphor-icons/react";
import NetworkIcon from "./NetworkIcon";

const NETWORK_META = {
  TRC20: { short: "TRC20", full: "Tron (TRX)" },
  BEP20: { short: "BEP20", full: "BNB Smart Chain (BSC)" },
  ERC20: { short: "ERC20", full: "Ethereum (ETH)" },
  ARBITRUM: { short: "ARBITRUM", full: "Arbitrum (ARB)" },
  BASE: { short: "BASE", full: "Base (BASE)" },
  POLYGON: { short: "POLYGON", full: "Polygon (POL)" },
  SOLANA: { short: "SOL", full: "Solana (SOL)" },
  AVALANCHE: { short: "AVALANCHE", full: "Avalanche C-Chain (AVAX)" },
  OPTIMISM: { short: "OPTIMISM", full: "OP Mainnet (OP)" },
};

export function networkPresentation(item) {
  const code = String(item?.code || "").toUpperCase();
  return NETWORK_META[code] || {
    short: code || "NETWORK",
    full: item?.label || code || "Network",
  };
}

export default function NetworkOption({ item, selected = false, onClick }) {
  const meta = networkPresentation(item);
  return (
    <button
      type="button"
      className={`network-option ${selected ? "selected" : ""}`}
      onClick={onClick}
      aria-pressed={selected}
    >
      <NetworkIcon network={item.code} size={34} />
      <span className="network-option-copy">
        <span className="network-option-code num">{meta.short}</span>
        <span className="network-option-name">{meta.full}</span>
      </span>
      {selected && <CheckCircle className="network-option-check" size={20} weight="fill" />}
    </button>
  );
}
