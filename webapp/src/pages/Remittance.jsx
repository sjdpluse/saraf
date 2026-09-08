import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Copy, GlobeHemisphereWest, PaperPlaneTilt, Receipt, Wallet } from "@phosphor-icons/react";
import { api } from "../lib/api";

const COUNTRIES = ["آمریکا", "کانادا", "آسترالیا", "آلمان", "فرانسه", "هالند", "سویدن", "بریتانیا", "امارات", "سایر"];
const RELATIONSHIPS = ["پدر/مادر", "همسر", "برادر/خواهر", "فرزند", "اقارب", "دوست", "سایر"];
const STATUS_LABELS = {
  awaiting_transfer: "منتظر انتقال کریپتو",
  transfer_submitted: "تراکنش ثبت شده",
  payout_ready: "آمادهٔ پرداخت نقدی",
  completed: "تکمیل شده",
  on_hold: "در حال بررسی",
  cancelled: "لغو شده",
};

function formatUsd(value) {
  return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function Remittance({ navigate, showError, onNeedProfile, onNeedVerification }) {
  const [config, setConfig] = useState(null);
  const [orders, setOrders] = useState([]);
  const [step, setStep] = useState("form");
  const [quote, setQuote] = useState(null);
  const [created, setCreated] = useState(null);
  const [txHash, setTxHash] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    sender_country: "آسترالیا",
    beneficiary_full_name: "",
    beneficiary_phone: "",
    beneficiary_province: "کابل",
    beneficiary_city: "کابل",
    beneficiary_address: "",
    relationship: "پدر/مادر",
    purpose: "مصارف خانواده",
    amount: "",
    asset: "USDT",
    network: "BEP20",
  });

  const assetConfig = useMemo(() => config?.assets?.find((x) => x.asset === form.asset), [config, form.asset]);

  useEffect(() => {
    Promise.all([api.getRemittanceConfig(), api.getMyRemittances()])
      .then(([c, list]) => {
        setConfig(c);
        setOrders(list || []);
        const first = c?.assets?.[0];
        if (first) {
          setForm((s) => ({ ...s, asset: first.asset, network: first.networks?.[0] || "" }));
        }
      })
      .catch((e) => showError(e.message));
  }, []);

  function setField(key, value) {
    setForm((s) => ({ ...s, [key]: value }));
  }

  useEffect(() => {
    if (!assetConfig?.networks?.length) return;
    if (!assetConfig.networks.includes(form.network)) setField("network", assetConfig.networks[0]);
  }, [assetConfig]);

  async function getQuote() {
    if (!config?.assets?.length) return showError("هنوز هیچ کیف پول حواله برای شبکه‌های پشتیبانی‌شده تنظیم نشده است.");
    const amount = Number(form.amount);
    if (!amount || amount <= 0) return showError("مقدار حواله را وارد کنید.");
    setBusy(true);
    try {
      const q = await api.getRemittanceQuote({ amount, asset: form.asset, network: form.network });
      setQuote(q);
      setStep("quote");
    } catch (e) {
      showError(e.message);
    } finally { setBusy(false); }
  }

  async function createOrder() {
    const required = ["beneficiary_full_name", "beneficiary_phone", "beneficiary_province", "beneficiary_city", "relationship", "purpose"];
    if (required.some((k) => !String(form[k] || "").trim())) return showError("تمام اطلاعات ضروری گیرنده را تکمیل کنید.");
    setBusy(true);
    try {
      const order = await api.createRemittance({ ...form, amount: Number(form.amount) });
      setCreated(order);
      setOrders((old) => [order, ...old.filter((x) => x.id !== order.id)]);
      setStep("transfer");
    } catch (e) {
      if (e.code === "IDENTITY_VERIFICATION_REQUIRED") {
        onNeedVerification?.({ asset: form.asset, amount: Number(form.amount) }, config?.identity_verification_threshold_usd);
      } else if (e.code === "BASIC_PROFILE_REQUIRED" || e.status === 403) {
        onNeedProfile?.({ asset: form.asset, amount: Number(form.amount) });
      } else showError(e.message);
    } finally { setBusy(false); }
  }

  async function submitTx() {
    if (!txHash.trim()) return showError("Tx Hash / Transaction ID را وارد کنید.");
    setBusy(true);
    try {
      const updated = await api.submitRemittanceTx(created.id, txHash.trim());
      setCreated(updated);
      setOrders((old) => old.map((x) => x.id === updated.id ? updated : x));
      setStep("done");
    } catch (e) { showError(e.message); }
    finally { setBusy(false); }
  }

  function copy(text) {
    navigator.clipboard?.writeText(String(text || ""));
  }

  return (
    <div className="app-shell">
      <div className="header">
        <button className="back-btn" onClick={() => navigate("home")}><ArrowRight size={18} /></button>
        <h1>حواله بین‌المللی</h1><div className="header-spacer" />
      </div>

      <div className="hero-card animate-in">
        <div className="hero-top">
          <div className="hero-row"><div className="hero-brand"><GlobeHemisphereWest size={28} weight="fill" /><span className="hero-brand-name">حواله با کریپتو</span></div></div>
          <div className="hero-tagline">کریپتو بفرستید؛ خانواده‌تان در افغانستان افغانی نقد دریافت کند.</div>
        </div>
      </div>

      {step === "form" && <div className="card animate-in">
        <div className="section-title">اطلاعات حواله</div>
        {!config?.assets?.length && config && <div className="notice warn">برای فعال‌شدن حواله، حداقل یک آدرس دریافت در تنظیمات سرور اضافه کنید.</div>}
        <div className="field"><label className="field-label">کشور فرستنده</label><select className="input" value={form.sender_country} onChange={(e) => setField("sender_country", e.target.value)}>{COUNTRIES.map((x) => <option key={x}>{x}</option>)}</select></div>
        <div className="field"><label className="field-label">مقدار {form.asset}</label><input className="input num" type="number" min="0" step="any" value={form.amount} onChange={(e) => setField("amount", e.target.value)} placeholder={form.asset === "BTC" ? "مثلاً 0.01" : form.asset === "ETH" ? "مثلاً 0.2" : "مثلاً 500"} /></div>
        <div className="notice">محدوده حواله بر اساس ارزش دلاری محاسبه می‌شود: {config?.min_usd || 10} تا {config?.max_usd || 10000} USD.</div>
        <div className="remit-grid">
          <div className="field"><label className="field-label">دارایی</label><select className="input" value={form.asset} onChange={(e) => setField("asset", e.target.value)}>{(config?.assets || []).map((x) => <option key={x.asset} value={x.asset}>{x.asset} — {x.name_fa || x.asset}</option>)}</select></div>
          <div className="field"><label className="field-label">شبکه</label><select className="input" value={form.network} onChange={(e) => setField("network", e.target.value)}>{(assetConfig?.networks || []).map((x) => <option key={x}>{x}</option>)}</select></div>
        </div>

        <div className="section-title" style={{ marginTop: 8 }}>گیرنده در افغانستان</div>
        <div className="field"><input className="input" value={form.beneficiary_full_name} onChange={(e) => setField("beneficiary_full_name", e.target.value)} placeholder="نام و تخلص گیرنده" /></div>
        <div className="field"><input className="input" value={form.beneficiary_phone} onChange={(e) => setField("beneficiary_phone", e.target.value)} placeholder="شماره تماس گیرنده" /></div>
        <div className="remit-grid"><div className="field"><input className="input" value={form.beneficiary_province} onChange={(e) => setField("beneficiary_province", e.target.value)} placeholder="ولایت" /></div><div className="field"><input className="input" value={form.beneficiary_city} onChange={(e) => setField("beneficiary_city", e.target.value)} placeholder="شهر" /></div></div>
        <div className="field"><input className="input" value={form.beneficiary_address} onChange={(e) => setField("beneficiary_address", e.target.value)} placeholder="آدرس (اختیاری)" /></div>
        <div className="field"><label className="field-label">نسبت با گیرنده</label><select className="input" value={form.relationship} onChange={(e) => setField("relationship", e.target.value)}>{RELATIONSHIPS.map((x) => <option key={x}>{x}</option>)}</select></div>
        <div className="field"><input className="input" value={form.purpose} onChange={(e) => setField("purpose", e.target.value)} placeholder="هدف حواله" /></div>
        <button className="btn btn-primary" disabled={busy || !config?.assets?.length} onClick={getQuote}>{busy ? "در حال محاسبه..." : "محاسبه مبلغ قابل دریافت"}</button>
      </div>}

      {step === "quote" && quote && <div className="card animate-in">
        <div className="section-title"><Receipt size={20} /> بررسی نهایی</div>
        <div className="quote-box">
          <div className="quote-row"><span>ارسال</span><span className="value num">{quote.crypto_amount} {quote.asset}</span></div>
          <div className="quote-row"><span>قیمت {quote.asset}</span><span className="value num">${formatUsd(quote.asset_price_usd)}</span></div>
          <div className="quote-row"><span>ارزش حواله</span><span className="value num">${formatUsd(quote.usd_value)}</span></div>
          <div className="quote-row"><span>نرخ دالر</span><span className="value num">{Number(quote.usd_rate).toLocaleString()} AFN</span></div>
          <div className="quote-row"><span>کارمزد خدمت</span><span className="value num">{quote.fee_percent}%</span></div>
          <div className="quote-total buy"><span className="label">دریافت خانواده</span><span className="amount num">{Number(quote.payout_afn).toLocaleString()} AFN</span></div>
        </div>
        <div style={{ height: 12 }} />
        <button className="btn btn-primary" disabled={busy} onClick={createOrder}>{busy ? "در حال ثبت..." : "ثبت حواله"}</button>
        <div style={{ height: 8 }} /><button className="btn btn-secondary" onClick={() => setStep("form")}>ویرایش اطلاعات</button>
      </div>}

      {step === "transfer" && created && <div className="card animate-in">
        <div className="section-title"><Wallet size={20} /> انتقال کریپتو</div>
        <div className="notice warn">فقط {created.asset} روی شبکه {created.network} به این آدرس ارسال کنید. انتقال روی شبکه اشتباه قابل بازیابی تضمینی نیست.</div>
        <div className="info-box" style={{ marginTop: 12 }}><div className="row"><span className="label">آدرس</span><span className="value"><code>{created.deposit_wallet}</code><button className="copy-btn" onClick={() => copy(created.deposit_wallet)}><Copy size={16} /></button></span></div><div className="row"><span className="label">مقدار دقیق</span><span className="value num">{created.crypto_amount} {created.asset}</span></div></div>
        <div className="field" style={{ marginTop: 16 }}><label className="field-label">Tx Hash / Transaction ID</label><input className="input num" value={txHash} onChange={(e) => setTxHash(e.target.value)} placeholder="پس از ارسال، شناسه تراکنش را وارد کنید" /></div>
        <button className="btn btn-primary" disabled={busy} onClick={submitTx}><PaperPlaneTilt size={18} /> {busy ? "در حال ثبت..." : "ثبت تراکنش"}</button>
      </div>}

      {step === "done" && created && <div className="card animate-in">
        <div className="section-title">درخواست ثبت شد</div>
        <div className="notice">تراکنش برای بررسی ارسال شد. پس از تایید دریافت کریپتو، کد دریافت نقدی برای شما ارسال می‌شود.</div>
        <div className="info-box" style={{ marginTop: 12 }}><div className="row"><span className="label">کد حواله</span><span className="value num">{created.order_code}</span></div><div className="row"><span className="label">وضعیت</span><span className="value">{STATUS_LABELS[created.status] || created.status}</span></div></div>
      </div>}

      {orders.length > 0 && <div className="card animate-in">
        <div className="section-title">حواله‌های من</div>
        {orders.slice(0, 8).map((o) => <div key={o.id} className="remit-order-row">
          <div className="row-text"><div className="row-title num">{o.order_code}</div><div className="row-subtitle">{o.beneficiary_full_name} · {Number(o.payout_afn).toLocaleString()} AFN · {o.crypto_amount} {o.asset}</div>{o.status === "payout_ready" && o.pickup_code && <div className="remit-pickup">کد دریافت: <strong className="num">{o.pickup_code}</strong></div>}</div>
          <div className={`status-badge status-${o.status === "completed" ? "completed" : o.status === "cancelled" ? "cancelled" : o.status === "payout_ready" ? "confirmed" : "pending"}`}>{STATUS_LABELS[o.status] || o.status}</div>
        </div>)}
      </div>}
    </div>
  );
}
