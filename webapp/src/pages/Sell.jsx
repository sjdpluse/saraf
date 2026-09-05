import { useEffect, useMemo, useState } from "react";
import {
  CaretRight,
  TrendDown,
  Buildings,
  Bank,
  UploadSimple,
  CheckCircle,
  Warning,
  ClipboardText,
  House,
  ChatCircleDots,
  Headset,
  ArrowRight,
  MagnifyingGlass,
} from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { hapticSuccess, hapticError, openTelegramChat } from "../lib/telegram";
import CopyRow from "../components/CopyRow";
import OrderReview from "../components/OrderReview";
import { assetLogo, ASSET_NAMES_FA, normalizeAsset } from "../lib/brand";
import NetworkIcon from "../components/NetworkIcon";

const EXCHANGES = ["Binance", "Bybit", "OKX", "KuCoin"];
const AZIZI_LOGO_URL = "https://i.postimg.cc/Y2FRCN2z/azizi.png";
const HESABPAY_LOGO_URL = "https://i.postimg.cc/63khhqcm/hesab.png";
const STEPS = ["amount", "quote", "exchange", "network", "deposit", "txproof", "receive", "bank", "review", "done"];

const providerLogoStyle = {
  width: 34,
  height: 34,
  objectFit: "contain",
  borderRadius: 8,
  background: "#fff",
};

function receiveLabel(method) {
  if (method === "in_person") return "دریافت حضوری";
  if (method === "online_hesabpay") return "حساب‌پی";
  if (method === "online_azizi") return "عزیزی بانک";
  return "—";
}

function resolveNetwork(input, networks) {
  const q = String(input || "").trim().toLowerCase();
  if (!q) return null;
  return networks.find((item) => item.code.toLowerCase() === q || item.label.toLowerCase() === q) || null;
}

export default function Sell({ asset = "USDT", navigate, showError, resumeState, onResumeConsumed, onNeedProfile, onNeedVerification }) {
  const selectedAsset = normalizeAsset(asset);
  const coinLogo = assetLogo(selectedAsset);
  const coinName = ASSET_NAMES_FA[selectedAsset];

  const [stepIdx, setStepIdx] = useState(0);
  const [amount, setAmount] = useState("");
  const [quote, setQuote] = useState(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [checkingProfile, setCheckingProfile] = useState(false);
  const [exchange, setExchange] = useState(null);
  const [exchangeCustom, setExchangeCustom] = useState("");
  const [network, setNetwork] = useState(null);
  const [networkCustom, setNetworkCustom] = useState("");
  const [txProof, setTxProof] = useState("");
  const [txProofUploading, setTxProofUploading] = useState(false);
  const [txProofUrl, setTxProofUrl] = useState(null);
  const [receiveMethod, setReceiveMethod] = useState(null);
  const [showOnlineProviders, setShowOnlineProviders] = useState(false);
  const [bankInfo, setBankInfo] = useState("");
  const [stablecoinConfig, setStablecoinConfig] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [cardPreviewUrl, setCardPreviewUrl] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [orderCode, setOrderCode] = useState(null);

  const step = STEPS[stepIdx];
  const networks = stablecoinConfig?.[selectedAsset]?.sell_networks || [];
  const finalExchange = exchange === "other" ? exchangeCustom.trim() : exchange;
  const finalNetwork = network === "other" ? resolveNetwork(networkCustom, networks)?.code : network;
  const selectedNetworkInfo = networks.find((item) => item.code === finalNetwork) || null;
  const walletForNetwork = selectedNetworkInfo?.deposit_address || null;

  useEffect(() => {
    api.getStablecoinConfig().then(setStablecoinConfig).catch((e) => {
      showError(e instanceof ApiError ? e.message : "دریافت شبکه‌های پشتیبانی‌شده ناموفق بود.");
    });
    return () => {
      if (cardPreviewUrl) URL.revokeObjectURL(cardPreviewUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (resumeState?.amount && resumeState?.quote && normalizeAsset(resumeState.asset) === selectedAsset) {
      setAmount(String(resumeState.amount));
      setQuote(resumeState.quote);
      checkGateAndProceed(resumeState.amount, resumeState.quote);
      onResumeConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const networkLabel = useMemo(() => {
    const item = networks.find((n) => n.code === finalNetwork);
    return item ? `${item.label} (${item.code})` : finalNetwork || "—";
  }, [networks, finalNetwork]);

  function clearPreview() {
    if (cardPreviewUrl) URL.revokeObjectURL(cardPreviewUrl);
    setCardPreviewUrl(null);
  }

  function goBack() {
    if (step === "review") clearPreview();
    if (stepIdx === 0) navigate("home");
    else setStepIdx((i) => i - 1);
  }

  async function fetchQuote() {
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) return showError("لطفاً یک مقدار معتبر وارد کنید.");
    setLoadingQuote(true);
    try {
      const q = await api.getQuote("sell", amt, selectedAsset);
      setQuote(q);
      setStepIdx(1);
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "خطا در دریافت نرخ.");
    } finally {
      setLoadingQuote(false);
    }
  }

  async function checkGateAndProceed(amt, q) {
    setCheckingProfile(true);
    try {
      const profile = await api.getProfile();
      const resumeData = { asset: selectedAsset, amount: amt, quote: q };
      if (!profile.has_basic_profile) return onNeedProfile?.(resumeData);
      const threshold = profile.identity_verification_threshold_usd || 250;
      if (amt > threshold && !profile.has_identity_verification) return onNeedVerification?.(resumeData, threshold);
      setStepIdx(2);
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "خطا در بررسی وضعیت پروفایل.");
    } finally {
      setCheckingProfile(false);
    }
  }

  function chooseExchange(ex) {
    setExchange(ex);
    if (ex === "other") {
      setExchangeCustom("");
      return;
    }
    setStepIdx(3);
  }

  function continueCustomExchange() {
    if (!exchangeCustom.trim()) return showError("نام صرافی را وارد کنید.");
    setStepIdx(3);
  }

  function chooseNetwork(code) {
    setNetwork(code);
    if (code === "other") {
      setNetworkCustom("");
      return;
    }
    setStepIdx(4);
  }

  function continueCustomNetwork() {
    if (!networkCustom.trim()) return showError("نام شبکه را وارد کنید.");
    const resolved = resolveNetwork(networkCustom, networks);
    if (!resolved) return showError(`این شبکه برای فروش ${selectedAsset} در صراف فعال نیست.`);
    setNetwork(resolved.code);
    setStepIdx(4);
  }

  async function handleProofFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setTxProofUploading(true);
    try {
      const res = await api.uploadReceipt(file);
      setTxProofUrl(res.url);
    } catch (err) {
      showError(err instanceof ApiError ? err.message : "آپلود رسید ناموفق بود.");
    } finally {
      setTxProofUploading(false);
    }
  }

  function chooseReceive(method) {
    if (method === "online") {
      setReceiveMethod(null);
      setShowOnlineProviders(true);
      return;
    }
    setShowOnlineProviders(false);
    setReceiveMethod(method);
    prepareReview(method);
  }

  function chooseOnlineProvider(provider) {
    setBankInfo("");
    setReceiveMethod(provider === "hesabpay" ? "online_hesabpay" : "online_azizi");
    setStepIdx(7);
  }

  async function prepareReview(methodOverride) {
    const method = methodOverride || receiveMethod;
    const proof = txProofUrl || txProof.trim();
    if (!proof) return showError("لطفاً کد تراکنش (TxID) یا رسید تراکنش را وارد کنید.");
    if (!finalExchange) return showError("نام صرافی الزامی است.");
    if (!finalNetwork || !walletForNetwork) return showError("یک شبکهٔ دریافت فعال را انتخاب کنید.");
    if (!method) return showError("روش دریافت مبلغ را انتخاب کنید.");
    if (method.startsWith("online_") && !bankInfo.trim()) {
      return showError(method === "online_hesabpay" ? "شماره حساب‌پی خود را وارد کنید." : "معلومات حساب عزیزی بانک را وارد کنید.");
    }

    setPreviewLoading(true);
    clearPreview();
    try {
      const blob = await api.getCardPreview({
        action: "sell",
        asset: selectedAsset,
        amount: parseFloat(amount),
        exchange_name: finalExchange,
        network: finalNetwork,
      });
      setCardPreviewUrl(URL.createObjectURL(blob));
      setStepIdx(8);
    } catch (err) {
      showError(err instanceof ApiError ? err.message : "آماده‌سازی صفحهٔ بررسی ناموفق بود.");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function submitOrder() {
    const proof = txProofUrl || txProof.trim();
    setSubmitting(true);
    try {
      const res = await api.createSellOrder({
        asset: selectedAsset,
        amount: parseFloat(amount),
        exchange_name: finalExchange,
        network: finalNetwork,
        tx_proof: proof,
        receive_method: receiveMethod,
        bank_info: receiveMethod?.startsWith("online_") ? bankInfo.trim() : null,
      });
      clearPreview();
      setOrderCode(res.order_code);
      setStepIdx(9);
      hapticSuccess();
    } catch (err) {
      hapticError();
      if (err instanceof ApiError && err.code === "IDENTITY_VERIFICATION_REQUIRED") {
        onNeedVerification?.({ asset: selectedAsset, amount: parseFloat(amount), quote });
        return;
      }
      showError(err instanceof ApiError ? err.message : "ثبت سفارش ناموفق بود.");
    } finally {
      setSubmitting(false);
    }
  }

  const isHesabPay = receiveMethod === "online_hesabpay";
  const proofLabel = txProofUrl ? "تصویر رسید بارگذاری‌شده" : txProof.trim();

  return (
    <div className="app-shell">
      <div className="header">
        {step !== "done" ? <button className="back-btn" onClick={goBack} aria-label="بازگشت"><CaretRight size={18} weight="bold" /></button> : <div className="header-spacer" />}
        <h1><TrendDown size={18} className="header-icon" weight="bold" /> فروش {selectedAsset}</h1>
        <div className="header-spacer" />
      </div>

      {step !== "done" && <div className="stepper">{STEPS.slice(0, -1).map((s, i) => <div key={s} className={`dot ${i <= stepIdx ? "active" : ""}`} />)}</div>}

      {step === "amount" && (
        <div className="card animate-in">
          <div className="field"><label className="field-label">چند {selectedAsset} می‌خواهید بفروشید؟</label><div className="amount-field"><input className="input num" type="number" inputMode="decimal" placeholder="مثال: 100" value={amount} onChange={(e) => setAmount(e.target.value)} /><span className="amount-badge"><img src={coinLogo} alt={selectedAsset} style={{ borderRadius: "50%" }} /></span></div><div className="notice" style={{ marginTop: 10 }}>{coinName} ({selectedAsset})</div></div>
          <button className="btn btn-sell" onClick={fetchQuote} disabled={loadingQuote}>{loadingQuote ? <span className="spinner" /> : "محاسبهٔ نرخ"}</button>
        </div>
      )}

      {step === "quote" && quote && (
        <div className="card animate-in">
          <div className="quote-box"><div className="quote-row"><span>مقدار درخواستی</span><span className="value num" style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><img src={coinLogo} alt="" className="tether-badge" style={{ borderRadius: "50%" }} />{Number(amount).toLocaleString()} {selectedAsset}</span></div><div className="quote-row"><span>ارزش دالری</span><span className="value num">${Number(quote.total_usd ?? amount).toLocaleString()}</span></div><div className="quote-row"><span>نرخ دالر</span><span className="value num">{quote.usd_rate.toLocaleString()} افغانی</span></div><div className="quote-total sell"><span className="label">مبلغ قابل دریافت</span><span className="amount num">{quote.total_afn.toLocaleString()} ؋</span></div></div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}><button className="btn btn-sell" onClick={() => checkGateAndProceed(parseFloat(amount), quote)} disabled={checkingProfile}>{checkingProfile ? <span className="spinner" /> : <>ادامهٔ درخواست فروش <ArrowRight size={16} weight="bold" /></>}</button><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}><button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، در مورد خرید و فروش ${selectedAsset} در Saraf معلومات بیشتر می‌خواهم.`)}><ChatCircleDots size={17} /> اطلاعات بیشتر</button><button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، برای خرید و فروش ${selectedAsset} در Saraf به پشتیبانی نیاز دارم.`)}><Headset size={17} /> پشتیبانی</button></div></div>
        </div>
      )}

      {step === "exchange" && (
        <div className="card animate-in">
          <label className="field-label">{selectedAsset} را از کدام صرافی یا کیف پول ارسال می‌کنید؟</label>
          <div className="choice-row" style={{ marginTop: 4 }}>{EXCHANGES.map((ex) => <button key={ex} className={`choice-btn ${exchange === ex ? "selected" : ""}`} onClick={() => chooseExchange(ex)}>{ex}</button>)}</div>
          <div style={{ marginTop: 10 }}><button className={`choice-btn ${exchange === "other" ? "selected" : ""}`} style={{ width: "100%" }} onClick={() => chooseExchange("other")}>صرافی / کیف پول دیگر</button></div>
          {exchange === "other" && <><input className="input" style={{ marginTop: 12 }} placeholder="نام صرافی یا کیف پول" value={exchangeCustom} onChange={(e) => setExchangeCustom(e.target.value)} /><button className="btn btn-sell" style={{ marginTop: 12 }} onClick={continueCustomExchange} disabled={!exchangeCustom.trim()}>ادامه</button></>}
        </div>
      )}

      {step === "network" && (
        <div className="card animate-in">
          <label className="field-label">شبکهٔ ارسال {selectedAsset}</label>
          {networks.length === 0 ? (
            <div className="notice warn"><Warning size={16} weight="fill" />در حال حاضر آدرس دریافت صراف برای فروش {selectedAsset} تنظیم نشده است. تا زمان تنظیم آدرس، فروش این دارایی از طریق مینی‌اپ ثبت نمی‌شود.</div>
          ) : (
            <>
              <div className="notice" style={{ marginBottom: 12 }}>فقط شبکه‌هایی نمایش داده می‌شوند که آدرس دریافت صراف برای همان {selectedAsset} تنظیم شده باشد.</div>
              <div className="choice-row cols-3" style={{ marginTop: 4 }}>{networks.map((item) => <button key={item.code} className={`choice-btn ${network === item.code ? "selected" : ""}`} onClick={() => chooseNetwork(item.code)}><NetworkIcon network={item.code} size={18} />{item.label}</button>)}</div>
              <div style={{ marginTop: 10 }}><button className={`choice-btn ${network === "other" ? "selected" : ""}`} style={{ width: "100%" }} onClick={() => chooseNetwork("other")}><MagnifyingGlass size={16} /> وارد کردن نام شبکه</button></div>
              {network === "other" && <><input className="input" style={{ marginTop: 12 }} placeholder="نام شبکه" value={networkCustom} onChange={(e) => setNetworkCustom(e.target.value)} /><button className="btn btn-sell" style={{ marginTop: 12 }} onClick={continueCustomNetwork} disabled={!networkCustom.trim()}>بررسی و ادامه</button></>}
            </>
          )}
        </div>
      )}

      {step === "deposit" && (
        <div className="card animate-in"><div className="notice" style={{ marginBottom: 14 }}>لطفاً مقدار <b className="num">{amount} {selectedAsset}</b> را دقیقاً روی شبکهٔ <b>{networkLabel}</b> به آدرس زیر ارسال کنید:</div><div className="info-box" style={{ marginBottom: 14 }}><CopyRow value={walletForNetwork} /></div><div className="notice warn" style={{ marginBottom: 16 }}><Warning size={16} className="notice-icon" weight="fill" />دارایی و شبکه باید دقیقاً با همین مشخصات مطابقت داشته باشند. انتقال روی شبکهٔ دیگر ممکن است قابل بازیابی نباشد.</div><button className="btn btn-sell" onClick={() => setStepIdx(5)}>{selectedAsset} را ارسال کردم، ادامه</button></div>
      )}

      {step === "txproof" && (
        <div className="card animate-in"><label className="field-label">کد تراکنش (TxID) را وارد کنید یا عکس رسید را بارگذاری کنید</label><input className="input num" placeholder="TxID (اختیاری اگر عکس رسید بارگذاری می‌کنید)" value={txProof} onChange={(e) => setTxProof(e.target.value)} style={{ marginBottom: 12 }} /><label className={`upload-box ${txProofUrl ? "has-file" : ""}`}><input type="file" accept="image/*" onChange={handleProofFile} />{txProofUploading ? <span className="spinner" style={{ borderTopColor: "var(--color-buy)" }} /> : txProofUrl ? <CheckCircle size={22} weight="fill" /> : <UploadSimple size={22} />}<span>{txProofUploading ? "در حال آپلود..." : txProofUrl ? "رسید بارگذاری شد" : "یا انتخاب تصویر رسید"}</span></label><button className="btn btn-sell" style={{ marginTop: 16 }} disabled={!txProof.trim() && !txProofUrl} onClick={() => setStepIdx(6)}>ادامه</button></div>
      )}

      {step === "receive" && (
        <div className="card animate-in"><label className="field-label">می‌خواهید مبلغ فروش را چگونه دریافت کنید؟</label><div className="choice-row" style={{ marginTop: 4 }}><button className="choice-btn" onClick={() => chooseReceive("in_person")} disabled={previewLoading}>{previewLoading && receiveMethod === "in_person" ? <span className="spinner" /> : <Buildings size={16} />} حضوری</button><button className={`choice-btn ${showOnlineProviders ? "selected" : ""}`} onClick={() => chooseReceive("online")} disabled={previewLoading}><Bank size={16} /> آنلاین</button></div>{showOnlineProviders && <div style={{ marginTop: 16 }}><label className="field-label">روش دریافت آنلاین را انتخاب کنید</label><div className="choice-row" style={{ marginTop: 6 }}><button className="choice-btn" onClick={() => chooseOnlineProvider("azizi")}><img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={providerLogoStyle} /> عزیزی بانک</button><button className="choice-btn" onClick={() => chooseOnlineProvider("hesabpay")}><img src={HESABPAY_LOGO_URL} alt="HesabPay" style={providerLogoStyle} /> حساب‌پی</button></div></div>}</div>
      )}

      {step === "bank" && (
        <div className="card animate-in"><div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}><img src={isHesabPay ? HESABPAY_LOGO_URL : AZIZI_LOGO_URL} alt={isHesabPay ? "HesabPay" : "Azizi Bank"} style={{ ...providerLogoStyle, width: 54, height: 54 }} /></div><div className="field"><label className="field-label">{isHesabPay ? "شماره حساب‌پی خود را وارد کنید" : "نام صاحب حساب و شمارهٔ حساب عزیزی بانک خود را وارد کنید"}</label>{isHesabPay ? <input className="input num" inputMode="tel" placeholder="مثال: 0775123456" value={bankInfo} onChange={(e) => setBankInfo(e.target.value)} /> : <textarea className="input" rows={3} placeholder="نام صاحب حساب — شماره حساب" value={bankInfo} onChange={(e) => setBankInfo(e.target.value)} />}</div><button className="btn btn-sell" onClick={() => prepareReview(receiveMethod)} disabled={!bankInfo.trim() || previewLoading}>{previewLoading ? <span className="spinner" /> : <>بررسی درخواست <ArrowRight size={16} weight="bold" /></>}</button></div>
      )}

      {step === "review" && quote && (
        <OrderReview
          action="sell"
          asset={selectedAsset}
          amount={amount}
          quote={quote}
          exchange={finalExchange}
          network={networkLabel}
          walletAddress={walletForNetwork}
          receiveLabel={receiveLabel(receiveMethod)}
          proofLabel={proofLabel}
          cardPreviewUrl={cardPreviewUrl}
          previewLoading={previewLoading}
          onBack={goBack}
          onConfirm={submitOrder}
          submitting={submitting}
        />
      )}

      {step === "done" && (
        <div className="card success-screen animate-in"><div className="success-icon"><CheckCircle size={36} weight="fill" /></div><div style={{ fontWeight: 700, fontSize: 16 }}>سفارش فروش {selectedAsset} ثبت شد</div><div className="code num">{orderCode}</div><div className="notice" style={{ textAlign: "right" }}>پس از تأیید تراکنش {selectedAsset} توسط تیم ما، مبلغ ظرف کمتر از ۱ ساعت پرداخت خواهد شد.<br />پشتیبانی: @SJDPLUS</div><button className="btn btn-secondary" onClick={() => navigate("orders")}><ClipboardText size={17} /> مشاهدهٔ سفارش‌های من</button><button className="btn btn-outline" onClick={() => navigate("home")}><House size={17} /> بازگشت به منوی اصلی</button></div>
      )}
    </div>
  );
}
