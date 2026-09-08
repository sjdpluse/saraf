import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Copy, GlobeHemisphereWest, PaperPlaneTilt, Receipt, Wallet } from "@phosphor-icons/react";
import { api } from "../lib/api";

const COUNTRIES = ["آمریکا", "کانادا", "آسترالیا", "آلمان", "فرانسه", "هالند", "سویدن", "بریتانیا", "امارات", "سایر"];
const RELATIONSHIPS = ["پدر/مادر", "همسر", "برادر/خواهر", "فرزند", "اقارب", "دوست", "سایر"];

export default function Remittance({ navigate, showError, onNeedProfile }) {
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
      .then(([c, list]) => { setConfig(c); setOrders(list || []); })
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
      if (e.status === 403) {
        onNeedProfile?.({ target: "remittance" });
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
      <button className="back-btn" onClick={() => navigate("home")}><ArrowRight size={18} /> بازگشت</button>

      <div className="hero-card animate-in">
        <div className="hero-top">
          <div className="hero-row"><div className="hero-brand"><GlobeHemisphereWest size={28} weight="fill" /><span className="hero-brand-name">حواله بین‌المللی</span></div></div>
          <div className="hero-tagline">کریپتو بفرستید؛ خانواده‌تان در افغانستان افغانی نقد دریافت کند.</div>
        </div>
      </div>

      {step === "form" && <div className="card animate-in">
        <div className="section-title">اطلاعات حواله</div>
        <label className="field-label">کشور فرستنده</label>
        <select className="input" value={form.sender_country} onChange={(e) => setField("sender_country", e.target.value)}>{COUNTRIES.map((x) => <option key={x}>{x}</option>)}</select>
        <label className="field-label">مقدار</label>
        <input className="input num" type="number" min="10" value={form.amount} onChange={(e) => setField("amount", e.target.value)} placeholder="مثلاً 500" />
        <div className="grid-2">
          <div><label className="field-label">دارایی</label><select className="input" value={form.asset} onChange={(e) => setField("asset", e.target.value)}>{(config?.assets || []).map((x) => <option key={x.asset}>{x.asset}</option>)}</select></div>
          <div><label className="field-label">شبکه</label><select className="input" value={form.network} onChange={(e) => setField("network", e.target.value)}>{(assetConfig?.networks || []).map((x) => <option key={x}>{x}</option>)}</select></div>
        </div>

        <div className="section-title" style={{ marginTop: 18 }}>گیرنده در افغانستان</div>
        <input className="input" value={form.beneficiary_full_name} onChange={(e) => setField("beneficiary_full_name", e.target.value)} placeholder="نام و تخلص گیرنده" />
        <input className="input" value={form.beneficiary_phone} onChange={(e) => setField("beneficiary_phone", e.target.value)} placeholder="شماره تماس گیرنده" />
        <div className="grid-2"><input className="input" value={form.beneficiary_province} onChange={(e) => setField("beneficiary_province", e.target.value)} placeholder="ولایت" /><input className="input" value={form.beneficiary_city} onChange={(e) => setField("beneficiary_city", e.target.value)} placeholder="شهر" /></div>
        <input className="input" value={form.beneficiary_address} onChange={(e) => setField("beneficiary_address", e.target.value)} placeholder="آدرس (اختیاری)" />
        <label className="field-label">نسبت با گیرنده</label><select className="input" value={form.relationship} onChange={(e) => setField("relationship", e.target.value)}>{RELATIONSHIPS.map((x) => <option key={x}>{x}</option>)}</select>
        <input className="input" value={form.purpose} onChange={(e) => setField("purpose", e.target.value)} placeholder="هدف حواله" />
        <button className="primary-btn" disabled={busy} onClick={getQuote}>{busy ? "در حال محاسبه..." : "محاسبه مبلغ قابل دریافت"}</button>
      </div>}

      {step === "quote" && quote && <div className="card animate-in">
        <div className="section-title"><Receipt size={20} /> بررسی نهایی</div>
        <div className="summary-row"><span>ارسال</span><strong className="num">{quote.crypto_amount} {quote.asset}</strong></div>
        <div className="summary-row"><span>نرخ دالر</span><strong className="num">{Number(quote.usd_rate).toLocaleString()} AFN</strong></div>
        <div className="summary-row"><span>کارمزد</span><strong className="num">{quote.fee_percent}%</strong></div>
        <div className="summary-row total"><span>دریافت خانواده</span><strong className="num">{Number(quote.payout_afn).toLocaleString()} AFN</strong></div>
        <button className="primary-btn" disabled={busy} onClick={createOrder}>{busy ? "در حال ثبت..." : "ثبت حواله"}</button>
        <button className="secondary-btn" onClick={() => setStep("form")}>ویرایش اطلاعات</button>
      </div>}

      {step === "transfer" && created && <div className="card animate-in">
        <div className="section-title"><Wallet size={20} /> انتقال کریپتو</div>
        <div className="notice">فقط {created.asset} روی شبکه {created.network} به آدرس زیر ارسال کنید.</div>
        <div className="wallet-box"><code>{created.deposit_wallet}</code><button onClick={() => copy(created.deposit_wallet)}><Copy size={18} /></button></div>
        <div className="summary-row"><span>مقدار دقیق</span><strong className="num">{created.crypto_amount} {created.asset}</strong></div>
        <label className="field-label">Tx Hash / Transaction ID</label>
        <input className="input num" value={txHash} onChange={(e) => setTxHash(e.target.value)} placeholder="پس از ارسال، شناسه تراکنش را وارد کنید" />
        <button className="primary-btn" disabled={busy} onClick={submitTx}><PaperPlaneTilt size={18} /> {busy ? "در حال ثبت..." : "ثبت تراکنش"}</button>
      </div>}

      {step === "done" && created && <div className="card animate-in">
        <div className="section-title">درخواست ثبت شد</div>
        <div className="notice">تراکنش شما برای بررسی ارسال شد. پس از تایید دریافت کریپتو، کد دریافت نقدی برای شما ارسال می‌شود.</div>
        <div className="summary-row"><span>کد حواله</span><strong className="num">{created.order_code}</strong></div>
        <div className="summary-row"><span>وضعیت</span><strong>{created.status}</strong></div>
      </div>}

      {orders.length > 0 && <div className="card animate-in">
        <div className="section-title">حواله‌های من</div>
        {orders.slice(0, 8).map((o) => <div key={o.id} className="list-row" style={{ borderBottom: "1px solid var(--border)", padding: "12px 0" }}>
          <div className="row-text"><div className="row-title num">{o.order_code}</div><div className="row-subtitle">{o.beneficiary_full_name} · {Number(o.payout_afn).toLocaleString()} AFN</div></div>
          <div className="num" style={{ fontSize: 11 }}>{o.status}</div>
        </div>)}
      </div>}
    </div>
  );
}
