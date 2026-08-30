import { useState } from "react";
import {
  CaretRight,
  IdentificationCard,
  User,
  Phone,
  CreditCard,
  UploadSimple,
  CheckCircle,
  ShieldCheck,
} from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { getTelegramUser } from "../lib/telegram";

const PROFILE_STEPS = ["intro", "basics", "submitting"];
const VERIFY_STEPS = ["intro", "payment", "id_doc", "selfie", "submitting"];

export default function Kyc({ mode = "profile", thresholdUsd, onComplete, onCancel, showError }) {
  const STEPS = mode === "verify" ? VERIFY_STEPS : PROFILE_STEPS;
  const [stepIdx, setStepIdx] = useState(0);
  const tgUser = getTelegramUser();

  const [firstName, setFirstName] = useState(tgUser?.first_name || "");
  const [lastName, setLastName] = useState(tgUser?.last_name || "");
  const [phone, setPhone] = useState("");
  const [paymentInfo, setPaymentInfo] = useState("");
  const [idDocFile, setIdDocFile] = useState(null);
  const [selfieFile, setSelfieFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const step = STEPS[stepIdx];

  function goBack() {
    if (stepIdx === 0) onCancel?.();
    else setStepIdx((i) => i - 1);
  }

  function validateBasics() {
    if (firstName.trim().length < 2 || lastName.trim().length < 2) {
      showError("لطفاً نام و تخلص معتبر وارد کنید.");
      return false;
    }
    if (phone.trim().length < 7) {
      showError("لطفاً شمارهٔ تماس معتبر وارد کنید.");
      return false;
    }
    return true;
  }

  async function submitBasicProfile() {
    if (!validateBasics()) return;
    setSubmitting(true);
    try {
      await api.submitBasicProfile({ first_name: firstName.trim(), last_name: lastName.trim(), phone: phone.trim() });
      setStepIdx(STEPS.indexOf("submitting"));
      setTimeout(() => onComplete?.(), 1000);
    } catch (err) {
      showError(err instanceof ApiError ? err.message : "ثبت پروفایل موفق نشد.");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitVerification() {
    if (!idDocFile || !selfieFile) {
      showError("لطفاً هر دو عکس، سند هویتی و سلفی، را انتخاب کنید.");
      return;
    }
    setSubmitting(true);
    try {
      await api.submitIdentityVerification({
        payment_info: paymentInfo.trim() || null,
        id_document: idDocFile,
        selfie: selfieFile,
      });
      setStepIdx(STEPS.indexOf("submitting"));
      setTimeout(() => onComplete?.(), 1200);
    } catch (err) {
      showError(err instanceof ApiError ? err.message : "ثبت اسناد تایید هویت موفق نشد.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="header">
        {step !== "submitting" ? (
          <button className="back-btn" onClick={goBack} aria-label="بازگشت">
            <CaretRight size={18} weight="bold" />
          </button>
        ) : (
          <div className="header-spacer" />
        )}
        <h1>
          <IdentificationCard size={18} className="header-icon" weight="bold" />
          {mode === "verify" ? "تایید هویت" : "تکمیل پروفایل"}
        </h1>
        <div className="header-spacer" />
      </div>

      {step !== "submitting" && (
        <div className="stepper">
          {STEPS.slice(0, -1).map((s, i) => (
            <div key={s} className={`dot ${i <= stepIdx ? "active" : ""}`} />
          ))}
        </div>
      )}

      {step === "intro" && mode === "profile" && (
        <div className="card animate-in">
          <div style={{ textAlign: "center", marginBottom: 16 }}>
            <ShieldCheck size={40} color="var(--color-primary)" weight="fill" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 15, textAlign: "center", marginBottom: 10 }}>
            برای ثبت سفارش، پروفایل خود را تکمیل کنید
          </div>
          <div className="notice" style={{ justifyContent: "center", textAlign: "center", marginBottom: 18 }}>
            فقط نام، تخلص و شمارهٔ تماس کافی است. این مرحله تنها یک‌بار انجام می‌شود.
          </div>
          <button className="btn btn-primary" onClick={() => setStepIdx(1)}>شروع</button>
        </div>
      )}

      {step === "intro" && mode === "verify" && (
        <div className="card animate-in">
          <div style={{ textAlign: "center", marginBottom: 16 }}>
            <ShieldCheck size={40} color="var(--color-primary)" weight="fill" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 15, textAlign: "center", marginBottom: 10 }}>
            تایید هویت برای معاملات بزرگ‌تر
          </div>
          <div className="notice" style={{ justifyContent: "center", textAlign: "center", marginBottom: 18 }}>
            برای معاملات بالای {thresholdUsd ? Math.round(thresholdUsd) : 250} دالر، طبق شرایط صراف، تایید هویت با یک سند هویتی و یک سلفی لازم است. معلومات پرداخت اختیاری است و می‌توانید بعداً هم وارد کنید.
          </div>
          <button className="btn btn-primary" onClick={() => setStepIdx(1)}>شروع تایید هویت</button>
        </div>
      )}

      {step === "basics" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label"><User size={14} style={{ verticalAlign: "-2px", marginLeft: 4 }} />نام</label>
            <input className="input" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div className="field">
            <label className="field-label">تخلص</label>
            <input className="input" value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
          <div className="field">
            <label className="field-label"><Phone size={14} style={{ verticalAlign: "-2px", marginLeft: 4 }} />شمارهٔ تماس</label>
            <input className="input num" type="tel" placeholder="+93 7XX XXX XXX" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <button className="btn btn-primary" disabled={submitting} onClick={submitBasicProfile}>
            {submitting ? <span className="spinner" /> : "ثبت پروفایل"}
          </button>
        </div>
      )}

      {step === "payment" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label"><CreditCard size={14} style={{ verticalAlign: "-2px", marginLeft: 4 }} />معلومات پرداخت (اختیاری — شمارهٔ حساب یا حواله‌جات)</label>
            <textarea className="input" rows={3} placeholder="مثال: عزیزی بانک — 0123456789 (اختیاری)" value={paymentInfo} onChange={(e) => setPaymentInfo(e.target.value)} />
          </div>
          <button className="btn btn-primary" onClick={() => setStepIdx(2)}>ادامه</button>
        </div>
      )}

      {step === "id_doc" && (
        <div className="card animate-in">
          <div className="notice" style={{ marginBottom: 14 }}>لطفاً یک عکس واضح از تذکره یا سند هویتی خود آپلود کنید.</div>
          <label className={`upload-box ${idDocFile ? "has-file" : ""}`}>
            <input type="file" accept="image/*" onChange={(e) => setIdDocFile(e.target.files?.[0] || null)} />
            {idDocFile ? <CheckCircle size={22} weight="fill" /> : <UploadSimple size={22} />}
            <span>{idDocFile ? "عکس انتخاب شد" : "انتخاب عکس سند هویتی"}</span>
          </label>
          <button className="btn btn-primary" style={{ marginTop: 16 }} disabled={!idDocFile} onClick={() => setStepIdx(3)}>ادامه</button>
        </div>
      )}

      {step === "selfie" && (
        <div className="card animate-in">
          <div className="notice" style={{ marginBottom: 14 }}>در مرحلهٔ آخر، یک سلفی واضح از چهرهٔ خود آپلود کنید.</div>
          <label className={`upload-box ${selfieFile ? "has-file" : ""}`}>
            <input type="file" accept="image/*" capture="user" onChange={(e) => setSelfieFile(e.target.files?.[0] || null)} />
            {selfieFile ? <CheckCircle size={22} weight="fill" /> : <UploadSimple size={22} />}
            <span>{selfieFile ? "سلفی انتخاب شد" : "گرفتن یا انتخاب سلفی"}</span>
          </label>
          <button className="btn btn-primary" style={{ marginTop: 16 }} disabled={!selfieFile || submitting} onClick={submitVerification}>
            {submitting ? <span className="spinner" /> : "ثبت اسناد"}
          </button>
        </div>
      )}

      {step === "submitting" && (
        <div className="card success-screen animate-in">
          <div className="success-icon"><CheckCircle size={36} weight="fill" /></div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>{mode === "verify" ? "اسناد شما ثبت شد" : "پروفایل شما ثبت شد"}</div>
          <div className="notice" style={{ textAlign: "center" }}>در حال برگشت به سفارش شما...</div>
        </div>
      )}
    </div>
  );
}
