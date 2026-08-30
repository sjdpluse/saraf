import { useEffect, useState } from "react";
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
  ArrowRight,
} from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { hapticSuccess, hapticError, openTelegramChat } from "../lib/telegram";
import CopyRow from "../components/CopyRow";
import { TETHER_LOGO_URL } from "../lib/brand";
import NetworkIcon from "../components/NetworkIcon";

const EXCHANGES = ["Binance", "Bybit", "OKX", "KuCoin"];
const NETWORKS = ["TRC20", "ERC20", "BEP20"];
const DEPOSIT_WALLETS = { BEP20: "0x4c49Ff39798C564A01F5fdEcB7E335a178f781BA" };

const AZIZI_LOGO_URL = "https://i.postimg.cc/Y2FRCN2z/azizi.png";
const HESABPAY_LOGO_URL = "https://i.postimg.cc/63khhqcm/hesab.png";

const STEPS = ["amount", "quote", "exchange", "network", "deposit", "txproof", "receive", "bank", "done"];

const providerLogoStyle = {
  width: 34,
  height: 34,
  objectFit: "contain",
  borderRadius: 8,
  background: "#fff",
};

export default function Sell({ navigate, showError, resumeState, onResumeConsumed, onNeedProfile, onNeedVerification }) {
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
  const [submitting, setSubmitting] = useState(false);
  const [orderCode, setOrderCode] = useState(null);

  const step = STEPS[stepIdx];
  const finalNetwork = network === "other" ? networkCustom.trim() : network;
  const finalExchange = exchange === "other" ? exchangeCustom.trim() : exchange;
  const walletForNetwork = finalNetwork ? DEPOSIT_WALLETS[finalNetwork.toUpperCase()] : null;

  useEffect(() => {
    if (resumeState?.amount && resumeState?.quote) {
      setAmount(String(resumeState.amount));
      setQuote(resumeState.quote);
      checkGateAndProceed(resumeState.amount, resumeState.quote);
      onResumeConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function goBack() {
    if (stepIdx === 0) {
      navigate("home");
    } else {
      setStepIdx((i) => i - 1);
    }
  }

  async function fetchQuote() {
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) {
      showError("لطفاً یک مقدار معتبر وارد کنید.");
      return;
    }
    setLoadingQuote(true);
    try {
      const q = await api.getQuote("sell", amt);
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
      if (!profile.has_basic_profile) {
        onNeedProfile?.({ amount: amt, quote: q });
        return;
      }
      const threshold = profile.identity_verification_threshold_usd || 250;
      if (amt > threshold && !profile.has_identity_verification) {
        onNeedVerification?.({ amount: amt, quote: q }, threshold);
        return;
      }
      setStepIdx(2);
    } catch (e) {
      showError(e instanceof ApiError ? e.message : "خطا در بررسی وضعیت پروفایل.");
    } finally {
      setCheckingProfile(false);
    }
  }

  function chooseExchange(ex) {
    setExchange(ex);
    setStepIdx(3);
  }

  function chooseNetwork(net) {
    setNetwork(net);
    const wallet = DEPOSIT_WALLETS[net.toUpperCase()];
    if (net !== "other" && !wallet) {
      showError("در حال حاضر فقط شبکهٔ BEP20 برای دریافت تتر پشتیبانی می‌شود.");
      return;
    }
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
    submitOrder(method);
  }

  function chooseOnlineProvider(provider) {
    setBankInfo("");
    setReceiveMethod(provider === "hesabpay" ? "online_hesabpay" : "online_azizi");
    setStepIdx(7);
  }

  async function submitOrder(methodOverride) {
    const method = methodOverride || receiveMethod;
    const proof = txProofUrl || txProof.trim();
    if (!proof) {
      showError("لطفاً کد تراکنش (TxID) یا رسید تراکنش را وارد کنید.");
      return;
    }
    if (method?.startsWith("online_") && !bankInfo.trim()) {
      showError(method === "online_hesabpay" ? "لطفاً شماره حساب‌پی خود را وارد کنید." : "لطفاً اطلاعات حساب عزیزی بانک خود را وارد کنید.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.createSellOrder({
        amount: parseFloat(amount),
        exchange_name: finalExchange,
        network: finalNetwork,
        tx_proof: proof,
        receive_method: method,
        bank_info: method?.startsWith("online_") ? bankInfo.trim() : null,
      });
      setOrderCode(res.order_code);
      setStepIdx(8);
      hapticSuccess();
    } catch (err) {
      hapticError();
      if (err instanceof ApiError && err.code === "IDENTITY_VERIFICATION_REQUIRED") {
        onNeedVerification?.({ amount: parseFloat(amount), quote });
        return;
      }
      showError(err instanceof ApiError ? err.message : "ثبت سفارش ناموفق بود.");
    } finally {
      setSubmitting(false);
    }
  }

  const isHesabPay = receiveMethod === "online_hesabpay";

  return (
    <div className="app-shell">
      <div className="header">
        {step !== "done" ? (
          <button className="back-btn" onClick={goBack} aria-label="بازگشت">
            <CaretRight size={18} weight="bold" />
          </button>
        ) : (
          <div className="header-spacer" />
        )}
        <h1>
          <TrendDown size={18} className="header-icon" weight="bold" />
          فروش تتر
        </h1>
        <div className="header-spacer" />
      </div>

      {step !== "done" && (
        <div className="stepper">
          {STEPS.slice(0, -1).map((s, i) => (
            <div key={s} className={`dot ${i <= stepIdx ? "active" : ""}`} />
          ))}
        </div>
      )}

      {step === "amount" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label">چند USDT می‌خواهید بفروشید؟</label>
            <div className="amount-field">
              <input
                className="input num"
                type="number"
                inputMode="decimal"
                placeholder="مثال: 100"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <span className="amount-badge"><img src={TETHER_LOGO_URL} alt="USDT" /></span>
            </div>
          </div>
          <button className="btn btn-sell" onClick={fetchQuote} disabled={loadingQuote}>
            {loadingQuote ? <span className="spinner" /> : "محاسبهٔ نرخ"}
          </button>
        </div>
      )}

      {step === "quote" && quote && (
        <div className="card animate-in">
          <div className="quote-box">
            <div className="quote-row">
              <span>مقدار درخواستی</span>
              <span className="value num" style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                <img src={TETHER_LOGO_URL} alt="" className="tether-badge" />
                {Number(amount).toLocaleString()} USDT
              </span>
            </div>
            <div className="quote-row"><span>نرخ دالر (صرافی محلی)</span><span className="value num">{quote.usd_rate.toLocaleString()} افغانی</span></div>
            <div className="quote-total sell"><span className="label">مبلغ قابل دریافت</span><span className="amount num">{quote.total_afn.toLocaleString()} ؋</span></div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}>
            <button className="btn btn-sell" onClick={() => checkGateAndProceed(parseFloat(amount), quote)} disabled={checkingProfile}>
              {checkingProfile ? <span className="spinner" /> : <>درخواست تتر <ArrowRight size={16} weight="bold" /></>}
            </button>
            <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS")}><ChatCircleDots size={17} /> اطلاعات بیشتر</button>
          </div>
        </div>
      )}

      {step === "exchange" && (
        <div className="card animate-in">
          <label className="field-label">معاملهٔ خود را از کدام صرافی انجام می‌دهید؟</label>
          <div className="choice-row" style={{ marginTop: 4 }}>
            {EXCHANGES.map((ex) => <button key={ex} className={`choice-btn ${exchange === ex ? "selected" : ""}`} onClick={() => chooseExchange(ex)}>{ex}</button>)}
          </div>
          <div style={{ marginTop: 10 }}><button className={`choice-btn ${exchange === "other" ? "selected" : ""}`} style={{ width: "100%" }} onClick={() => chooseExchange("other")}>صرافی دیگر</button></div>
          {exchange === "other" && <input className="input" style={{ marginTop: 12 }} placeholder="نام صرافی" value={exchangeCustom} onChange={(e) => setExchangeCustom(e.target.value)} />}
        </div>
      )}

      {step === "network" && (
        <div className="card animate-in">
          <label className="field-label">شبکهٔ مورد نظر برای ارسال تتر را انتخاب کنید</label>
          <div className="choice-row cols-3" style={{ marginTop: 4 }}>
            {NETWORKS.map((n) => <button key={n} className={`choice-btn ${network === n ? "selected" : ""}`} onClick={() => chooseNetwork(n)}><NetworkIcon network={n} size={18} />{n}</button>)}
          </div>
          <div style={{ marginTop: 10 }}><button className={`choice-btn ${network === "other" ? "selected" : ""}`} style={{ width: "100%" }} onClick={() => chooseNetwork("other")}>شبکهٔ دیگر</button></div>
          {network === "other" && <input className="input" style={{ marginTop: 12 }} placeholder="نام شبکه" value={networkCustom} onChange={(e) => setNetworkCustom(e.target.value)} />}
        </div>
      )}

      {step === "deposit" && (
        <div className="card animate-in">
          <div className="notice" style={{ marginBottom: 14 }}>لطفاً مقدار <b className="num">{amount} USDT</b> را به آدرس زیر در شبکهٔ <b>{finalNetwork}</b> ارسال کنید:</div>
          <div className="info-box" style={{ marginBottom: 14 }}><CopyRow value={walletForNetwork} /></div>
          <div className="notice warn" style={{ marginBottom: 16 }}><Warning size={16} className="notice-icon" weight="fill" />پیش از ارسال، آدرس و شبکه را با دقت بررسی کنید؛ ارسال در شبکهٔ اشتباه ممکن است باعث از دست رفتن دارایی شود.</div>
          <button className="btn btn-sell" onClick={() => setStepIdx(5)}>تتر را ارسال کردم، ادامه</button>
        </div>
      )}

      {step === "txproof" && (
        <div className="card animate-in">
          <label className="field-label">کد تراکنش (TxID) را وارد کنید یا عکس رسید را بارگذاری کنید</label>
          <input className="input num" placeholder="TxID (اختیاری اگر عکس رسید بارگذاری می‌کنید)" value={txProof} onChange={(e) => setTxProof(e.target.value)} style={{ marginBottom: 12 }} />
          <label className={`upload-box ${txProofUrl ? "has-file" : ""}`}>
            <input type="file" accept="image/*" onChange={handleProofFile} />
            {txProofUploading ? <span className="spinner" style={{ borderTopColor: "var(--color-buy)" }} /> : txProofUrl ? <CheckCircle size={22} weight="fill" /> : <UploadSimple size={22} />}
            <span>{txProofUploading ? "در حال آپلود..." : txProofUrl ? "رسید بارگذاری شد" : "یا انتخاب تصویر رسید"}</span>
          </label>
          <button className="btn btn-sell" style={{ marginTop: 16 }} disabled={!txProof.trim() && !txProofUrl} onClick={() => setStepIdx(6)}>ادامه</button>
        </div>
      )}

      {step === "receive" && (
        <div className="card animate-in">
          <label className="field-label">می‌خواهید مبلغ فروش را چگونه دریافت کنید؟</label>
          <div className="choice-row" style={{ marginTop: 4 }}>
            <button className="choice-btn" onClick={() => chooseReceive("in_person")} disabled={submitting}>{submitting && receiveMethod === "in_person" ? <span className="spinner" /> : <Buildings size={16} />} حضوری</button>
            <button className={`choice-btn ${showOnlineProviders ? "selected" : ""}`} onClick={() => chooseReceive("online")} disabled={submitting}><Bank size={16} /> آنلاین (بانکی)</button>
          </div>

          {showOnlineProviders && (
            <div style={{ marginTop: 16 }}>
              <label className="field-label">روش دریافت آنلاین را انتخاب کنید</label>
              <div className="choice-row" style={{ marginTop: 6 }}>
                <button className="choice-btn" onClick={() => chooseOnlineProvider("azizi")}>
                  <img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={providerLogoStyle} />
                  عزیزی بانک
                </button>
                <button className="choice-btn" onClick={() => chooseOnlineProvider("hesabpay")}>
                  <img src={HESABPAY_LOGO_URL} alt="HesabPay" style={providerLogoStyle} />
                  حساب‌پی
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {step === "bank" && (
        <div className="card animate-in">
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
            <img src={isHesabPay ? HESABPAY_LOGO_URL : AZIZI_LOGO_URL} alt={isHesabPay ? "HesabPay" : "Azizi Bank"} style={{ ...providerLogoStyle, width: 54, height: 54 }} />
          </div>
          <div className="field">
            <label className="field-label">
              {isHesabPay ? "شماره حساب‌پی خود را وارد کنید" : "نام صاحب حساب و شمارهٔ حساب عزیزی بانک خود را وارد کنید"}
            </label>
            {isHesabPay ? (
              <input className="input num" inputMode="tel" placeholder="مثال: 0775123456" value={bankInfo} onChange={(e) => setBankInfo(e.target.value)} />
            ) : (
              <textarea className="input" rows={3} placeholder="نام صاحب حساب — شماره حساب" value={bankInfo} onChange={(e) => setBankInfo(e.target.value)} />
            )}
          </div>
          <button className="btn btn-sell" onClick={() => submitOrder(receiveMethod)} disabled={!bankInfo.trim() || submitting}>
            {submitting ? <span className="spinner" /> : "ثبت نهایی سفارش"}
          </button>
        </div>
      )}

      {step === "done" && (
        <div className="card success-screen animate-in">
          <div className="success-icon"><CheckCircle size={36} weight="fill" /></div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>سفارش فروش شما ثبت شد</div>
          <div className="code num">{orderCode}</div>
          <div className="notice" style={{ textAlign: "right" }}>پس از تأیید تراکنش توسط تیم ما، مبلغ ظرف کمتر از ۱ ساعت پرداخت خواهد شد.<br />پشتیبانی: @SJDPLUS</div>
          <button className="btn btn-secondary" onClick={() => navigate("orders")}><ClipboardText size={17} /> مشاهدهٔ سفارش‌های من</button>
          <button className="btn btn-outline" onClick={() => navigate("home")}><House size={17} /> بازگشت به منوی اصلی</button>
        </div>
      )}
    </div>
  );
}
