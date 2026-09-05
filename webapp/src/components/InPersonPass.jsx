import { useMemo, useState } from "react";
import { CheckCircle, DownloadSimple, MapPin, Warning } from "@phosphor-icons/react";
import { SARAF_LOGO_URL, assetLogo, normalizeAsset } from "../lib/brand";

const ADDRESS = "کوته‌سنگی، همادی مارکیت، کابل، افغانستان";

function escapeXml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export default function InPersonPass({ action, asset, code, onContinue, buttonClass = "btn-primary" }) {
  const selectedAsset = normalizeAsset(asset);
  const [downloaded, setDownloaded] = useState(false);
  const actionFa = action === "buy" ? "پرداخت حضوری" : "دریافت حضوری";
  const coinLogo = assetLogo(selectedAsset);

  const svg = useMemo(() => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f7fbff"/><stop offset="1" stop-color="#eef5ff"/>
    </linearGradient>
    <filter id="s"><feDropShadow dx="0" dy="18" stdDeviation="22" flood-opacity="0.12"/></filter>
  </defs>
  <rect width="1200" height="760" fill="#f5f5f7"/>
  <rect x="70" y="65" width="1060" height="630" rx="46" fill="white" filter="url(#s)"/>
  <rect x="70" y="65" width="1060" height="170" rx="46" fill="url(#g)"/>
  <image href="${escapeXml(SARAF_LOGO_URL)}" x="115" y="105" width="78" height="78" preserveAspectRatio="xMidYMid slice"/>
  <text x="220" y="142" font-family="Arial, sans-serif" font-size="42" font-weight="800" fill="#1d1d1f">SARAF</text>
  <text x="220" y="180" font-family="Arial, sans-serif" font-size="22" fill="#6e6e73">In-person transaction pass</text>
  <image href="${escapeXml(coinLogo)}" x="995" y="108" width="72" height="72" preserveAspectRatio="xMidYMid meet"/>
  <text x="1030" y="205" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#1d1d1f">${selectedAsset}</text>
  <text x="600" y="318" text-anchor="middle" direction="rtl" unicode-bidi="plaintext" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#1d1d1f">${escapeXml(actionFa)}</text>
  <text x="600" y="390" text-anchor="middle" direction="rtl" unicode-bidi="plaintext" font-family="Arial, sans-serif" font-size="25" fill="#6e6e73">${escapeXml(ADDRESS)}</text>
  <rect x="395" y="445" width="410" height="130" rx="30" fill="#f2f7ff" stroke="#d6e6ff" stroke-width="2"/>
  <text x="600" y="486" text-anchor="middle" direction="rtl" unicode-bidi="plaintext" font-family="Arial, sans-serif" font-size="20" fill="#6e6e73">کد مراجعه</text>
  <text x="600" y="550" text-anchor="middle" font-family="Arial, sans-serif" font-size="58" font-weight="900" letter-spacing="10" fill="#0071e3">${escapeXml(code)}</text>
  <text x="600" y="638" text-anchor="middle" direction="rtl" unicode-bidi="plaintext" font-family="Arial, sans-serif" font-size="19" fill="#86868b">این کارت را هنگام مراجعه به صراف نشان دهید</text>
</svg>`, [actionFa, code, coinLogo, selectedAsset]);

  function download() {
    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `saraf-${selectedAsset}-${action}-${code}.svg`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setDownloaded(true);
  }

  return (
    <div className="inperson-pass-wrap animate-in">
      <div className="inperson-pass">
        <div className="inperson-pass-head">
          <div className="inperson-brand-lockup">
            <img src={SARAF_LOGO_URL} alt="Saraf" />
            <div><b>صراف</b><span>کارت مراجعهٔ حضوری</span></div>
          </div>
          <div className="inperson-asset-lockup">
            <img src={coinLogo} alt={selectedAsset} />
            <b className="num">{selectedAsset}</b>
          </div>
        </div>
        <div className="inperson-action">{actionFa}</div>
        <div className="inperson-address"><MapPin size={18} weight="fill" /><span>{ADDRESS}</span></div>
        <div className="inperson-code"><span>کد مراجعه</span><strong className="num">{code}</strong></div>
      </div>
      <button className="btn btn-secondary" onClick={download}>
        {downloaded ? <CheckCircle size={18} weight="fill" /> : <DownloadSimple size={18} weight="bold" />}
        {downloaded ? "کارت دانلود شد" : "دانلود کارت مراجعه"}
      </button>
      <div className={`notice ${downloaded ? "" : "warn"}`}>
        {downloaded ? <><CheckCircle size={16} weight="fill" /> کارت را نگه دارید و هنگام مراجعه نشان دهید.</> : <><Warning size={16} weight="fill" /> برای ادامه ابتدا کارت مراجعه را دانلود کنید.</>}
      </div>
      <button className={`btn ${buttonClass}`} onClick={onContinue} disabled={!downloaded}>ادامه</button>
    </div>
  );
}
