from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def replace_once(path, old, new):
    text = read(path)
    if old not in text:
        raise RuntimeError(f"Pattern not found in {path}: {old[:120]!r}")
    write(path, text.replace(old, new, 1))


# ------------------------------------------------------------------
# Shared components
# ------------------------------------------------------------------
write("webapp/src/components/InPersonPass.jsx", r'''import { useMemo, useState } from "react";
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
''')

write("webapp/src/components/WhatsAppSupport.jsx", r'''import { ChatCircleDots, MagnifyingGlass } from "@phosphor-icons/react";

const WHATSAPP_QR_URL = "https://wa.me/qr/25MA3IJZTGQPE1";
const SUPPORT_TEXT = "سلام، برای استفاده از خدمات خرید و فروش USDT / USDC در Saraf به پشتیبانی نیاز دارم.";
const TRACK_TEXT = "سلام، برای رهگیری سفارش Saraf پیام می‌دهم. لطفاً وضعیت سفارش من را بررسی کنید. کد سفارش: ";

function openWhatsApp(text) {
  // لینک QR داده‌شده مستقیماً چت را باز می‌کند؛ متن آماده در کلیپ‌بورد قرار می‌گیرد
  // تا حتی روی کلاینت‌هایی که query text را برای لینک QR پشتیبانی نمی‌کنند قابل استفاده باشد.
  navigator.clipboard?.writeText(text).catch(() => {});
  window.open(WHATSAPP_QR_URL, "_blank", "noopener,noreferrer");
}

export default function WhatsAppSupport() {
  return (
    <div className="whatsapp-support-bar" aria-label="پشتیبانی واتسپ">
      <button type="button" onClick={() => openWhatsApp(SUPPORT_TEXT)}><ChatCircleDots size={17} weight="fill" /> پشتیبانی واتسپ</button>
      <button type="button" onClick={() => openWhatsApp(TRACK_TEXT)}><MagnifyingGlass size={17} weight="bold" /> رهگیری سفارش</button>
    </div>
  );
}
''')

# ------------------------------------------------------------------
# App: global WhatsApp support / tracking
# ------------------------------------------------------------------
replace_once(
    "webapp/src/App.jsx",
    'import Toast from "./components/Toast";\n',
    'import Toast from "./components/Toast";\nimport WhatsAppSupport from "./components/WhatsAppSupport";\n',
)
replace_once(
    "webapp/src/App.jsx",
    '      <Toast message={error} onClose={() => setError(null)} />\n',
    '      <WhatsAppSupport />\n      <Toast message={error} onClose={() => setError(null)} />\n',
)

# ------------------------------------------------------------------
# Network presentation: compact, ordered, logo + short + full name
# ------------------------------------------------------------------
# Buy
replace_once("webapp/src/pages/Buy.jsx", 'import NetworkIcon from "../components/NetworkIcon";\n', 'import NetworkOption from "../components/NetworkOption";\nimport InPersonPass from "../components/InPersonPass";\n')
replace_once("webapp/src/pages/Buy.jsx", '  const [paymentMethod, setPaymentMethod] = useState(null);\n', '  const [paymentMethod, setPaymentMethod] = useState(null);\n  const [showInPersonPass, setShowInPersonPass] = useState(false);\n  const [inPersonCode] = useState(() => String(Math.floor(1000 + Math.random() * 9000)));\n')
replace_once("webapp/src/pages/Buy.jsx", '  function choosePayment(method) {\n    if (method === "online") {\n', '  function choosePayment(method) {\n    if (method === "in_person") {\n      setShowOnlineProviders(false);\n      setPaymentMethod("in_person");\n      setPaymentInfo(null);\n      setReceiptUrl(null);\n      setShowInPersonPass(true);\n      return;\n    }\n    if (method === "online") {\n')
replace_once("webapp/src/pages/Buy.jsx", '        receipt_url: receiptUrl,\n', '        receipt_url: receiptUrl,\n        in_person_code: paymentMethod === "in_person" ? inPersonCode : null,\n')
replace_once("webapp/src/pages/Buy.jsx", '<div className="quote-row"><span>ارزش دالری</span><span className="value num">${Number(quote.total_usd ?? amount).toLocaleString()}</span></div>', '<div className="quote-row"><span>مبلغ قابل پرداخت به دالر</span><span className="value num">${Number(quote.payable_usd ?? quote.total_usd ?? amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span></div>')
replace_once("webapp/src/pages/Buy.jsx", '<div className="choice-row cols-3" style={{ marginTop: 4 }}>{networks.map((item) => <button key={item.code} className={`choice-btn ${network === item.code ? "selected" : ""}`} onClick={() => chooseNetwork(item.code)}><NetworkIcon network={item.code} size={18} />{item.label}</button>)}</div>', '<div className="network-option-list" style={{ marginTop: 4 }}>{networks.map((item) => <NetworkOption key={item.code} item={item} selected={network === item.code} onClick={() => chooseNetwork(item.code)} />)}</div>')
replace_once("webapp/src/pages/Buy.jsx", '          {showOnlineProviders && <div style={{ marginTop: 16 }}><label className="field-label">روش پرداخت آنلاین را انتخاب کنید</label><div className="choice-row" style={{ marginTop: 6 }}><button className="choice-btn" onClick={() => chooseOnlineProvider("azizi")} disabled={loadingPaymentInfo}>{loadingPaymentInfo ? <span className="spinner" /> : <img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={providerLogoStyle} />} عزیزی بانک</button><button className="choice-btn" onClick={() => chooseOnlineProvider("hesabpay")} disabled={loadingPaymentInfo}><img src={HESABPAY_LOGO_URL} alt="HesabPay" style={providerLogoStyle} /> حساب‌پی</button></div></div>}\n', '          {showOnlineProviders && <div style={{ marginTop: 16 }}><label className="field-label">روش پرداخت آنلاین را انتخاب کنید</label><div className="choice-row" style={{ marginTop: 6 }}><button className="choice-btn" onClick={() => chooseOnlineProvider("azizi")} disabled={loadingPaymentInfo}>{loadingPaymentInfo ? <span className="spinner" /> : <img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={providerLogoStyle} />} عزیزی بانک</button><button className="choice-btn" onClick={() => chooseOnlineProvider("hesabpay")} disabled={loadingPaymentInfo}><img src={HESABPAY_LOGO_URL} alt="HesabPay" style={providerLogoStyle} /> حساب‌پی</button></div></div>}\n          {showInPersonPass && <div style={{ marginTop: 16 }}><InPersonPass action="buy" asset={selectedAsset} code={inPersonCode} buttonClass="btn-buy" onContinue={() => { setShowInPersonPass(false); setStepIdx(4); }} /></div>}\n')
replace_once("webapp/src/pages/Buy.jsx", '          paymentLabel={paymentLabel(paymentMethod)}\n', '          paymentLabel={paymentLabel(paymentMethod)}\n          inPersonCode={paymentMethod === "in_person" ? inPersonCode : null}\n')

# Sell
replace_once("webapp/src/pages/Sell.jsx", 'import NetworkIcon from "../components/NetworkIcon";\n', 'import NetworkOption from "../components/NetworkOption";\nimport InPersonPass from "../components/InPersonPass";\n')
replace_once("webapp/src/pages/Sell.jsx", '  const [receiveMethod, setReceiveMethod] = useState(null);\n', '  const [receiveMethod, setReceiveMethod] = useState(null);\n  const [showInPersonPass, setShowInPersonPass] = useState(false);\n  const [inPersonCode] = useState(() => String(Math.floor(1000 + Math.random() * 9000)));\n')
replace_once("webapp/src/pages/Sell.jsx", '  function chooseReceive(method) {\n    if (method === "online") {\n', '  function chooseReceive(method) {\n    if (method === "in_person") {\n      setShowOnlineProviders(false);\n      setReceiveMethod("in_person");\n      setShowInPersonPass(true);\n      return;\n    }\n    if (method === "online") {\n')
replace_once("webapp/src/pages/Sell.jsx", '        bank_info: receiveMethod?.startsWith("online_") ? bankInfo.trim() : null,\n', '        bank_info: receiveMethod?.startsWith("online_") ? bankInfo.trim() : null,\n        in_person_code: receiveMethod === "in_person" ? inPersonCode : null,\n')
replace_once("webapp/src/pages/Sell.jsx", '<div className="quote-row"><span>ارزش دالری</span><span className="value num">${Number(quote.total_usd ?? amount).toLocaleString()}</span></div>', '<div className="quote-row"><span>مبلغ قابل دریافت به دالر</span><span className="value num">${Number(quote.receivable_usd ?? quote.total_usd ?? amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span></div>')
replace_once("webapp/src/pages/Sell.jsx", '<div className="choice-row cols-3" style={{ marginTop: 4 }}>{networks.map((item) => <button key={item.code} className={`choice-btn ${network === item.code ? "selected" : ""}`} onClick={() => chooseNetwork(item.code)}><NetworkIcon network={item.code} size={18} />{item.label}</button>)}</div>', '<div className="network-option-list" style={{ marginTop: 4 }}>{networks.map((item) => <NetworkOption key={item.code} item={item} selected={network === item.code} onClick={() => chooseNetwork(item.code)} />)}</div>')
replace_once("webapp/src/pages/Sell.jsx", '{step === "receive" && (\n        <div className="card animate-in"><label className="field-label">می‌خواهید مبلغ فروش را چگونه دریافت کنید؟</label><div className="choice-row" style={{ marginTop: 4 }}><button className="choice-btn" onClick={() => chooseReceive("in_person")} disabled={previewLoading}>{previewLoading && receiveMethod === "in_person" ? <span className="spinner" /> : <Buildings size={16} />} حضوری</button><button className={`choice-btn ${showOnlineProviders ? "selected" : ""}`} onClick={() => chooseReceive("online")} disabled={previewLoading}><Bank size={16} /> آنلاین</button></div>{showOnlineProviders && <div style={{ marginTop: 16 }}><label className="field-label">روش دریافت آنلاین را انتخاب کنید</label><div className="choice-row" style={{ marginTop: 6 }}><button className="choice-btn" onClick={() => chooseOnlineProvider("azizi")}><img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={providerLogoStyle} /> عزیزی بانک</button><button className="choice-btn" onClick={() => chooseOnlineProvider("hesabpay")}><img src={HESABPAY_LOGO_URL} alt="HesabPay" style={providerLogoStyle} /> حساب‌پی</button></div></div>}</div>\n      )}', '{step === "receive" && (\n        <div className="card animate-in">\n          <label className="field-label">می‌خواهید مبلغ فروش را چگونه دریافت کنید؟</label>\n          <div className="choice-row" style={{ marginTop: 4 }}><button className="choice-btn" onClick={() => chooseReceive("in_person")} disabled={previewLoading}><Buildings size={16} /> حضوری</button><button className={`choice-btn ${showOnlineProviders ? "selected" : ""}`} onClick={() => chooseReceive("online")} disabled={previewLoading}><Bank size={16} /> آنلاین</button></div>\n          {showOnlineProviders && <div style={{ marginTop: 16 }}><label className="field-label">روش دریافت آنلاین را انتخاب کنید</label><div className="choice-row" style={{ marginTop: 6 }}><button className="choice-btn" onClick={() => chooseOnlineProvider("azizi")}><img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={providerLogoStyle} /> عزیزی بانک</button><button className="choice-btn" onClick={() => chooseOnlineProvider("hesabpay")}><img src={HESABPAY_LOGO_URL} alt="HesabPay" style={providerLogoStyle} /> حساب‌پی</button></div></div>}\n          {showInPersonPass && <div style={{ marginTop: 16 }}><InPersonPass action="sell" asset={selectedAsset} code={inPersonCode} buttonClass="btn-sell" onContinue={() => { setShowInPersonPass(false); prepareReview("in_person"); }} /></div>}\n        </div>\n      )}')
replace_once("webapp/src/pages/Sell.jsx", '          receiveLabel={receiveLabel(receiveMethod)}\n', '          receiveLabel={receiveLabel(receiveMethod)}\n          inPersonCode={receiveMethod === "in_person" ? inPersonCode : null}\n')

# ------------------------------------------------------------------
# Order review UI: professional hierarchy and correct dollar payable/receivable
# ------------------------------------------------------------------
write("webapp/src/components/OrderReview.jsx", r'''import { CheckCircle, ShieldCheck, Warning, ArrowRight, CurrencyDollar, Wallet } from "@phosphor-icons/react";
import { assetLogo, normalizeAsset } from "../lib/brand";

function DetailRow({ label, value, mono = false }) {
  return (
    <div className="review-detail-row">
      <span>{label}</span>
      <strong className={mono ? "num" : ""}>{value || "—"}</strong>
    </div>
  );
}

export default function OrderReview({ action, asset, amount, quote, exchange, network, walletAddress, paymentLabel, paymentProofLabel, receiveLabel, payoutInfo, proofLabel, inPersonCode, cardPreviewUrl, previewLoading, onBack, onConfirm, submitting }) {
  const selectedAsset = normalizeAsset(asset);
  const isBuy = action === "buy";
  const afn = Number(quote?.total_afn || 0);
  const dollarAmount = Number(isBuy ? (quote?.payable_usd ?? quote?.total_usd ?? amount ?? 0) : (quote?.receivable_usd ?? quote?.total_usd ?? amount ?? 0));
  const resolvedPaymentProof = paymentProofLabel || (isBuy ? (paymentLabel === "پرداخت حضوری" ? "پرداخت حضوری — بدون رسید آنلاین" : "رسید پرداخت بارگذاری‌شده") : null);

  return (
    <div className="animate-in review-stack">
      <div className={`card review-hero ${isBuy ? "buy" : "sell"}`}>
        <div className="review-hero-head">
          <div className="review-asset-title">
            <span className="review-asset-logo"><img src={assetLogo(selectedAsset)} alt={selectedAsset} /></span>
            <div><h2>بررسی نهایی درخواست</h2><p>معلومات را پیش از ثبت نهایی کنترل کنید</p></div>
          </div>
          <span className="review-type-pill num">{isBuy ? "BUY" : "SELL"} {selectedAsset}</span>
        </div>

        <div className="review-amount-block">
          <span className="review-amount-label">مقدار معامله</span>
          <div className="review-amount-value"><img src={assetLogo(selectedAsset)} alt="" /><strong className="num">{Number(amount).toLocaleString()} {selectedAsset}</strong></div>
        </div>

        <div className="review-money-grid">
          <div className="review-money-card"><CurrencyDollar size={20} weight="bold" /><span>{isBuy ? "قابل پرداخت به دالر" : "قابل دریافت به دالر"}</span><strong className="num">${dollarAmount.toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong></div>
          <div className="review-money-card"><Wallet size={20} weight="bold" /><span>{isBuy ? "قابل پرداخت به افغانی" : "قابل دریافت به افغانی"}</span><strong className="num">{afn.toLocaleString()} ؋</strong></div>
        </div>
      </div>

      <div className="card review-details-card">
        <div className="review-section-title">جزئیات معامله</div>
        <DetailRow label="نوع درخواست" value={`${isBuy ? "خرید" : "فروش"} ${selectedAsset}`} />
        <DetailRow label="صرافی / کیف پول" value={exchange} />
        <DetailRow label="شبکه" value={network} mono />
        {walletAddress && <DetailRow label={isBuy ? "آدرس دریافت" : "آدرس واریز صراف"} value={walletAddress} mono />}
        {isBuy && <DetailRow label="روش پرداخت" value={paymentLabel} />}
        {isBuy && resolvedPaymentProof && <DetailRow label="وضعیت پرداخت / رسید" value={resolvedPaymentProof} />}
        {!isBuy && <DetailRow label="روش دریافت" value={receiveLabel} />}
        {!isBuy && payoutInfo && <DetailRow label="معلومات حساب دریافت" value={payoutInfo} mono />}
        {!isBuy && proofLabel && <DetailRow label="اثبات تراکنش" value={proofLabel} mono />}
        {inPersonCode && <DetailRow label="کد مراجعهٔ حضوری" value={inPersonCode} mono />}
        <DetailRow label="نرخ دالر" value={`${Number(quote?.usd_rate || 0).toLocaleString()} افغانی`} mono />
        {isBuy && Number(quote?.fee_afn || 0) > 0 && <DetailRow label="کارمزد" value={`${Number(quote.fee_afn).toLocaleString()} افغانی`} mono />}
      </div>

      <div className="card" style={{ padding: 14 }}>
        <div className="review-section-title"><ShieldCheck size={18} weight="fill" /> پیش‌نمایش کارت مشتری</div>
        {previewLoading && <div className="review-preview-placeholder"><span className="spinner" /></div>}
        {!previewLoading && cardPreviewUrl && <img src={cardPreviewUrl} alt="پیش‌نمایش کارت مشتری" className="review-card-preview" />}
        {!previewLoading && !cardPreviewUrl && <div className="notice warn"><Warning size={16} weight="fill" />پیش‌نمایش کارت در دسترس نیست.</div>}
      </div>

      <div className="notice warn"><Warning size={17} weight="fill" /> پس از تایید، درخواست برای بررسی تیم صراف ثبت می‌شود. شبکه، آدرس و مبلغ را دقیق کنترل کنید.</div>
      <button className={`btn ${isBuy ? "btn-buy" : "btn-sell"}`} onClick={onConfirm} disabled={submitting || previewLoading || !cardPreviewUrl}>{submitting ? <span className="spinner" /> : <><CheckCircle size={18} weight="fill" /> تایید و درخواست {isBuy ? "خرید" : "فروش"} {selectedAsset}</>}</button>
      <button className="btn btn-outline" onClick={onBack} disabled={submitting}><ArrowRight size={17} /> بازگشت و اصلاح معلومات</button>
    </div>
  );
}
''')

# ------------------------------------------------------------------
# Dollar calculations in quote service
# ------------------------------------------------------------------
replace_once("services/usdt_service.py", '    total_afn = base_afn + fee_afn\n\n    return {\n', '    total_afn = base_afn + fee_afn\n    payable_usd = total_afn / usd_sell_rate\n\n    return {\n')
replace_once("services/usdt_service.py", '        "total_usd": to_float(quantize_usd(amount_d)),\n        "basis": quote["saraf_quote"]["basis"],\n', '        "total_usd": to_float(quantize_usd(amount_d)),\n        "payable_usd": to_float(quantize_usd(payable_usd)),\n        "basis": quote["saraf_quote"]["basis"],\n')
replace_once("services/usdt_service.py", '    total_afn = amount_d * usd_buy_rate\n\n    return {\n', '    total_afn = amount_d * usd_buy_rate\n    receivable_usd = total_afn / usd_buy_rate\n\n    return {\n')
replace_once("services/usdt_service.py", '        "total_usd": to_float(quantize_usd(amount_d)),\n        "basis": quote["saraf_quote"]["basis"],\n    }\n', '        "total_usd": to_float(quantize_usd(amount_d)),\n        "receivable_usd": to_float(quantize_usd(receivable_usd)),\n        "basis": quote["saraf_quote"]["basis"],\n    }\n',)

# Guarded quote reconstruction also needs the fields for bound quotes.
replace_once("services/usdt_api_guard.py", '                "total_usd": to_float(D(q["total_usd"])),\n                "quote_id": q["id"],\n', '                "total_usd": to_float(D(q["total_usd"])),\n                "payable_usd": to_float(quantize_afn(D(q["total_afn"])) / rate),\n                "quote_id": q["id"],\n')
replace_once("services/usdt_api_guard.py", '                "total_usd": to_float(D(q["total_usd"])),\n                "quote_id": q["id"],\n                "expires_at": q["expires_at"],\n            }\n        qctx = _quote_context.get()\n        selected_asset = _normalize_asset(asset or (qctx or {}).get("asset"))\n        quote = await original_sell', '                "total_usd": to_float(D(q["total_usd"])),\n                "receivable_usd": to_float(D(q["total_usd"])),\n                "quote_id": q["id"],\n                "expires_at": q["expires_at"],\n            }\n        qctx = _quote_context.get()\n        selected_asset = _normalize_asset(asset or (qctx or {}).get("asset"))\n        quote = await original_sell')

# ------------------------------------------------------------------
# USDC BEP20 sell deposit wallet
# ------------------------------------------------------------------
replace_once("services/stablecoin_networks.py", '    "USDC": [\n        {"code": "ERC20", "label": "Ethereum", "family": "evm"},\n', '    "USDC": [\n        {"code": "BEP20", "label": "BNB Smart Chain", "family": "evm"},\n        {"code": "ERC20", "label": "Ethereum", "family": "evm"},\n')
replace_once("services/stablecoin_networks.py", 'def _load_usdc_deposit_wallets() -> dict[str, str]:\n', 'USDC_DEFAULT_DEPOSIT_WALLETS = {\n    "BEP20": "0x4f43149a206694e53ca23abe407d58f01a416149",\n}\n\n\ndef _load_usdc_deposit_wallets() -> dict[str, str]:\n')
replace_once("services/stablecoin_networks.py", '    return {str(k).strip().upper(): str(v).strip() for k, v in parsed.items() if str(v).strip()}\n', '    configured = {str(k).strip().upper(): str(v).strip() for k, v in parsed.items() if str(v).strip()}\n    return {**USDC_DEFAULT_DEPOSIT_WALLETS, **configured}\n')

# ------------------------------------------------------------------
# Persist 4-digit in-person code in API / order records
# ------------------------------------------------------------------
replace_once("api.py", 'class UsdtBuyOrderRequest(BaseModel):\n    amount: float\n', 'class UsdtBuyOrderRequest(BaseModel):\n    amount: float\n    in_person_code: Optional[str] = None\n')
replace_once("api.py", 'class UsdtSellOrderRequest(BaseModel):\n    amount: float\n', 'class UsdtSellOrderRequest(BaseModel):\n    amount: float\n    in_person_code: Optional[str] = None\n')
replace_once("api.py", '    if payload.payment_method not in ("in_person", "online"):\n', '    if payload.payment_method not in ("in_person", "online"):\n')
replace_once("api.py", '    if payload.payment_method == "online" and not payload.receipt_url:\n', '    if payload.payment_method == "in_person" and (not payload.in_person_code or not payload.in_person_code.isdigit() or len(payload.in_person_code) != 4):\n        raise HTTPException(status_code=400, detail="کد ۴ رقمی مراجعهٔ حضوری نامعتبر است.")\n    if payload.payment_method == "online" and not payload.receipt_url:\n')
replace_once("api.py", '        quote_id=quote.get("quote_id"),\n    )\n    return {"order_id": result["order_id"], "order_code": result["order_code"], "quote": quote}\n', '        quote_id=quote.get("quote_id"),\n        in_person_code=payload.in_person_code,\n    )\n    return {"order_id": result["order_id"], "order_code": result["order_code"], "quote": quote}\n',)
replace_once("api.py", '    if payload.receive_method == "online" and not payload.bank_info:\n', '    if payload.receive_method == "in_person" and (not payload.in_person_code or not payload.in_person_code.isdigit() or len(payload.in_person_code) != 4):\n        raise HTTPException(status_code=400, detail="کد ۴ رقمی مراجعهٔ حضوری نامعتبر است.")\n    if payload.receive_method == "online" and not payload.bank_info:\n')
# second order call
sell_call_old = '        quote_id=quote.get("quote_id"),\n    )\n    return {"order_id": result["order_id"], "order_code": result["order_code"], "quote": quote}\n'
text = read("api.py")
pos = text.find(sell_call_old, text.find("async def create_usdt_sell_order"))
if pos < 0:
    raise RuntimeError("Sell order call pattern not found")
text = text[:pos] + sell_call_old.replace('        quote_id=quote.get("quote_id"),\n', '        quote_id=quote.get("quote_id"),\n        in_person_code=payload.in_person_code,\n') + text[pos + len(sell_call_old):]
write("api.py", text)

# Service signatures / database payload / admin message
replace_once("services/usdt_order_service.py", '    asset: Optional[str] = None,\n) -> dict:\n    selected_asset = _asset_from(asset, quote)\n', '    asset: Optional[str] = None,\n    in_person_code: Optional[str] = None,\n) -> dict:\n    selected_asset = _asset_from(asset, quote)\n')
replace_once("services/usdt_order_service.py", '        "risk_reasons": "؛ ".join(risk_reasons) if risk_reasons else None,\n    }\n', '        "risk_reasons": "؛ ".join(risk_reasons) if risk_reasons else None,\n        "in_person_code": in_person_code if payment_method == "in_person" else None,\n    }\n')
replace_once("services/usdt_order_service.py", '        f"روش پرداخت: {_md_escape(payment_method)}\\n"\n', '        f"روش پرداخت: {_md_escape(payment_method)}\\n"\n        f"کد مراجعه حضوری: {_md_escape(in_person_code) if payment_method == \'in_person\' else \'-\'}\\n"\n')
# sell signature: target second occurrence manually
text = read("services/usdt_order_service.py")
needle = '    asset: Optional[str] = None,\n) -> dict:\n    selected_asset = _asset_from(asset, quote)\n'
pos = text.find(needle, text.find("async def create_sell_order"))
if pos < 0:
    raise RuntimeError("Sell signature pattern not found")
text = text[:pos] + needle.replace('    asset: Optional[str] = None,\n', '    asset: Optional[str] = None,\n    in_person_code: Optional[str] = None,\n') + text[pos + len(needle):]
write("services/usdt_order_service.py", text)
text = read("services/usdt_order_service.py")
start = text.find("async def create_sell_order")
needle = '        "risk_reasons": "؛ ".join(risk_reasons) if risk_reasons else None,\n    }\n'
pos = text.find(needle, start)
if pos < 0:
    raise RuntimeError("Sell order payload pattern not found")
text = text[:pos] + needle.replace('    }\n', '        "in_person_code": in_person_code if receive_method == "in_person" else None,\n    }\n') + text[pos + len(needle):]
write("services/usdt_order_service.py", text)
replace_once("services/usdt_order_service.py", '        f"روش دریافت: {receive_label}\\n"\n', '        f"روش دریافت: {receive_label}\\n"\n        f"کد مراجعه حضوری: {_md_escape(in_person_code) if receive_method == \'in_person\' else \'-\'}\\n"\n')

write("supabase/migrations/20260905_002_in_person_code.sql", '''BEGIN;\n\nALTER TABLE public.usdt_orders\n  ADD COLUMN IF NOT EXISTS in_person_code text;\n\nALTER TABLE public.usdt_orders\n  DROP CONSTRAINT IF EXISTS usdt_orders_in_person_code_check;\n\nALTER TABLE public.usdt_orders\n  ADD CONSTRAINT usdt_orders_in_person_code_check\n  CHECK (in_person_code IS NULL OR in_person_code ~ '^[0-9]{4}$');\n\nCREATE INDEX IF NOT EXISTS usdt_orders_in_person_code_idx\n  ON public.usdt_orders (in_person_code)\n  WHERE in_person_code IS NOT NULL;\n\nCOMMIT;\n''')

# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------
with (ROOT / "webapp/src/index.css").open("a", encoding="utf-8") as f:
    f.write(r'''

/* ===== Stablecoin network selector ===== */
.network-option-list { display: flex; flex-direction: column; gap: 8px; }
.network-option { width: 100%; position: relative; border: 1px solid var(--color-border); background: var(--color-bg-elevated); border-radius: 16px; min-height: 70px; padding: 10px 12px; display: flex; align-items: center; gap: 12px; text-align: left; cursor: pointer; font-family: inherit; transition: .16s ease; }
.network-option.selected { border-color: var(--color-primary); background: var(--color-info-bg); box-shadow: 0 6px 18px rgba(0,113,227,.08); }
.network-option-copy { display: flex; min-width: 0; flex-direction: column; align-items: flex-start; line-height: 1.25; }
.network-option-code { color: var(--color-text); font-size: 17px; font-weight: 850; letter-spacing: -.01em; }
.network-option-name { color: var(--color-text-muted); font-size: 12.5px; margin-top: 5px; }
.network-option-check { position: absolute; right: 12px; color: var(--color-primary); }

/* ===== In-person pass ===== */
.inperson-pass-wrap { display: flex; flex-direction: column; gap: 10px; }
.inperson-pass { overflow: hidden; border: 1px solid var(--color-border); border-radius: 22px; background: linear-gradient(145deg,#fff,#f3f8ff); box-shadow: var(--shadow-card); }
.inperson-pass-head { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:16px; border-bottom:1px solid var(--color-border); }
.inperson-brand-lockup,.inperson-asset-lockup { display:flex; align-items:center; gap:9px; }
.inperson-brand-lockup img { width:38px; height:38px; border-radius:11px; object-fit:cover; }
.inperson-brand-lockup div { display:flex; flex-direction:column; }
.inperson-brand-lockup b { font-size:14px; }
.inperson-brand-lockup span { color:var(--color-text-muted); font-size:10.5px; }
.inperson-asset-lockup img { width:34px; height:34px; border-radius:50%; object-fit:contain; }
.inperson-action { text-align:center; font-size:16px; font-weight:800; padding:18px 16px 8px; }
.inperson-address { display:flex; align-items:flex-start; justify-content:center; gap:7px; padding:0 18px; text-align:center; color:var(--color-text-muted); font-size:12.5px; line-height:1.8; }
.inperson-address svg { color:var(--color-primary); flex-shrink:0; margin-top:2px; }
.inperson-code { margin:16px; border-radius:16px; background:#fff; border:1px solid var(--color-border); padding:13px; display:flex; align-items:center; justify-content:space-between; }
.inperson-code span { color:var(--color-text-muted); font-size:12px; }
.inperson-code strong { color:var(--color-primary); font-size:26px; letter-spacing:5px; }

/* ===== Final review ===== */
.review-stack { display:flex; flex-direction:column; gap:12px; }
.review-hero { padding:16px; overflow:hidden; }
.review-hero.buy { border-top:3px solid var(--color-buy); }
.review-hero.sell { border-top:3px solid #1d1d1f; }
.review-hero-head { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; }
.review-asset-title { display:flex; align-items:center; gap:10px; min-width:0; }
.review-asset-logo { width:44px; height:44px; border-radius:14px; background:#fff; display:grid; place-items:center; box-shadow:0 2px 10px rgba(0,0,0,.06); flex-shrink:0; }
.review-asset-logo img { width:34px; height:34px; object-fit:contain; border-radius:50%; }
.review-asset-title h2 { margin:0; font-size:16px; }
.review-asset-title p { margin:3px 0 0; font-size:11px; color:var(--color-text-muted); }
.review-type-pill { flex-shrink:0; border-radius:999px; background:var(--color-bg-elevated); padding:6px 9px; font-size:10.5px; font-weight:800; }
.review-amount-block { margin-top:16px; padding:15px; border-radius:18px; background:var(--color-bg-elevated); }
.review-amount-label { display:block; color:var(--color-text-muted); font-size:11px; margin-bottom:7px; }
.review-amount-value { display:flex; align-items:center; gap:8px; }
.review-amount-value img { width:24px; height:24px; border-radius:50%; }
.review-amount-value strong { font-size:22px; }
.review-money-grid { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-top:10px; }
.review-money-card { min-width:0; border:1px solid var(--color-border); border-radius:15px; background:#fff; padding:11px; display:flex; flex-direction:column; gap:4px; }
.review-money-card svg { color:var(--color-primary); }
.review-money-card span { color:var(--color-text-muted); font-size:10px; }
.review-money-card strong { font-size:15px; overflow-wrap:anywhere; }
.review-details-card { padding:15px; }
.review-section-title { display:flex; align-items:center; gap:7px; font-weight:800; font-size:13px; margin-bottom:8px; }
.review-detail-row { display:grid; grid-template-columns:minmax(95px,.8fr) minmax(0,1.6fr); gap:12px; padding:11px 0; border-bottom:1px solid var(--color-border); align-items:start; }
.review-detail-row:last-child { border-bottom:none; }
.review-detail-row span { color:var(--color-text-muted); font-size:11.5px; }
.review-detail-row strong { font-size:12px; text-align:left; overflow-wrap:anywhere; }
.review-preview-placeholder { min-height:180px; display:grid; place-items:center; background:var(--color-bg-elevated); border-radius:16px; }
.review-card-preview { width:100%; display:block; border-radius:16px; border:1px solid var(--color-border); }

/* ===== WhatsApp support ===== */
.whatsapp-support-bar { position:sticky; bottom:8px; z-index:30; margin:10px auto 8px; width:min(calc(100% - 24px),520px); display:grid; grid-template-columns:1fr 1fr; gap:8px; padding:7px; border:1px solid rgba(0,0,0,.08); border-radius:18px; background:rgba(255,255,255,.94); backdrop-filter:blur(14px); box-shadow:0 10px 30px rgba(0,0,0,.12); }
.whatsapp-support-bar button { border:0; border-radius:13px; min-height:40px; padding:8px 7px; display:flex; align-items:center; justify-content:center; gap:6px; font-family:inherit; font-weight:700; font-size:11.5px; cursor:pointer; }
.whatsapp-support-bar button:first-child { background:#eaf8ef; color:#16783a; }
.whatsapp-support-bar button:last-child { background:var(--color-bg-elevated); color:var(--color-text); }
''')

print("USDC miniapp fixes applied")
