import { CheckCircle } from "@phosphor-icons/react";
import { ASSET_NAMES_FA, assetLogo, normalizeAsset } from "../lib/brand";

export default function AssetSelector({ value = "USDT", onChange }) {
  return (
    <fieldset className="asset-selector">
      <legend>انتخاب رمزارز</legend>
      <div className="asset-selector-options">
        {["USDT", "USDC"].map((asset) => <button key={asset} type="button" className={"asset-choice " + (normalizeAsset(value) === asset ? "selected" : "")} aria-pressed={normalizeAsset(value) === asset} onClick={() => onChange?.(asset)}>
          <img src={assetLogo(asset)} alt="" />
          <span><strong className="num">{asset}</strong><small>{ASSET_NAMES_FA[asset]}</small></span>
          {normalizeAsset(value) === asset && <CheckCircle size={18} weight="fill" />}
        </button>)}
      </div>
    </fieldset>
  );
}
