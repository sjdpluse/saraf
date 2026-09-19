import { useState } from "react";
import {
  ArrowRight,
  Check,
  Copy,
  ExternalLink,
  Handshake,
  Info,
  ShieldCheck,
  WarningCircle,
} from "@phosphor-icons/react";

export const JM_REFERRAL_URL = "https://one.justmarkets.link/a/tju6sc0sb8";
export const JM_PARTNER_CODE = "tju6sc0sb8";

export function JMPage({ children }) {
  return <main className="app-shell jm-shell">{children}</main>;
}

export function JMHeader({ title, onBack }) {
  return (
    <header className="jm-header">
      <button className="back-btn jm-back-btn" type="button" onClick={onBack} aria-label="بازگشت">
        <ArrowRight size={22} weight="bold" />
      </button>
      <div>
        <span className="jm-header-kicker">Saraf IB</span>
        <strong>{title}</strong>
      </div>
      <span className="jm-header-mark" aria-hidden="true"><Handshake size={21} weight="duotone" /></span>
    </header>
  );
}

export function JMPartnershipBadge() {
  return (
    <span className="jm-partnership-badge">
      <Handshake size={17} weight="duotone" />
      <b>Saraf</b>
      <span>×</span>
      <b>JustMarkets</b>
    </span>
  );
}

export function JMSectionTitle({ eyebrow, title, description }) {
  return (
    <div className="jm-section-title">
      {eyebrow && <span>{eyebrow}</span>}
      <h2>{title}</h2>
      {description && <p>{description}</p>}
    </div>
  );
}

export function JMNotice({ title, children, tone = "info" }) {
  const Icon = tone === "warning" ? WarningCircle : Info;
  return (
    <aside className={`jm-notice ${tone}`}>
      <Icon size={21} weight="fill" />
      <div><strong>{title}</strong><p>{children}</p></div>
    </aside>
  );
}

export function JMServiceCard({ icon, title, children }) {
  return (
    <article className="jm-service-card">
      <span className="jm-service-icon">{icon}</span>
      <strong>{title}</strong>
      <p>{children}</p>
    </article>
  );
}

export function JMStep({ number, icon, title, children }) {
  return (
    <article className="jm-step">
      <span className="jm-step-icon">{icon || number}</span>
      <div>
        <small>مرحله {number}</small>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </article>
  );
}

export function JMReferralCard() {
  const [copied, setCopied] = useState(false);

  async function copyPartnerCode() {
    try {
      await navigator.clipboard.writeText(JM_PARTNER_CODE);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      const area = document.createElement("textarea");
      area.value = JM_PARTNER_CODE;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    }
  }

  return (
    <section className="jm-referral-card">
      <div className="jm-referral-head">
        <span><ShieldCheck size={24} weight="duotone" /></span>
        <div><small>لینک معرفی Saraf IB</small><strong>افتتاح حساب JustMarkets</strong></div>
      </div>
      <p>برای این‌که حساب از مسیر معرفی صراف ثبت شود، از لینک زیر استفاده کنید یا کد معرفی را در بخش Partner Code وارد نمایید.</p>
      <div className="jm-code-row" dir="ltr">
        <code>{JM_PARTNER_CODE}</code>
        <button type="button" onClick={copyPartnerCode} aria-label="کاپی کد معرفی">
          {copied ? <Check size={19} weight="bold" /> : <Copy size={19} />}
          <span>{copied ? "کاپی شد" : "کاپی"}</span>
        </button>
      </div>
      <a className="jm-primary-link" href={JM_REFERRAL_URL} target="_blank" rel="noreferrer">
        افتتاح حساب با لینک صراف
        <ExternalLink size={18} weight="bold" />
      </a>
    </section>
  );
}

export function JMNavCard({ icon, title, description, onClick }) {
  return (
    <button className="jm-nav-card" type="button" onClick={onClick}>
      <span className="jm-nav-icon">{icon}</span>
      <span><strong>{title}</strong><small>{description}</small></span>
      <span className="jm-nav-arrow">‹</span>
    </button>
  );
}
