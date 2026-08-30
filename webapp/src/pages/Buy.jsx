import { useEffect, useState } from "react";
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
  ArrowRight,
} from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { hapticSuccess, hapticError, openTelegramChat } from "../lib/telegram";
import CopyRow from "../components/CopyRow";
import { TETHER_LOGO_URL } from "../lib/brand";
import NetworkIcon from "../components/NetworkIcon";

const EXCHANGES = ["Binance", "Bybit", "OKX", "KuCoin"];
const NETWORKS = ["TRC20", "ERC20", "BEP20"];

const AZIZI_LOGO_URL = "https://i.postimg.cc/Y2FRCN2z/azizi.png";
const HESABPAY_LOGO_URL = "https://i.postimg.cc/63khhqcm/hesab.png";
const HESABPAY_QR_URL = "https://i.postimg.cc/D058wYSQ/Hesab.jpg";
const HESABPAY_PHONE = "0775146747";

const STEPS = ["amount", "quote", "payment", "receipt", "exchange", "network", "wallet", "done"];

const providerLogoStyle = {
  width: 34,
  height: 34,
  objectFit: "contain",
  borderRadius: 8,
  background: "#fff",
};

export default function Buy({ navigate, showError, resumeState, onResumeConsumed, onNeedProfile, onNeedVerification }) {
  const [stepIdx, setStepIdx] = useState(0);
  const [amount, setAmount] = useState("");
  const [quote, setQuote] = useState(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [checkingProfile, setCheckingProfile] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState(null);
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
  const [submitting, setSubmitting] = useState(false);
  const [orderCode, setOrderCode] = useState(null);

  const step = STEPS[stepIdx];

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
      const q = await api.getQuote("buy", amt);
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

  function choosePayment(method) {
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
      const info = await api.getPaymentInfo();
      setPaymentInfo(info);
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
    setStepIdx(5);
  }

  function chooseNetwork(net) {
    setNetwork(net);
    setStepIdx(6);
  }

  async function submitOrder() {
    if (!walletAddress.trim()) {
      showError("لطفاً آدرس ولت را وارد کنید.");
      return;
    }
    const finalExchange = exchange === "other" ? exchangeCustom.trim() : exchange;
    const finalNetwork = network === "other" ? networkCustom.trim() : network;

    setSubmitting(true);
    try {
      const res = await api.createBuyOrder({
        amount: parseFloat(amount),
        payment_method: paymentMethod,
        exchange_name: finalExchange || null,
        network: finalNetwork,
        wallet_address: walletAddress.trim(),
        receipt_url: receiptUrl,
      });
      setOrderCode(res.order_code);
      setStepIdx(7);
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

  const isHesabPay = paymentMethod === "online_hesabpay";

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
          <TrendUp size={18} className="header-icon" weight="bold" />
          خرید تتر
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
            <label className="field-label">چند USDT می‌خواهید بخرید؟</label>
            <div className="amount-field">
              <input
                className="input num"
                type="number"
                inputMode="decimal"
                placeholder="مثال: 100"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <span className="amount-badge">
                <img src={TETHER_LOGO_URL} alt="USDT" />
              </span>
            </div>
          </div>
          <button className="btn btn-buy" onClick={fetchQuote} disabled={loadingQuote}>
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
            <div className="quote-row">
              <span>نرخ دالر (صرافی محلی)</span>
              <span className="value num">{quote.usd_rate.toLocaleString()} افغانی</span>
            </div>
            <div className="quote-row">
              <span>مبلغ پایه</span>
              <span className="value num">{quote.base_afn.toLocaleString()} افغانی</span>
            </div>
            <div className="quote-row">
              <span>کارمزد ({quote.fee_percent}٪)</span>
              <span className="value num">{quote.fee_afn.toLocaleString()} افغانی</span>
            </div>
            <div className="quote-total buy">
              <span className="label">مبلغ نهایی قابل پرداخت</span>
              <span className="amount num">{quote.total_afn.toLocaleString()} ؋</span>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}>
            <button className="btn btn-buy" onClick={() => checkGateAndProceed(parseFloat(amount), quote)} disabled={checkingProfile}>
              {checkingProfile ? <span className="spinner" /> : <>درخواست تتر <ArrowRight size={16} weight="bold" /></>}
            </button>
            <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS")}>
              <ChatCircleDots size={17} /> اطلاعات بیشتر
            </button>
          </div>
        </div>
      )}

      {step === "payment" && (
        <div className="card animate-in">
          <label className="field-label">روش پرداخت خود را انتخاب کنید</label>
          <div className="choice-row" style={{ marginTop: 4 }}>
            <button className="choice-btn" onClick={() => choosePayment("in_person")} disabled={loadingPaymentInfo}>
              <Buildings size={16} /> حضوری
            </button>
            <button className={`choice-btn ${showOnlineProviders ? "selected" : ""}`} onClick={() => choosePayment("online")} disabled={loadingPaymentInfo}>
              <Bank size={16} /> آنلاین (بانکی)
            </button>
          </div>

          {showOnlineProviders && (
            <div style={{ marginTop: 16 }}>
              <label className="field-label">روش پرداخت آنلاین را انتخاب کنید</label>
              <div className="choice-row" style={{ marginTop: 6 }}>
                <button className="choice-btn" onClick={() => chooseOnlineProvider("azizi")} disabled={loadingPaymentInfo}>
                  {loadingPaymentInfo ? <span className="spinner" /> : <img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={providerLogoStyle} />}
                  عزیزی بانک
                </button>
                <button className="choice-btn" onClick={() => chooseOnlineProvider("hesabpay")} disabled={loadingPaymentInfo}>
                  <img src={HESABPAY_LOGO_URL} alt="HesabPay" style={providerLogoStyle} />
                  حساب‌پی
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {step === "receipt" && (
        <div className="card animate-in">
          {isHesabPay ? (
            <>
              <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
                <img src={HESABPAY_LOGO_URL} alt="HesabPay" style={{ ...providerLogoStyle, width: 54, height: 54 }} />
              </div>
              <div className="info-box" style={{ marginBottom: 14, textAlign: "center" }}>
                <img
                  src={HESABPAY_QR_URL}
                  alt="QR حساب‌پی"
                  style={{ width: "min(100%, 260px)", borderRadius: 14, display: "block", margin: "0 auto 14px" }}
                />
                <CopyRow label="شماره حساب‌پی" value={HESABPAY_PHONE} />
              </div>
              <div className="notice" style={{ marginBottom: 16 }}>
                مبلغ سفارش را از طریق QR یا شمارهٔ بالا در حساب‌پی پرداخت کنید، سپس تصویر رسید را بارگذاری نمایید.
              </div>
            </>
          ) : (
            <>
              <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
                <img src={AZIZI_LOGO_URL} alt="Azizi Bank" style={{ ...providerLogoStyle, width: 54, height: 54 }} />
              </div>
              <div className="info-box" style={{ marginBottom: 16 }}>
                {paymentInfo ? (
                  <>
                    <CopyRow label="بانک" value={paymentInfo.bank_name} />
                    <CopyRow label="صاحب حساب" value={paymentInfo.bank_account_holder} />
                    <CopyRow label="شماره حساب" value={paymentInfo.bank_account_number} />
                  </>
                ) : (
                  <div className="skeleton skeleton-order-card" style={{ height: 76 }} />
                )}
              </div>
            </>
          )}

          <label className="field-label">
            پس از پرداخت، عکس رسید {isHesabPay ? "حساب‌پی" : "عزیزی بانک"} را بارگذاری کنید
          </label>
          <label className={`upload-box ${receiptUrl ? "has-file" : ""}`}>
            <input type="file" accept="image/*" onChange={handleReceiptFile} />
            {receiptUploading ? (
              <span className="spinner" style={{ borderTopColor: "var(--color-buy)" }} />
            ) : receiptUrl ? (
              <CheckCircle size={22} weight="fill" />
            ) : (
              <UploadSimple size={22} />
            )}
            <span>{receiptUploading ? "در حال آپلود..." : receiptUrl ? "رسید بارگذاری شد" : "انتخاب تصویر رسید"}</span>
          </label>
          <button
            className="btn btn-buy"
            style={{ marginTop: 16 }}
            disabled={!receiptUrl}
            onClick={() => setStepIdx(4)}
          >
            ادامه
          </button>
        </div>
      )}

      {step === "exchange" && (
        <div className="card animate-in">
          <label className="field-label">تتر خود را در کدام صرافی یا کیف پول می‌خواهید دریافت کنید؟</label>
          <div className="choice-row" style={{ marginTop: 4 }}>
            {EXCHANGES.map((ex) => (
              <button
                key={ex}
                className={`choice-btn ${exchange === ex ? "selected" : ""}`}
                onClick={() => chooseExchange(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
          <div style={{ marginTop: 10 }}>
            <button
              className={`choice-btn ${exchange === "other" ? "selected" : ""}`}
              style={{ width: "100%" }}
              onClick={() => chooseExchange("other")}
            >
              کیف پول شخصی / دیگر
            </button>
          </div>
          {exchange === "other" && (
            <input
              className="input"
              style={{ marginTop: 12 }}
              placeholder="نام صرافی یا کیف پول"
              value={exchangeCustom}
              onChange={(e) => setExchangeCustom(e.target.value)}
            />
          )}
        </div>
      )}

      {step === "network" && (
        <div className="card animate-in">
          <label className="field-label">شبکهٔ مورد نظر برای دریافت تتر را انتخاب کنید</label>
          <div className="choice-row cols-3" style={{ marginTop: 4 }}>
            {NETWORKS.map((n) => (
              <button
                key={n}
                className={`choice-btn ${network === n ? "selected" : ""}`}
                onClick={() => chooseNetwork(n)}
              >
                <NetworkIcon network={n} size={18} />
                {n}
              </button>
            ))}
          </div>
          <div style={{ marginTop: 10 }}>
            <button
              className={`choice-btn ${network === "other" ? "selected" : ""}`}
              style={{ width: "100%" }}
              onClick={() => chooseNetwork("other")}
            >
              شبکهٔ دیگر
            </button>
          </div>
          {network === "other" && (
            <input
              className="input"
              style={{ marginTop: 12 }}
              placeholder="نام شبکه (مثال: Polygon)"
              value={networkCustom}
              onChange={(e) => setNetworkCustom(e.target.value)}
            />
          )}
        </div>
      )}

      {step === "wallet" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label">آدرس ولت (کیف پول) خودتان برای دریافت تتر</label>
            <input
              className="input num"
              placeholder="0x... یا T..."
              value={walletAddress}
              onChange={(e) => setWalletAddress(e.target.value)}
            />
          </div>
          <div className="notice warn" style={{ marginBottom: 14 }}>
            <Warning size={16} className="notice-icon" weight="fill" />
            لطفاً آدرس و شبکه را با دقت بررسی کنید؛ ارسال به آدرس یا شبکهٔ اشتباه ممکن
            است باعث از دست رفتن دارایی شود.
          </div>
          <button className="btn btn-buy" onClick={submitOrder} disabled={!walletAddress.trim() || submitting}>
            {submitting ? <span className="spinner" /> : "ثبت نهایی سفارش"}
          </button>
        </div>
      )}

      {step === "done" && (
        <div className="card success-screen animate-in">
          <div className="success-icon">
            <CheckCircle size={36} weight="fill" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>سفارش شما ثبت شد</div>
          <div className="code num">{orderCode}</div>
          <div className="notice" style={{ textAlign: "right" }}>
            تتر شما پس از تأیید پرداخت توسط تیم ما، ظرف کمتر از ۱ ساعت به آدرس اعلام‌شده
            واریز خواهد شد.
            <br />
            پشتیبانی: @SJDPLUS
          </div>
          <button className="btn btn-secondary" onClick={() => navigate("orders")}>
            <ClipboardText size={17} /> مشاهدهٔ سفارش‌های من
          </button>
          <button className="btn btn-outline" onClick={() => navigate("home")}>
            <House size={17} /> بازگشت به منوی اصلی
          </button>
        </div>
      )}
    </div>
  );
}
