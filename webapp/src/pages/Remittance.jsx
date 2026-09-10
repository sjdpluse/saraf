import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle,
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
import CopyRow from "../components/CopyRow";
import { REMITTANCE_STATUS as STATUS_LABELS } from "../lib/remittance";

const COUNTRIES = [
  "آسترالیا", "امارات متحده عربی", "آلمان", "امریکا", "بریتانیا", "ترکیه",
  "فرانسه", "کانادا", "هالند", "سویدن", "سایر",
];

const STEPS = ["sender", "asset", "network", "amount", "beneficiary", "identity", "address", "review", "transfer", "tx", "done"];
const PHASES = [
  { label: "فرستنده", steps: ["sender"] },
  { label: "دارایی", steps: ["asset", "network", "amount"] },
  { label: "گیرنده", steps: ["beneficiary", "identity", "address"] },
  { label: "بررسی", steps: ["review"] },
  { label: "انتقال", steps: ["transfer", "tx", "done"] },
];

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
  const active = Math.max(0, PHASES.findIndex((phase) => phase.steps.includes(current)));
  return (
    <ol className="remit-progress" aria-label="مراحل حواله">
      {PHASES.map((phase, i) => <li key={phase.label} className={i < active || current === "done" ? "complete" : i === active ? "current" : ""} aria-current={i === active ? "step" : undefined}><span>{i < active || current === "done" ? <CheckCircle size={21} weight="fill" /> : (i + 1).toLocaleString("fa-AF")}</span><small>{phase.label}</small></li>)}
    </ol>
  );
}

function ReviewRow({ label, children }) {
  return <div className="quote-row"><span>{label}</span><span className="value">{children}</span></div>;
}

export default function Remittance({ navigate, showError, onNeedProfile, onNeedVerification, initialOrder, resumeState, onResumeConsumed }) {
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [configError, setConfigError] = useState("");
  const [configAttempt, setConfigAttempt] = useState(0);
  const [step, setStep] = useState(initialOrder ? "transfer" : resumeState?.step || "sender");
  const [quote, setQuote] = useState(resumeState?.quote || null);
  const [created, setCreated] = useState(initialOrder || null);
  const [txHash, setTxHash] = useState("");
  const [idFile, setIdFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(() => ({
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
    ...resumeState?.form,
    ...(initialOrder ? { asset: initialOrder.asset, network: initialOrder.network } : {}),
  }));

  const assetConfig = useMemo(() => config?.assets?.find((x) => x.asset === form.asset), [config, form.asset]);
  const networkConfig = useMemo(() => assetConfig?.networks?.find((x) => x.code === form.network), [assetConfig, form.network]);
  const currentIndex = STEPS.indexOf(step);

  useEffect(() => {
    let active = true;
    setConfigLoading(true);
    setConfigError("");
    api.getRemittanceConfig()
      .then((c) => {
        if (!active) return;
        setConfig(c);
        const first = c?.assets?.[0];
        if (first) setForm((s) => s.asset ? s : ({ ...s, asset: first.asset, network: first.networks?.[0]?.code || "" }));
      })
      .catch((e) => { if (active) setConfigError(e.message); })
      .finally(() => { if (active) setConfigLoading(false); });
    return () => { active = false; };
  }, [configAttempt]);

  useEffect(() => {
    if (resumeState) onResumeConsumed?.();
  }, []);

  function setField(key, value) {
    setForm((s) => ({ ...s, [key]: value }));
  }

  function next(target) { setStep(target); window.scrollTo?.({ top: 0, behavior: "instant" }); }
  function back() {
    if (step === "sender") return navigate("home");
    if (step === "tx") return next("transfer");
    if (["transfer", "done"].includes(step)) return navigate("remittances");
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
    if (form.beneficiary_id_document_path) return next("address");
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
      next("transfer");
    } catch (e) {
      if (e.code === "IDENTITY_VERIFICATION_REQUIRED") {
        onNeedVerification?.({ form, quote, step: "review" }, config?.identity_verification_threshold_usd);
      } else if (e.code === "BASIC_PROFILE_REQUIRED") {
        onNeedProfile?.({ form, quote, step: "review" });
      } else showError(e.message);
    } finally { setBusy(false); }
  }

  async function submitTx() {
    if (!txHash.trim()) return showError("Tx Hash / Transaction ID را وارد کنید.");
    setBusy(true);
    try {
      const updated = await api.submitRemittanceTx(created.id, txHash.trim());
      setCreated(updated);
      next("done");
    } catch (e) { showError(e.message); }
    finally { setBusy(false); }
  }

  const invalidSender = form.sender_full_name.trim().length < 3 || !form.sender_country;
  const invalidBeneficiary = form.beneficiary_full_name.trim().length < 3 || form.beneficiary_phone.trim().length < 7;
  const invalidAddress = !form.beneficiary_province.trim() || !form.beneficiary_city.trim() || form.beneficiary_address.trim().length < 3;

  return (
    <main className="app-shell remittance-shell">
      <div className="header">
        <button className="back-btn" onClick={back} disabled={busy} aria-label={["transfer", "done"].includes(step) ? "رفتن به حواله‌های من" : "بازگشت"}><ArrowRight size={18} /></button>
        <h1>حواله از طریق کریپتو</h1><div className="header-spacer" />
      </div>
      <StepHeader current={step} />

      {configError && !created && <div className="card" role="alert"><p>{configError}</p><button className="btn btn-outline" onClick={() => setConfigAttempt((value) => value + 1)}>تلاش دوباره</button></div>}
      {configLoading && !created && <div className="notice" role="status">در حال دریافت اطلاعات حواله…</div>}
      {["beneficiary", "identity", "address"].includes(step) && quote && <div className="remit-context"><span className="num">{quote.crypto_amount} {quote.asset}</span><span>دریافت گیرنده: <b>{fmt(quote.payout_afn, 0)} افغانی</b></span></div>}
      <fieldset className="remit-flow" disabled={busy || (!created && (configLoading || !!configError))}>

      {step === "sender" && <div className="card animate-in">
        <div className="section-title"><User size={20} /> اطلاعات فرستنده</div>
        <div className="field"><label className="field-label" htmlFor="remit-sender">نام کامل فرستنده</label><input id="remit-sender" className="input" value={form.sender_full_name} onChange={(e) => setField("sender_full_name", e.target.value)} placeholder="نام و تخلص" autoComplete="name" /></div>
        <div className="field"><label className="field-label" htmlFor="remit-country">کشور فرستنده</label><select id="remit-country" className="input" value={form.sender_country} onChange={(e) => setField("sender_country", e.target.value)}><option value="" disabled>کشور را انتخاب کنید</option>{COUNTRIES.map((x) => <option key={x} value={x}>{x}</option>)}</select></div>
        <button className="btn btn-primary" disabled={invalidSender || !config?.assets?.length} onClick={() => next("asset")}>ادامه</button>
        {config && !config.assets?.length && <div className="notice warn">در حال حاضر حوالهٔ جدید فعال نیست.</div>}
      </div>}

      {step === "asset" && <div className="card animate-in">
        <div className="section-title">انتخاب دارایی</div>
        <div className="section-hint">دارایی مورد نظر برای ارسال حواله را انتخاب کنید.</div>
        <div className="remit-assets">
          {(config?.assets || []).map((item) => <button key={item.asset} aria-pressed={form.asset === item.asset} className={`remit-asset-card ${form.asset === item.asset ? "selected" : ""}`} onClick={() => chooseAsset(item)}>
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
        <div className="amount-input-wrap"><input aria-label={`مقدار حواله به ${form.asset}`} className="input amount-input num" type="number" inputMode="decimal" min="0" step="any" value={form.amount} onChange={(e) => { setField("amount", e.target.value); setQuote(null); }} placeholder={form.asset === "BTC" ? "0.01" : form.asset === "ETH" ? "0.20" : "500"} /><span>{form.asset}</span></div>
        <div className="notice">ارزش حواله باید بین {fmt(config?.min_usd || 10, 0)} تا {fmt(config?.max_usd || 10000, 0)} دالر امریکا (USD) باشد.</div>
        <button className="btn btn-primary" disabled={busy || !form.amount} onClick={calculateQuote}>{busy ? "در حال محاسبه..." : "محاسبه حواله"}</button>
      </div>}

      {step === "beneficiary" && <div className="card animate-in">
        <div className="section-title"><User size={20} /> اطلاعات گیرنده</div>
        <div className="field"><label className="field-label" htmlFor="remit-beneficiary">نام کامل گیرنده</label><input id="remit-beneficiary" className="input" value={form.beneficiary_full_name} onChange={(e) => setField("beneficiary_full_name", e.target.value)} placeholder="نام و تخلص مطابق تذکره" /></div>
        <div className="field"><label className="field-label" htmlFor="remit-phone">شماره تماس گیرنده</label><input id="remit-phone" className="input num" type="tel" value={form.beneficiary_phone} onChange={(e) => setField("beneficiary_phone", e.target.value)} placeholder="07XXXXXXXX" /></div>
        <button className="btn btn-primary" disabled={invalidBeneficiary} onClick={() => next("identity")}>ادامه</button>
      </div>}

      {step === "identity" && <div className="card animate-in">
        <div className="section-title"><IdentificationCard size={21} /> تذکره گیرنده</div>
        <div className="notice">تصویر واضح تذکره گیرنده را آپلود کنید. این فایل خصوصی است و برای تطبیق هویت هنگام پرداخت استفاده می‌شود.</div>
        <label className={`remit-upload ${idFile ? "ready" : ""}`}>
          <UploadSimple size={28} weight="duotone" />
          <strong>{idFile ? idFile.name : form.beneficiary_id_document_path ? "تذکره آپلود شده — تغییر تصویر" : "انتخاب تصویر تذکره"}</strong>
          <small>JPG, PNG یا WEBP — حداکثر ۱۰ MB</small>
          <input type="file" className="visually-hidden-input" aria-label="انتخاب تصویر تذکره گیرنده" accept="image/jpeg,image/png,image/webp" onChange={(e) => { const file = e.target.files?.[0]; if (file) { setIdFile(file); setField("beneficiary_id_document_path", ""); } }} />
        </label>
        <button className="btn btn-primary" disabled={busy || (!idFile && !form.beneficiary_id_document_path)} onClick={uploadIdentity}>{busy ? "در حال آپلود..." : form.beneficiary_id_document_path ? "ادامه" : "آپلود و ادامه"}</button>
      </div>}

      {step === "address" && <div className="card animate-in">
        <div className="section-title"><MapPin size={20} /> آدرس گیرنده</div>
        <div className="remit-grid"><div className="field"><label className="field-label" htmlFor="remit-province">ولایت</label><input id="remit-province" className="input" value={form.beneficiary_province} onChange={(e) => setField("beneficiary_province", e.target.value)} placeholder="مثلاً کابل" /></div><div className="field"><label className="field-label" htmlFor="remit-city">شهر / ولسوالی</label><input id="remit-city" className="input" value={form.beneficiary_city} onChange={(e) => setField("beneficiary_city", e.target.value)} placeholder="مثلاً کابل" /></div></div>
        <div className="field"><label className="field-label" htmlFor="remit-address">آدرس کامل</label><textarea id="remit-address" className="input remit-textarea" value={form.beneficiary_address} onChange={(e) => setField("beneficiary_address", e.target.value)} placeholder="ناحیه، منطقه، سرک یا نشانی دقیق" /></div>
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
          <CopyRow label="آدرس دریافت" value={created.deposit_wallet} />
        </div>
        <button className="btn btn-primary" onClick={() => next("tx")}>کریپتو را ارسال کردم</button>
      </div>}

      {step === "tx" && created && <div className="card animate-in">
        <div className="section-title"><PaperPlaneTilt size={20} /> ثبت تراکنش</div>
        <div className="notice">Tx Hash / Transaction ID را از کیف پول یا صرافی مبدأ کپی و اینجا وارد کنید.</div>
        <div className="field" style={{ marginTop: 14 }}><label className="field-label" htmlFor="remit-tx">Tx Hash / Transaction ID</label><textarea id="remit-tx" className="input remit-textarea num" value={txHash} onChange={(e) => setTxHash(e.target.value)} placeholder="شناسه تراکنش" /></div>
        <button className="btn btn-primary" disabled={busy || !txHash.trim()} onClick={submitTx}>{busy ? "در حال ثبت..." : "ثبت و ارسال برای تأیید"}</button>
      </div>}

      {step === "done" && created && <div className="card animate-in remit-success-card">
        <CheckCircle size={54} weight="fill" className="remit-success-icon" />
        <div className="section-title">تراکنش ثبت شد</div>
        <div className="notice">درخواست اکنون برای مدیر صراف ارسال شده و تأیید بلاکچین به‌صورت خودکار انجام می‌شود. بعد از تأیید، وضعیت حواله به «آماده پرداخت» تغییر می‌کند.</div>
        <div className="info-box" style={{ marginTop: 12 }}><div className="row"><span className="label">کد حواله</span><span className="value num">{created.order_code}</span></div><div className="row"><span className="label">وضعیت</span><span className="value">{STATUS_LABELS[created.status] || created.status}</span></div></div>
      </div>}

      {step === "done" && <button className="btn btn-primary" onClick={() => navigate("remittances")}>پیگیری در حواله‌های من</button>}
      </fieldset>
    </main>
  );
}
