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

/**
 * mode="profile": مرحلهٔ اول و اجباری — فقط نام/نام‌خانوادگی/شماره تماس. برای
 *   هر سفارشی (حتی کوچک‌ترین) لازم است.
 * mode="verify": مرحلهٔ دوم و اختیاری — فقط وقتی مبلغ سفارش کاربر از
 *   thresholdUsd بیشتر باشد لازم می‌شود. اطلاعات پرداخت در این حالت اختیاری
 *   است؛ مدرک هویتی و سلفی الزامی‌اند.
 */
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
  const lastStepIdx = STEPS.length - 2; // ایندکس آخرین مرحلهٔ قابل‌نمایش پیش از «submitting»

  function goBack() {
    if (stepIdx === 0) {
      onCancel?.();
    } else {
      setStepIdx((i) => i - 1);
    }
  }

  function validateBasics() {
    if (firstName.trim().length < 2 || lastName.trim().length < 2) {
      showError("لطفاً نام و نام خانوادگی معتبر وارد کنید.");
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
      showError(err instanceof ApiError ? err.message : "ثبت پروفایل ناموفق بود.");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitVerification() {
    if (!idDocFile || !selfieFile) {
      showError("لطفاً هر دو عکس (مدرک هویتی و سلفی) را انتخاب کنید.");
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
      showError(err instanceof ApiError ? err.message : "ثبت مدارک احراز هویت ناموفق بود.");
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
          {mode === "verify" ? "احراز هویت" : "تکمیل پروفایل"}
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
            فقط نام، نام خانوادگی و شمارهٔ تماس کافی است — همین. این کار فقط همین
            یک‌بار انجام می‌شود.
          </div>
          <button className="btn btn-primary" onClick={() => setStepIdx(1)}>
            شروع
          </button>
        </div>
      )}

      {step === "intro" && mode === "verify" && (
        <div className="card animate-in">
          <div style={{ textAlign: "center", marginBottom: 16 }}>
            <ShieldCheck size={40} color="var(--color-primary)" weight="fill" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 15, textAlign: "center", marginBottom: 10 }}>
            احراز هویت برای معاملات بزرگ‌تر
          </div>
          <div className="notice" style={{ justifyContent: "center", textAlign: "center", marginBottom: 18 }}>
            برای معاملات بالای {thresholdUsd ? Math.round(thresholdUsd) : 250} دالر، طبق قوانین Saraf، تایید
            هویت با یک مدرک شناسایی و یک سلفی لازم است. اطلاعات پرداخت اختیاری
            است و می‌توانید بعداً هم وارد کنید.
          </div>
          <button className="btn btn-primary" onClick={() => setStepIdx(1)}>
            شروع احراز هویت
          </button>
        </div>
      )}

      {step === "basics" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label">
              <User size={14} style={{ verticalAlign: "-2px", marginLeft: 4 }} />
              نام
            </label>
            <input className="input" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div className="field">
            <label className="field-label">نام خانوادگی</label>
            <input className="input" value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
          <div className="field">
            <label className="field-label">
              <Phone size={14} style={{ verticalAlign: "-2px", marginLeft: 4 }} />
              شمارهٔ تماس
            </label>
            <input
              className="input num"
              type="tel"
              placeholder="+93 7XX XXX XXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" disabled={submitting} onClick={submitBasicProfile}>
            {submitting ? <span className="spinner" /> : "ثبت پروفایل"}
          </button>
        </div>
      )}

      {step === "payment" && (
        <div className="card animate-in">
          <div className="field">
            <label className="field-label">
              <CreditCard size={14} style={{ verticalAlign: "-2px", marginLeft: 4 }} />
              اطلاعات پرداخت (اختیاری — شمارهٔ حساب یا حواله‌جات)
            </label>
            <textarea
              className="input"
              rows={3}
              placeholder="مثال: بانک ملی — 0123456789 (اختیاری)"
              value={paymentInfo}
              onChange={(e) => setPaymentInfo(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" onClick={() => setStepIdx(2)}>
            ادامه
          </button>
        </div>
      )}

      {step === "id_doc" && (
        <div className="card animate-in">
          <div className="notice" style={{ marginBottom: 14 }}>
            لطفاً یک عکس واضح از تذکره یا مدرک هویتی خود بارگذاری کنید.
          </div>
          <label className={`upload-box ${idDocFile ? "has-file" : ""}`}>
            <input type="file" accept="image/*" onChange={(e) => setIdDocFile(e.target.files?.[0] || null)} />
            {idDocFile ? <CheckCircle size={22} weight="fill" /> : <UploadSimple size={22} />}
            <span>{idDocFile ? "عکس انتخاب شد" : "انتخاب عکس مدرک هویتی"}</span>
          </label>
          <button className="btn btn-primary" style={{ marginTop: 16 }} disabled={!idDocFile} onClick={() => setStepIdx(3)}>
            ادامه
          </button>
        </div>
      )}

      {step === "selfie" && (
        <div className="card animate-in">
          <div className="notice" style={{ marginBottom: 14 }}>
            در آخرین مرحله، یک سلفی واضح از چهرهٔ خودتان بارگذاری کنید.
          </div>
          <label className={`upload-box ${selfieFile ? "has-file" : ""}`}>
            <input type="file" accept="image/*" capture="user" onChange={(e) => setSelfieFile(e.target.files?.[0] || null)} />
            {selfieFile ? <CheckCircle size={22} weight="fill" /> : <UploadSimple size={22} />}
            <span>{selfieFile ? "سلفی انتخاب شد" : "گرفتن / انتخاب سلفی"}</span>
          </label>
          <button className="btn btn-primary" style={{ marginTop: 16 }} disabled={!selfieFile || submitting} onClick={submitVerification}>
            {submitting ? <span className="spinner" /> : "ثبت مدارک"}
          </button>
        </div>
      )}

      {step === "submitting" && (
        <div className="card success-screen animate-in">
          <div className="success-icon">
            <CheckCircle size={36} weight="fill" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>
            {mode === "verify" ? "مدارک شما ثبت شد" : "پروفایل شما ثبت شد"}
          </div>
          <div className="notice" style={{ textAlign: "center" }}>
            در حال بازگشت به سفارش شما...
          </div>
        </div>
      )}
    </div>
  );
}
