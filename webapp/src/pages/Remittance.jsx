import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle,
  Copy,
  GlobeHemisphereWest,
  IdentificationCard,
  MapPin,
  PaperPlaneTilt,
  ShieldCheck,
  UploadSimple,
  User,
  Wallet,
} from "@phosphor-icons/react";
import { api } from "../lib/api";
import NetworkOption from "../components/NetworkOption";

const COUNTRIES = [
  "آسترالیا", "امارات متحده عربی", "آلمان", "امریکا", "بریتانیا", "ترکیه",
  "فرانسه", "کانادا", "هالند", "سویدن", "سایر",
];

const STEPS = ["sender", "asset", "network", "amount", "beneficiary", "identity", "address", "review", "transfer", "tx", "done"];
const STATUS_LABELS = {
  awaiting_transfer: "منتظر انتقال کریپتو",
  transfer_submitted: "در حال تأیید بلاکچین",
  payout_ready: "آماده پرداخت",
  completed: "تکمیل شده",
  on_hold: "در حال بررسی",
  cancelled: "لغو شده",
};

function fmt(value, digits = 2) {
  return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function AssetLogo({ item, size = 42 }) {
  const [failed, setFailed] = useState(false);
  if (!item || failed || !item.logo_url) {
    return <span className="remit-asset-fallback num" style={{ width: size, height: size }}>{item?.asset?.slice(0, 4) || "?"}</span>;
  }
  return <img className="remit-asset-logo" src={item.logo_url} alt={item.asset} style={{ width: size, height: size }} onError={() => setFailed(true)} />;
}

function StepHeader({ current }) {
  const active = Math.max(0, STEPS.indexOf(current));
  const visibleCount = 8;
  const visualActive = Math.min(active, visibleCount - 1);
  return (
    <div className="step-progress">
      {Array.from({ length: visibleCount }).map((_, i) => <span key={i} className={`step-dot ${i <= visualActive ? "active" : ""}`} />)}
    </div>
  );
}

function ReviewRow({ label, children }) {
  return <div className="quote-row"><span>{label}</span><span className="value">{children}</span></div>;
}

export default function Remittance({ navigate, showError, onNeedProfile, onNeedVerification }) {
  const [config, setConfig] = useState(null);
  const [orders, setOrders] = useState([]);
  const [step, setStep] = useState("sender");
  const [quote, setQuote] = useState(null);
  const [created, setCreated] = useState(null);
  const [txHash, setTxHash] = useState("");
  const [idFile, setIdFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    sender_full_name: "",
    sender_country: "",
    amount: "",
    asset: "",
    network: "",
    beneficiary_full_name: "",
    beneficiary_phone: "",
    beneficiary_province: "",
    beneficiary_city: "",
    beneficiary_address: "",
    beneficiary_id_document_path: "",
  });

  const assetConfig = useMemo(() => config?.assets?.find((x) => x.asset === form.asset), [config, form.asset]);
  const networkConfig = useMemo(() => assetConfig?.networks?.find((x) => x.code === form.network), [assetConfig, form.network]);
  const currentIndex = STEPS.indexOf(step);

  useEffect(() => {
    Promise.all([api.getRemittanceConfig(), api.getMyRemittances()])
      .then(([c, list]) => {
        setConfig(c);
        setOrders(list || []);
        const first = c?.assets?.[0];
        if (first) setForm((s) => ({ ...s, asset: first.asset, network: first.networks?.[0]?.code || "" }));
      })
      .catch((e) => showError(e.message));
  }, []);

  function setField(key, value) {
    setForm((s) => ({ ...s, [key]: value }));
  }

  function next(target) { setStep(target); window.scrollTo?.({ top: 0, behavior: "smooth" }); }
  function back() {
    if (step === "sender") return navigate("home");
    if (["transfer", "tx", "done"].includes(step)) return;
    const prev = STEPS[Math.max(0, currentIndex - 1)];
    next(prev);
  }

  function chooseAsset(item) {
    setForm((s) => ({ ...s, asset: item.asset, network: item.networks?.[0]?.code || "" }));
    setQuote(null);
    next("network");
  }

  async function calculateQuote() {
    const amount = Number(form.amount);
    if (!amount || amount <= 0) return showError("مقدار حواله را وارد کنید.");
    setBusy(true);
    try {
      const q = await api.getRemittanceQuote({ amount, asset: form.asset, network: form.network });
      setQuote(q);
      next("beneficiary");
    } catch (e) { showError(e.message); }
    finally { setBusy(false); }
  }

  async function uploadIdentity() {
    if (!idFile) return showError("تصویر تذکره گیرنده را انتخاب کنید.");
    setBusy(true);
    try {
      const result = await api.uploadRemittanceBeneficiaryId(idFile);
      setField("beneficiary_id_document_path", result.file_id);
      next("address");
    } catch (e) { showError(e.message); }
    finally { setBusy(false); }
  }

  async function createOrder() {
    setBusy(true);
    try {
      const order = await api.createRemittance({ ...form, amount: Number(form.amount) });
      setCreated(order);
      setOrders((old) => [order, ...old.filter((x) => x.id !== order.id)]);
      next("transfer");
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
      next("done");
    } catch (e) { showError(e.message); }
    finally { setBusy(false); }
  }

  function copy(text) { navigator.clipboard?.writeText(String(text || "")); }

  const invalidSender = form.sender_full_name.trim().length < 3 || !form.sender_country;
  const invalidBeneficiary = form.beneficiary_full_name.trim().length < 3 || form.beneficiary_phone.trim().length < 7;
  const invalidAddress = !form.beneficiary_province.trim() || !form.beneficiary_city.trim() || form.beneficiary_address.trim().length < 3;

  return (
    <div className="app-shell">
      <div className="header">
        <button className="back-btn" onClick={back} disabled={["transfer", "tx", "done"].includes(step)}><ArrowRight size={18} /></button>
        <h1>حواله بین‌المللی</h1><div className="header-spacer" />
      </div>
      <StepHeader current={step} />

      <div className="hero-card animate-in remit-hero">
        <div className="hero-top">
          <div className="hero-row"><div className="hero-brand"><GlobeHemisphereWest size={28} weight="fill" /><span className="hero-brand-name">International Remittance</span></div></div>
          <div className="hero-tagline">ارسال دارایی دیجیتال و پرداخت افغانی به گیرنده در افغانستان.</div>
        </div>
      </div>

      {step === "sender" && <div className="card animate-in">
        <div className="section-title"><User size={20} /> اطلاعات فرستنده</div>
        <div className="field"><label className="field-label">نام کامل فرستنده</label><input className="input" value={form.sender_full_name} onChange={(e) => setField("sender_full_name", e.target.value)} placeholder="نام و تخلص" autoComplete="name" /></div>
        <div className="field"><label className="field-label">کشور فرستنده</label><select className="input" value={form.sender_country} onChange={(e) => setField("sender_country", e.target.value)}><option value="" disabled>کشور را انتخاب کنید</option>{COUNTRIES.map((x) => <option key={x} value={x}>{x}</option>)}</select></div>
        <button className="btn btn-primary" disabled={invalidSender} onClick={() => next("asset")}>ادامه</button>
      </div>}

      {step === "asset" && <div className="card animate-in">
        <div className="section-title">انتخاب دارایی</div>
        <div className="section-hint">دارایی مورد نظر برای ارسال حواله را انتخاب کنید.</div>
        <div className="remit-assets">
          {(config?.assets || []).map((item) => <button key={item.asset} className={`remit-asset-card ${form.asset === item.asset ? "selected" : ""}`} onClick={() => chooseAsset(item)}>
            <AssetLogo item={item} />
            <span className="remit-asset-copy"><strong className="num">{item.asset}</strong><small>{item.name}</small></span>
            {form.asset === item.asset && <CheckCircle size={19} weight="fill" />}
          </button>)}
        </div>
        {!config?.assets?.length && config && <div className="notice warn">در حال حاضر هیچ دارایی برای حواله فعال نیست.</div>}
      </div>}

      {step === "network" && <div className="card animate-in">
        <div className="section-title">انتخاب شبکه</div>
        <div className="remit-selected-asset"><AssetLogo item={assetConfig} size={34} /><div><strong className="num">{form.asset}</strong><small>{assetConfig?.name}</small></div></div>
        <div className="network-list">{(assetConfig?.networks || []).map((item) => <NetworkOption key={item.code} item={item} selected={form.network === item.code} onClick={() => { setField("network", item.code); setQuote(null); }} />)}</div>
        <button className="btn btn-primary" disabled={!form.network} onClick={() => next("amount")}>ادامه</button>
      </div>}

      {step === "amount" && <div className="card animate-in">
        <div className="section-title">مقدار حواله</div>
        <div className="amount-input-wrap"><input className="input amount-input num" type="number" min="0" step="any" value={form.amount} onChange={(e) => { setField("amount", e.target.value); setQuote(null); }} placeholder={form.asset === "BTC" ? "0.01" : form.asset === "ETH" ? "0.20" : "500"} /><span>{form.asset}</span></div>
        <div className="notice">ارزش حواله باید بین {fmt(config?.min_usd || 10, 0)} تا {fmt(config?.max_usd || 10000, 0)} دالر امریکا (USD) باشد.</div>
        <button className="btn btn-primary" disabled={busy || !form.amount} onClick={calculateQuote}>{busy ? "در حال محاسبه..." : "محاسبه حواله"}</button>
      </div>}

      {step === "beneficiary" && <div className="card animate-in">
        <div className="section-title"><User size={20} /> اطلاعات گیرنده</div>
        <div className="field"><label className="field-label">نام کامل گیرنده</label><input className="input" value={form.beneficiary_full_name} onChange={(e) => setField("beneficiary_full_name", e.target.value)} placeholder="نام و تخلص مطابق تذکره" /></div>
        <div className="field"><label className="field-label">شماره تماس گیرنده</label><input className="input num" type="tel" value={form.beneficiary_phone} onChange={(e) => setField("beneficiary_phone", e.target.value)} placeholder="07XXXXXXXX" /></div>
        <button className="btn btn-primary" disabled={invalidBeneficiary} onClick={() => next("identity")}>ادامه</button>
      </div>}

      {step === "identity" && <div className="card animate-in">
        <div className="section-title"><IdentificationCard size={21} /> تذکره گیرنده</div>
        <div className="notice">تصویر واضح تذکره گیرنده را آپلود کنید. این فایل خصوصی است و برای تطبیق هویت هنگام پرداخت استفاده می‌شود.</div>
        <label className={`remit-upload ${idFile ? "ready" : ""}`}>
          <UploadSimple size={28} weight="duotone" />
          <strong>{idFile ? idFile.name : "انتخاب تصویر تذکره"}</strong>
          <small>JPG, PNG یا WEBP — حداکثر ۱۰ MB</small>
          <input type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => { setIdFile(e.target.files?.[0] || null); setField("beneficiary_id_document_path", ""); }} />
        </label>
        <button className="btn btn-primary" disabled={busy || !idFile} onClick={uploadIdentity}>{busy ? "در حال آپلود..." : "آپلود و ادامه"}</button>
      </div>}

      {step === "address" && <div className="card animate-in">
        <div className="section-title"><MapPin size={20} /> آدرس گیرنده</div>
        <div className="remit-grid"><div className="field"><label className="field-label">ولایت</label><input className="input" value={form.beneficiary_province} onChange={(e) => setField("beneficiary_province", e.target.value)} placeholder="مثلاً کابل" /></div><div className="field"><label className="field-label">شهر / ولسوالی</label><input className="input" value={form.beneficiary_city} onChange={(e) => setField("beneficiary_city", e.target.value)} placeholder="مثلاً کابل" /></div></div>
        <div className="field"><label className="field-label">آدرس کامل</label><textarea className="input remit-textarea" value={form.beneficiary_address} onChange={(e) => setField("beneficiary_address", e.target.value)} placeholder="ناحیه، منطقه، سرک یا نشانی دقیق" /></div>
        <button className="btn btn-primary" disabled={invalidAddress} onClick={() => next("review")}>بررسی نهایی</button>
      </div>}

      {step === "review" && quote && <div className="card animate-in">
        <div className="section-title"><ShieldCheck size={21} /> بررسی نهایی حواله</div>
        <div className="remit-review-section"><h3>فرستنده</h3><ReviewRow label="نام کامل">{form.sender_full_name}</ReviewRow><ReviewRow label="کشور">{form.sender_country}</ReviewRow></div>
        <div className="remit-review-section"><h3>حواله</h3><ReviewRow label="دارایی"><span className="num">{form.asset} · {assetConfig?.name}</span></ReviewRow><ReviewRow label="شبکه">{networkConfig?.label || form.network}</ReviewRow><ReviewRow label="مقدار"><span className="num">{quote.crypto_amount} {quote.asset}</span></ReviewRow><ReviewRow label="ارزش تقریبی"><span className="num">{fmt(quote.usd_value)} USD</span></ReviewRow></div>
        <div className="remit-review-section"><h3>گیرنده</h3><ReviewRow label="نام کامل">{form.beneficiary_full_name}</ReviewRow><ReviewRow label="شماره تماس"><span className="num">{form.beneficiary_phone}</span></ReviewRow><ReviewRow label="تذکره"><span className="remit-verified"><CheckCircle size={16} weight="fill" /> آپلود شده</span></ReviewRow><ReviewRow label="موقعیت">{form.beneficiary_province} / {form.beneficiary_city}</ReviewRow><ReviewRow label="آدرس">{form.beneficiary_address}</ReviewRow></div>
        <div className="quote-box">
          <ReviewRow label={`قیمت ${quote.asset}`}><span className="num">{fmt(quote.asset_price_usd, 6)} USD</span></ReviewRow>
          <ReviewRow label="نرخ دالر امریکا"><span className="num">{fmt(quote.usd_rate)} AFN</span></ReviewRow>
          <ReviewRow label="کارمزد خدمت"><span className="num">{quote.fee_percent}% · {fmt(quote.fee_afn)} AFN</span></ReviewRow>
          <div className="quote-total buy"><span className="label">مبلغ قابل پرداخت به گیرنده</span><span className="amount num">{fmt(quote.payout_afn, 0)} AFN</span></div>
        </div>
        <button className="btn btn-primary" disabled={busy} onClick={createOrder}>{busy ? "در حال ساخت حواله..." : "تایید و ساخت حواله"}</button>
      </div>}

      {step === "transfer" && created && <div className="card animate-in">
        <div className="section-title"><Wallet size={20} /> ارسال دارایی</div>
        <div className="notice warn">فقط {created.asset} روی شبکه {networkConfig?.label || created.network} به آدرس زیر ارسال شود.</div>
        <div className="info-box" style={{ marginTop: 12 }}>
          <div className="row"><span className="label">مقدار دقیق</span><span className="value num">{created.crypto_amount} {created.asset}</span></div>
          <div className="row remit-wallet-row"><span className="label">آدرس دریافت</span><span className="value"><code>{created.deposit_wallet}</code><button className="copy-btn" onClick={() => copy(created.deposit_wallet)}><Copy size={16} /></button></span></div>
        </div>
        <button className="btn btn-primary" onClick={() => next("tx")}>کریپتو را ارسال کردم</button>
      </div>}

      {step === "tx" && created && <div className="card animate-in">
        <div className="section-title"><PaperPlaneTilt size={20} /> ثبت تراکنش</div>
        <div className="notice">Tx Hash / Transaction ID را از کیف پول یا صرافی مبدأ کپی و اینجا وارد کنید.</div>
        <div className="field" style={{ marginTop: 14 }}><label className="field-label">Tx Hash / Transaction ID</label><textarea className="input remit-textarea num" value={txHash} onChange={(e) => setTxHash(e.target.value)} placeholder="شناسه تراکنش" /></div>
        <button className="btn btn-primary" disabled={busy || !txHash.trim()} onClick={submitTx}>{busy ? "در حال ثبت..." : "ثبت و ارسال برای تأیید"}</button>
      </div>}

      {step === "done" && created && <div className="card animate-in remit-success-card">
        <CheckCircle size={54} weight="fill" className="remit-success-icon" />
        <div className="section-title">تراکنش ثبت شد</div>
        <div className="notice">درخواست اکنون برای مدیر صراف ارسال شده و تأیید بلاکچین به‌صورت خودکار انجام می‌شود. بعد از تأیید، وضعیت حواله به «آماده پرداخت» تغییر می‌کند.</div>
        <div className="info-box" style={{ marginTop: 12 }}><div className="row"><span className="label">کد حواله</span><span className="value num">{created.order_code}</span></div><div className="row"><span className="label">وضعیت</span><span className="value">{STATUS_LABELS[created.status] || created.status}</span></div></div>
      </div>}

      {orders.length > 0 && <div className="card animate-in">
        <div className="section-title">حواله‌های من</div>
        {orders.slice(0, 8).map((o) => <div key={o.id} className="remit-order-row">
          <div className="row-text"><div className="row-title num">{o.order_code}</div><div className="row-subtitle">{o.beneficiary_full_name} · {fmt(o.payout_afn, 0)} AFN · {o.crypto_amount} {o.asset}</div>{o.status === "payout_ready" && o.pickup_code && <div className="remit-pickup">کد دریافت: <strong className="num">{o.pickup_code}</strong></div>}</div>
          <div className={`status-badge status-${o.status === "completed" ? "completed" : o.status === "cancelled" ? "cancelled" : o.status === "payout_ready" ? "confirmed" : "pending"}`}>{STATUS_LABELS[o.status] || o.status}</div>
        </div>)}
      </div>}
    </div>
  );
}
