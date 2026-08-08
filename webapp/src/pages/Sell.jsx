import { useState } from "react";
import { api, ApiError } from "../lib/api";
import { hapticSuccess, hapticError } from "../lib/telegram";

const EXCHANGES = ["Binance", "Bybit", "OKX", "KuCoin"];
const NETWORKS = ["TRC20", "ERC20", "BEP20"];
const DEPOSIT_WALLETS = { BEP20: "0x4c49Ff39798C564A01F5fdEcB7E335a178f781BA" };

const STEPS = ["amount", "exchange", "network", "deposit", "txproof", "receive", "bank", "phone", "done"];

export default function Sell({ navigate, showError }) {
  const [stepIdx, setStepIdx] = useState(0);
  const [amount, setAmount] = useState("");
  const [quote, setQuote] = useState(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [exchange, setExchange] = useState(null);
  const [exchangeCustom, setExchangeCustom] = useState("");
  const [network, setNetwork] = useState(null);
  const [networkCustom, setNetworkCustom] = useState("");
  const [txProof, setTxProof] = useState("");
  const [txProofUploading, setTxProofUploading] = useState(false);
  const [txProofUrl, setTxProofUrl] = useState(null);
  const [receiveMethod, setReceiveMethod] = useState(null);
  const [bankInfo, setBankInfo] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [orderCode, setOrderCode] = useState(null);

  const step = STEPS[stepIdx];
  const finalNetwork = network === "other" ? networkCustom.trim() : network;
  const finalExchange = exchange === "other" ? exchangeCustom.trim() : exchange;
  const walletForNetwork = finalNetwork ? DEPOSIT_WALLETS[finalNetwork.toUpperCase()] : null;

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

  function chooseExchange(ex) {
    setExchange(ex);
    setStepIdx(2);
  }

  function chooseNetwork(net) {
    setNetwork(net);
    const wallet = DEPOSIT_WALLETS[net.toUpperCase()];
    if (net !== "other" && !wallet) {
      showError("در حال حاضر فقط شبکهٔ BEP20 برای دریافت تتر پشتیبانی می‌شود.");
      return;
    }
    setStepIdx(3);
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
    setReceiveMethod(method);
    setStepIdx(method === "online" ? 6 : 7);
  }

  async function submitOrder() {
    const proof = txProofUrl || txProof.trim();
    if (!proof) {
      showError("لطفاً کد تراکنش (TxID) یا رسید تراکنش را وارد کنید.");
      return;
    }
    if (!phone.trim() || phone.trim().length < 7) {
      showError("لطفاً شمارهٔ تماس معتبر وارد کنید.");
      return;
    }
    if (receiveMethod === "online" && !bankInfo.trim()) {
      showError("لطفاً اطلاعات بانکی خود را وارد کنید.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.createSellOrder({
        amount: parseFloat(amount),
        phone: phone.trim(),
        exchange_name: finalExchange,
        network: finalNetwork,
        tx_proof: proof,
        receive_method: receiveMethod,
        bank_info: receiveMethod === "online" ? bankInfo.trim() : null,
      });
      setOrderCode(res.order_code);
      setStepIdx(8);
      hapticSuccess();
    } catch (err) {
      hapticError();
      showError(err instanceof ApiError ? err.message : "ثبت سفارش ناموفق بود.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="header">
        <button className="back-btn" onClick={goBack}>
          › {step === "done" ? "" : "بازگشت"}
        </button>
        <h1>🔴 فروش تتر</h1>
      </div>

      {step !== "done" && (
        <div className="stepper">
          {STEPS.slice(0, 8).map((s, i) => (
            <div key={s} className={`dot ${i <= stepIdx ? "active" : ""}`} />
          ))}
        </div>
      )}

      {step === "amount" && (
        <div className="card">
          <div className="field">
            <label className="field-label">چند USDT می‌خواهید بفروشید؟</label>
            <input
              className="input"
              type="number"
              inputMode="decimal"
              placeholder="مثال: 100"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" onClick={fetchQuote} disabled={loadingQuote}>
            {loadingQuote ? <span className="spinner" /> : "محاسبهٔ نرخ"}
          </button>
        </div>
      )}

      {step === "exchange" && quote && (
        <>
          <div className="card">
            <div className="quote-box">
              <div className="quote-row">
                <span>نرخ دالر (صرافی محلی)</span>
                <span className="value">{quote.usd_rate.toLocaleString()} افغانی</span>
              </div>
              <div className="quote-total">
                <span className="label">مبلغ قابل دریافت</span>
                <span className="amount">{quote.total_afn.toLocaleString()} ؋</span>
              </div>
            </div>
          </div>
          <div className="card">
            <label className="field-label">معاملهٔ خود را از کدام صرافی انجام می‌دهید؟</label>
            <div className="choice-row" style={{ marginTop: 4 }}>
              {EXCHANGES.map((ex) => (
                <button key={ex} className="choice-btn" onClick={() => chooseExchange(ex)}>
                  {ex}
                </button>
              ))}
            </div>
            <div style={{ marginTop: 10 }}>
              <button className="choice-btn" style={{ width: "100%" }} onClick={() => chooseExchange("other")}>
                ✏️ صرافی دیگر
              </button>
            </div>
            {exchange === "other" && (
              <input
                className="input"
                style={{ marginTop: 12 }}
                placeholder="نام صرافی"
                value={exchangeCustom}
                onChange={(e) => setExchangeCustom(e.target.value)}
              />
            )}
          </div>
        </>
      )}

      {step === "network" && (
        <div className="card">
          <label className="field-label">شبکهٔ مورد نظر برای ارسال تتر را انتخاب کنید</label>
          <div className="choice-row cols-3" style={{ marginTop: 4 }}>
            {NETWORKS.map((n) => (
              <button key={n} className="choice-btn" onClick={() => chooseNetwork(n)}>
                {n}
              </button>
            ))}
          </div>
          <div style={{ marginTop: 10 }}>
            <button className="choice-btn" style={{ width: "100%" }} onClick={() => chooseNetwork("other")}>
              ✏️ شبکهٔ دیگر
            </button>
          </div>
          {network === "other" && (
            <input
              className="input"
              style={{ marginTop: 12 }}
              placeholder="نام شبکه"
              value={networkCustom}
              onChange={(e) => setNetworkCustom(e.target.value)}
            />
          )}
        </div>
      )}

      {step === "deposit" && (
        <div className="card">
          <div className="notice" style={{ marginBottom: 14 }}>
            لطفاً مقدار <b>{amount} USDT</b> را به آدرس زیر در شبکهٔ <b>{finalNetwork}</b> ارسال
            کنید:
          </div>
          <div className="info-box" style={{ marginBottom: 14 }}>
            <div className="row">
              <span style={{ wordBreak: "break-all" }} className="value">
                {walletForNetwork}
              </span>
            </div>
          </div>
          <div className="notice warn" style={{ marginBottom: 16 }}>
            ⚠️ پیش از ارسال، آدرس و شبکه را با دقت بررسی کنید؛ ارسال در شبکهٔ اشتباه ممکن است
            باعث از دست رفتن دارایی شود.
          </div>
          <button className="btn btn-primary" onClick={() => setStepIdx(4)}>
            تتر را ارسال کردم، ادامه
          </button>
        </div>
      )}

      {step === "txproof" && (
        <div className="card">
          <label className="field-label">کد تراکنش (TxID) را وارد کنید یا عکس رسید را بارگذاری کنید</label>
          <input
            className="input"
            placeholder="TxID (اختیاری اگر عکس رسید بارگذاری می‌کنید)"
            value={txProof}
            onChange={(e) => setTxProof(e.target.value)}
            style={{ direction: "ltr", textAlign: "left", marginBottom: 12 }}
          />
          <label className={`upload-box ${txProofUrl ? "has-file" : ""}`}>
            <input type="file" accept="image/*" onChange={handleProofFile} />
            {txProofUploading ? "در حال آپلود..." : txProofUrl ? "✅ رسید بارگذاری شد" : "📎 یا انتخاب تصویر رسید"}
          </label>
          <button
            className="btn btn-primary"
            style={{ marginTop: 16 }}
            disabled={!txProof.trim() && !txProofUrl}
            onClick={() => setStepIdx(5)}
          >
            ادامه
          </button>
        </div>
      )}

      {step === "receive" && (
        <div className="card">
          <label className="field-label">می‌خواهید مبلغ فروش را چگونه دریافت کنید؟</label>
          <div className="choice-row" style={{ marginTop: 4 }}>
            <button className="choice-btn" onClick={() => chooseReceive("in_person")}>
              🏢 حضوری
            </button>
            <button className="choice-btn" onClick={() => chooseReceive("online")}>
              🏦 آنلاین (بانکی)
            </button>
          </div>
        </div>
      )}

      {step === "bank" && (
        <div className="card">
          <div className="field">
            <label className="field-label">نام صاحب حساب و شمارهٔ حساب بانکی خود را وارد کنید</label>
            <textarea
              className="input"
              rows={3}
              placeholder="احمد احمدی — 0123456789 — بانک ..."
              value={bankInfo}
              onChange={(e) => setBankInfo(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" onClick={() => setStepIdx(7)} disabled={!bankInfo.trim()}>
            ادامه
          </button>
        </div>
      )}

      {step === "phone" && (
        <div className="card">
          <div className="field">
            <label className="field-label">شمارهٔ تماس شما (برای اعتبارسنجی و هماهنگی سفارش)</label>
            <input
              className="input"
              type="tel"
              placeholder="+93 7XX XXX XXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              style={{ direction: "ltr", textAlign: "left" }}
            />
          </div>
          <button className="btn btn-primary" onClick={submitOrder} disabled={submitting}>
            {submitting ? <span className="spinner" /> : "✅ ثبت نهایی سفارش"}
          </button>
        </div>
      )}

      {step === "done" && (
        <div className="card success-screen">
          <div className="icon">✅</div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>سفارش فروش شما ثبت شد</div>
          <div className="code">{orderCode}</div>
          <div className="notice">
            پس از تأیید تراکنش توسط تیم ما، مبلغ ظرف کمتر از ۱ ساعت پرداخت خواهد شد.
            <br />
            🆘 پشتیبانی: @SJDPLUS
          </div>
          <button className="btn btn-secondary" onClick={() => navigate("orders")}>
            مشاهدهٔ سفارش‌های من
          </button>
          <button className="btn btn-outline" onClick={() => navigate("home")}>
            بازگشت به منوی اصلی
          </button>
        </div>
      )}
    </div>
  );
}
