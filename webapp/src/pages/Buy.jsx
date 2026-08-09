import { useState } from "react";
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
} from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { getTelegramUser, hapticSuccess, hapticError } from "../lib/telegram";
import CopyRow from "../components/CopyRow";

const EXCHANGES = ["Binance", "Bybit", "OKX", "KuCoin"];
const NETWORKS = ["TRC20", "ERC20", "BEP20"];

const STEPS = ["amount", "payment", "receipt", "exchange", "network", "wallet", "phone", "done"];

export default function Buy({ navigate, showError }) {
  const [stepIdx, setStepIdx] = useState(0);
  const [amount, setAmount] = useState("");
  const [quote, setQuote] = useState(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState(null);
  const [receiptUrl, setReceiptUrl] = useState(null);
  const [receiptUploading, setReceiptUploading] = useState(false);
  const [exchange, setExchange] = useState(null);
  const [exchangeCustom, setExchangeCustom] = useState("");
  const [network, setNetwork] = useState(null);
  const [networkCustom, setNetworkCustom] = useState("");
  const [walletAddress, setWalletAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [orderCode, setOrderCode] = useState(null);

  const step = STEPS[stepIdx];

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

  function choosePayment(method) {
    setPaymentMethod(method);
    setStepIdx(method === "online" ? 2 : 3); // آنلاین -> رسید | حضوری -> مستقیم صرافی
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
    setStepIdx(4);
  }

  function chooseNetwork(net) {
    setNetwork(net);
    setStepIdx(5);
  }

  async function submitOrder() {
    if (!walletAddress.trim()) {
      showError("لطفاً آدرس ولت را وارد کنید.");
      return;
    }
    if (!phone.trim() || phone.trim().length < 7) {
      showError("لطفاً شمارهٔ تماس معتبر وارد کنید.");
      return;
    }
    const finalExchange = exchange === "other" ? exchangeCustom.trim() : exchange;
    const finalNetwork = network === "other" ? networkCustom.trim() : network;

    setSubmitting(true);
    try {
      const res = await api.createBuyOrder({
        amount: parseFloat(amount),
        phone: phone.trim(),
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
      showError(err instanceof ApiError ? err.message : "ثبت سفارش ناموفق بود.");
    } finally {
      setSubmitting(false);
    }
  }

  const tgUser = getTelegramUser();

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
          {STEPS.slice(0, 7).map((s, i) => (
            <div key={s} className={`dot ${i <= stepIdx ? "active" : ""}`} />
          ))}
        </div>
      )}

      {step === "amount" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label">چند USDT می‌خواهید بخرید؟</label>
            <input
              className="input num"
              type="number"
              inputMode="decimal"
              placeholder="مثال: 100"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
          <button className="btn btn-buy" onClick={fetchQuote} disabled={loadingQuote}>
            {loadingQuote ? <span className="spinner" /> : "محاسبهٔ نرخ"}
          </button>
        </div>
      )}

      {step === "payment" && quote && (
        <>
          <div className="card animate-in">
            <div className="quote-box">
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
          </div>

          <div className="card animate-in">
            <label className="field-label">روش پرداخت خود را انتخاب کنید</label>
            <div className="choice-row" style={{ marginTop: 4 }}>
              <button className="choice-btn" onClick={() => choosePayment("in_person")}>
                <Buildings size={16} /> حضوری
              </button>
              <button className="choice-btn" onClick={() => choosePayment("online")}>
                <Bank size={16} /> آنلاین (بانکی)
              </button>
            </div>
          </div>
        </>
      )}

      {step === "receipt" && (
        <div className="card animate-in">
          <div className="info-box" style={{ marginBottom: 16 }}>
            <CopyRow label="بانک" value="Azizi Bank" />
            <CopyRow label="صاحب حساب" value="SAJAD ALI MOHAMMADI" />
            <CopyRow label="شماره حساب" value="000601102302066" />
          </div>
          <label className="field-label">پس از واریز، عکس رسید بانکی را بارگذاری کنید</label>
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
            onClick={() => setStepIdx(3)}
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
          <button className="btn btn-buy" onClick={() => setStepIdx(6)} disabled={!walletAddress.trim()}>
            ادامه
          </button>
        </div>
      )}

      {step === "phone" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label">شمارهٔ تماس شما (برای اعتبارسنجی و هماهنگی سفارش)</label>
            <input
              className="input num"
              type="tel"
              placeholder={tgUser ? "+93 7XX XXX XXX" : "شمارهٔ تماس"}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          <button className="btn btn-buy" onClick={submitOrder} disabled={submitting}>
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
