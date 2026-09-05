import { useEffect, useMemo, useState } from "react";
import {
  CaretRight,
  TrendUp,
  Bank,
  Buildings,
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
import NetworkOption from "../components/NetworkOption";
import InPersonPass from "../components/InPersonPass";
import { WhatsAppActionButton } from "../components/WhatsAppSupport";
import { generateInPersonCode } from "../lib/inPerson";

const EXCHANGES = ["Binance", "Bybit", "OKX", "KuCoin"];
const AZIZI_LOGO_URL = "https://i.postimg.cc/Y2FRCN2z/azizi.png";
const HESABPAY_LOGO_URL = "https://i.postimg.cc/63khhqcm/hesab.png";
const HESABPAY_QR_URL = "https://i.postimg.cc/D058wYSQ/Hesab.jpg";
const HESABPAY_PHONE = "0775146747";
const STEPS = ["amount", "quote", "payment", "receipt", "exchange", "network", "wallet", "review", "done"];

const providerLogoStyle = {
  width: 34,
  height: 34,
  objectFit: "contain",
  borderRadius: 8,
  background: "#fff",
};

function paymentLabel(method) {
  if (method === "in_person") return "پرداخت حضوری";
  if (method === "online_hesabpay") return "حساب‌پی";
  if (method === "online_azizi") return "عزیزی بانک";
  return "—";
}

function resolveNetwork(input, networks) {
  const q = String(input || "").trim().toLowerCase();
  if (!q) return null;
  return networks.find((item) => item.code.toLowerCase() === q || item.label.toLowerCase() === q) || null;
}

export default function Buy({ asset = "USDT", navigate, showError, resumeState, onResumeConsumed, onNeedProfile, onNeedVerification }) {
  const selectedAsset = normalizeAsset(asset);
  const coinLogo = assetLogo(selectedAsset);
  const coinName = ASSET_NAMES_FA[selectedAsset];

  const [stepIdx, setStepIdx] = useState(0);
  const [amount, setAmount] = useState("");
  const [quote, setQuote] = useState(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [checkingProfile, setCheckingProfile] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState(null);
  const [showInPersonPass, setShowInPersonPass] = useState(false);
  const [inPersonCode] = useState(() => generateInPersonCode());
  const [showOnlineProviders, setShowOnlineProviders] = useState(false);
  const [paymentInfo, setPaymentInfo] = useState(null);
  const [loadingPaymentInfo, setLoadingPaymentInfo] = useState(false);
  const [receiptUrl, setReceiptUrl] = useState(null);
  const [receiptUploading, setReceiptUploading] = useState(false);
  const [exchange, setExchange] = useState(null);
  const [exchangeCustom, setExchangeCustom] = useState("");
  const [network, setNetwork] = useState(null);
  const [networkCustom, setNetworkCustom] = useState("");
  const [walletAddress, setWalletAddress] = useState("");
  const [stablecoinConfig, setStablecoinConfig] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [cardPreviewUrl, setCardPreviewUrl] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [orderCode, setOrderCode] = useState(null);

  const step = STEPS[stepIdx];
  const networks = stablecoinConfig?.[selectedAsset]?.buy_networks || [];
  const finalExchange = exchange === "other" ? exchangeCustom.trim() : exchange;
  const finalNetwork = network === "other" ? resolveNetwork(networkCustom, networks)?.code : network;

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
      const q = await api.getQuote("buy", amt, selectedAsset);
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

  function choosePayment(method) {
    if (method === "in_person") {
      setShowOnlineProviders(false);
      setPaymentMethod("in_person");
      setPaymentInfo(null);
      setReceiptUrl(null);
      setShowInPersonPass(true);
      return;
    }
    if (method === "online") {
      setPaymentMethod(null);
      setShowOnlineProviders(true);
      return;
    }
    setShowOnlineProviders(false);
    setPaymentMethod(method);
    setPaymentInfo(null);
    setReceiptUrl(null);
    setStepIdx(4);
  }

  async function chooseOnlineProvider(provider) {
    setReceiptUrl(null);
    if (provider === "hesabpay") {
      setPaymentMethod("online_hesabpay");
      setPaymentInfo(null);
      setStepIdx(3);
      return;
    }
    setPaymentMethod("online_azizi");
    setLoadingPaymentInfo(true);
    try {
      setPaymentInfo(await api.getPaymentInfo());
      setStepIdx(3);
    } catch (err) {
      setPaymentMethod(null);
      showError(err instanceof ApiError ? err.message : "دریافت اطلاعات حساب عزیزی بانک ناموفق بود.");
    } finally {
      setLoadingPaymentInfo(false);
    }
  }

  async function handleReceiptFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setReceiptUploading(true);
    try {
      const res = await api.uploadReceipt(file);
      setReceiptUrl(res.url);
    } catch (err) {
      showError(err instanceof ApiError ? err.message : "آپلود رسید ناموفق بود.");
    } finally {
      setReceiptUploading(false);
    }
  }

  function chooseExchange(ex) {
    setExchange(ex);
    if (ex === "other") {
      setExchangeCustom("");
      return;
    }
    setStepIdx(5);
  }

  function continueCustomExchange() {
    if (!exchangeCustom.trim()) return showError("نام صرافی یا کیف پول را وارد کنید.");
    setStepIdx(5);
  }

  function chooseNetwork(code) {
    setNetwork(code);
    if (code === "other") {
      setNetworkCustom("");
      return;
    }
    setStepIdx(6);
  }

  function continueCustomNetwork() {
    if (!networkCustom.trim()) return showError("نام شبکه را وارد کنید.");
    const resolved = resolveNetwork(networkCustom, networks);
    if (!resolved) return showError(`شبکهٔ واردشده برای ${selectedAsset} پشتیبانی نمی‌شود.`);
    setNetwork(resolved.code);
    setStepIdx(6);
  }

  async function prepareReview() {
    if (!finalExchange) return showError("نام صرافی یا کیف پول الزامی است.");
    if (!finalNetwork) return showError("شبکهٔ معتبر را مشخص کنید.");
    if (!walletAddress.trim()) return showError("آدرس ولت را وارد کنید.");

    setPreviewLoading(true);
    clearPreview();
    try {
      const blob = await api.getCardPreview({
        action: "buy",
        asset: selectedAsset,
        amount: parseFloat(amount),
        exchange_name: finalExchange,
        network: finalNetwork,
        wallet_address: walletAddress.trim(),
      });
      setCardPreviewUrl(URL.createObjectURL(blob));
      setStepIdx(7);
    } catch (err) {
      showError(err instanceof ApiError ? err.message : "آماده‌سازی صفحهٔ بررسی ناموفق بود.");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function submitOrder() {
    setSubmitting(true);
    try {
      const res = await api.createBuyOrder({
        asset: selectedAsset,
        amount: parseFloat(amount),
        payment_method: paymentMethod,
        exchange_name: finalExchange,
        network: finalNetwork,
        wallet_address: walletAddress.trim(),
        receipt_url: receiptUrl,
        in_person_code: paymentMethod === "in_person" ? inPersonCode : null,
      });
      clearPreview();
      setOrderCode(res.order_code);
      setStepIdx(8);
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

  const isHesabPay = paymentMethod === "online_hesabpay";

  return (
    <div className="app-shell">
      <div className="header">
        {step !== "done" ? <button className="back-btn" onClick={goBack} aria-label="بازگشت"><CaretRight size={18} weight="bold" /></button> : <div className="header-spacer" />}
        <h1><TrendUp size={18} className="header-icon" weight="bold" /> خرید {selectedAsset}</h1>
        <div className="header-spacer" />
      </div>

      {step !== "done" && <div className="stepper">{STEPS.slice(0, -1).map((s, i) => <div key={s} className={`dot ${i <= stepIdx ? "active" : ""}`} />)}</div>}

      {step === "amount" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label">چند {selectedAsset} می‌خواهید بخرید؟</label>
            <div className="amount-field">
              <input className="input num" type="number" inputMode="decimal" placeholder="مثال: 100" value={amount} onChange={(e) => setAmount(e.target.value)} />
              <span className="amount-badge"><img src={coinLogo} alt={selectedAsset} style={{ borderRadius: "50%" }} /></span>
            </div>
            <div className="notice" style={{ marginTop: 10 }}>{coinName} ({selectedAsset})</div>
          </div>
          <button className="btn btn-buy" onClick={fetchQuote} disabled={loadingQuote}>{loadingQuote ? <span className="spinner" /> : "محاسبهٔ نرخ"}</button>
        </div>
      )}

      {step === "quote" && quote && (
        <div className="card animate-in">
          <div className="quote-box">
            <div className="quote-row"><span>مقدار درخواستی</span><span className="value num" style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><img src={coinLogo} alt="" className="tether-badge" style={{ borderRadius: "50%" }} />{Number(amount).toLocaleString()} {selectedAsset}</span></div>
            <div className="quote-row"><span>مبلغ قابل پرداخت به دالر</span><span className="value num">${Number(quote.payable_usd ?? quote.total_usd ?? amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span></div>
            <div className="quote-row"><span>نرخ دالر</span><span className="value num">{quote.usd_rate.toLocaleString()} افغانی</span></div>
            <div className="quote-row"><span>مبلغ پایه</span><span className="value num">{quote.base_afn.toLocaleString()} افغانی</span></div>
            <div className="quote-row"><span>کارمزد ({quote.fee_percent}٪)</span><span className="value num">{quote.fee_afn.toLocaleString()} افغانی</span></div>
            <div className="quote-total buy"><span className="label">مبلغ نهایی قابل پرداخت</span><span className="amount num">{quote.total_afn.toLocaleString()} ؋</span></div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}>
            <button className="btn btn-buy" onClick={() => checkGateAndProceed(parseFloat(amount), quote)} disabled={checkingProfile}>{checkingProfile ? <span className="spinner" /> : <>ادامهٔ درخواست خرید <ArrowRight size={16} weight="bold" /></>}</button>
            <div className="help-actions-grid">
              <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، در مورد خرید و فروش ${selectedAsset} در صراف معلومات بیشتر می‌خواهم.`)}><ChatCircleDots size={17} /> اطلاعات بیشتر</button>
              <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS", `سلام، برای خرید و فروش ${selectedAsset} در صراف به پشتیبانی نیاز دارم.`)}><Headset size={17} /> پشتیبانی</button>
              <WhatsAppActionButton mode="support" asset={selectedAsset} />
            </div>
          </div>
        </div>
      )}

      {step === "payment" && (
        <div className="card animate-in">
          <label className="field-label">روش پرداخت خود را انتخاب کنید</label>
          <div className="choice-row" style={{ marginTop: 4 }}>
            <button className="choice-btn" onClick={() => choosePayment("in_person")} disabled={loadingPaymentInfo}><Buildings size={16} /> حضوری</button>
            <button className={`choice-btn ${showOnlineProviders ? "selected" : ""}`} onClick={() => choosePayment("online")} disabled={loadingPaymentInfo}><Bank size={16} /> آنلاین</button>
          </div>
          {showOnlineProviders && <div style={{ marginTop: 16 }}><label className="field-label">روش پرداخت آنلاین را انتخاب کنید</label><div className="choice-row" style={{ marginTop: 6 }}><button className="choice-btn" onClick={() => chooseOnlineProvider("azizi")} disabled={loadingPaymentInfo}>{loadingPaymentInfo ? <span className="spinner" /> : <img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={providerLogoStyle} />} عزیزی بانک</button><button className="choice-btn" onClick={() => chooseOnlineProvider("hesabpay")} disabled={loadingPaymentInfo}><img src={HESABPAY_LOGO_URL} alt="HesabPay" style={providerLogoStyle} /> حساب‌پی</button></div></div>}
          {showInPersonPass && <div style={{ marginTop: 16 }}><InPersonPass action="buy" asset={selectedAsset} code={inPersonCode} buttonClass="btn-buy" showError={showError} onContinue={() => { setShowInPersonPass(false); setStepIdx(4); }} /></div>}
        </div>
      )}

      {step === "receipt" && (
        <div className="card animate-in">
          {isHesabPay ? <><div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}><img src={HESABPAY_LOGO_URL} alt="HesabPay" style={{ ...providerLogoStyle, width: 54, height: 54 }} /></div><div className="info-box" style={{ marginBottom: 14, textAlign: "center" }}><img src={HESABPAY_QR_URL} alt="QR حساب‌پی" style={{ width: "min(100%, 260px)", borderRadius: 14, display: "block", margin: "0 auto 14px" }} /><CopyRow label="شماره حساب‌پی" value={HESABPAY_PHONE} /></div></> : <><div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}><img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={{ ...providerLogoStyle, width: 54, height: 54 }} /></div>{paymentInfo && <div className="info-box" style={{ marginBottom: 14 }}><CopyRow label="بانک" value={paymentInfo.bank_name} /><CopyRow label="صاحب حساب" value={paymentInfo.bank_account_holder} /><CopyRow label="شماره حساب" value={paymentInfo.bank_account_number} /></div>}</>}
          <div className="notice" style={{ marginBottom: 16 }}>پس از پرداخت، تصویر رسید را بارگذاری کنید.</div>
          <label className={`upload-box ${receiptUrl ? "has-file" : ""}`}><input type="file" accept="image/*" onChange={handleReceiptFile} />{receiptUploading ? <span className="spinner" /> : receiptUrl ? <CheckCircle size={22} weight="fill" /> : <UploadSimple size={22} />}<span>{receiptUploading ? "در حال آپلود..." : receiptUrl ? "رسید بارگذاری شد" : "انتخاب تصویر رسید"}</span></label>
          <button className="btn btn-buy" style={{ marginTop: 16 }} disabled={!receiptUrl || receiptUploading} onClick={() => setStepIdx(4)}>ادامه</button>
        </div>
      )}

      {step === "exchange" && (
        <div className="card animate-in">
          <label className="field-label">{selectedAsset} را در کدام صرافی یا کیف پول می‌خواهید دریافت کنید؟</label>
          <div className="choice-row" style={{ marginTop: 4 }}>{EXCHANGES.map((ex) => <button key={ex} className={`choice-btn ${exchange === ex ? "selected" : ""}`} onClick={() => chooseExchange(ex)}>{ex}</button>)}</div>
          <div style={{ marginTop: 10 }}><button className={`choice-btn ${exchange === "other" ? "selected" : ""}`} style={{ width: "100%" }} onClick={() => chooseExchange("other")}>کیف پول شخصی / صرافی دیگر</button></div>
          {exchange === "other" && <><input className="input" style={{ marginTop: 12 }} placeholder="نام صرافی یا کیف پول" value={exchangeCustom} onChange={(e) => setExchangeCustom(e.target.value)} /><button className="btn btn-buy" style={{ marginTop: 12 }} onClick={continueCustomExchange} disabled={!exchangeCustom.trim()}>ادامه</button></>}
        </div>
      )}

      {step === "network" && (
        <div className="card animate-in">
          <label className="field-label">شبکهٔ مورد نظر برای دریافت {selectedAsset}</label>
          <div className="notice" style={{ marginBottom: 12 }}>فقط شبکه‌های پشتیبانی‌شده برای {selectedAsset} نمایش داده می‌شوند.</div>
          <div className="network-option-list" style={{ marginTop: 4 }}>{networks.map((item) => <NetworkOption key={item.code} item={item} selected={network === item.code} onClick={() => chooseNetwork(item.code)} />)}</div>
          <div style={{ marginTop: 10 }}><button className={`choice-btn ${network === "other" ? "selected" : ""}`} style={{ width: "100%" }} onClick={() => chooseNetwork("other")}><MagnifyingGlass size={16} /> وارد کردن نام شبکه</button></div>
          {network === "other" && <><input className="input" style={{ marginTop: 12 }} placeholder="مثال: Ethereum یا Base" value={networkCustom} onChange={(e) => setNetworkCustom(e.target.value)} /><button className="btn btn-buy" style={{ marginTop: 12 }} onClick={continueCustomNetwork} disabled={!networkCustom.trim()}>بررسی و ادامه</button></>}
        </div>
      )}

      {step === "wallet" && (
        <div className="card animate-in">
          <div className="field"><label className="field-label">آدرس ولت دریافت {selectedAsset}</label><textarea className="input num" rows={3} placeholder="آدرس ولت را دقیق وارد کنید" value={walletAddress} onChange={(e) => setWalletAddress(e.target.value)} /></div>
          <div className="notice" style={{ marginBottom: 12 }}>شبکه: <b>{networkLabel}</b></div>
          <div className="notice warn" style={{ marginBottom: 16 }}><Warning size={16} className="notice-icon" weight="fill" />آدرس و شبکه را دقیق بررسی کنید؛ انتقال بلاک‌چینی به آدرس یا شبکهٔ اشتباه قابل برگشت نیست.</div>
          <button className="btn btn-buy" onClick={prepareReview} disabled={!walletAddress.trim() || previewLoading}>{previewLoading ? <span className="spinner" /> : <>بررسی درخواست <ArrowRight size={16} weight="bold" /></>}</button>
        </div>
      )}

      {step === "review" && quote && (
        <OrderReview
          action="buy"
          asset={selectedAsset}
          amount={amount}
          quote={quote}
          exchange={finalExchange}
          network={networkLabel}
          walletAddress={walletAddress.trim()}
          paymentLabel={paymentLabel(paymentMethod)}
          inPersonCode={paymentMethod === "in_person" ? inPersonCode : null}
          cardPreviewUrl={cardPreviewUrl}
          previewLoading={previewLoading}
          onBack={goBack}
          onConfirm={submitOrder}
          submitting={submitting}
        />
      )}

      {step === "done" && (
        <div className="card success-screen animate-in"><div className="success-icon"><CheckCircle size={36} weight="fill" /></div><div style={{ fontWeight: 700, fontSize: 16 }}>سفارش خرید {selectedAsset} ثبت شد</div><div className="code num">{orderCode}</div><div className="notice" style={{ textAlign: "right" }}>{selectedAsset} شما پس از تایید پرداخت، ظرف کمتر از ۱ ساعت به آدرس ثبت‌شده واریز خواهد شد.<br />پشتیبانی: @SJDPLUS</div><button className="btn btn-secondary" onClick={() => navigate("orders")}><ClipboardText size={17} /> مشاهدهٔ سفارش‌های من</button><button className="btn btn-outline" onClick={() => navigate("home")}><House size={17} /> بازگشت به منوی اصلی</button></div>
      )}
    </div>
  );
}
