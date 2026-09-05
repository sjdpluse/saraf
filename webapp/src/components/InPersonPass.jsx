import { useEffect, useState } from "react";
import { CheckCircle, DownloadSimple, MapPin, Phone, Warning } from "@phosphor-icons/react";
import { api, ApiError } from "../lib/api";
import { downloadTelegramFile } from "../lib/telegram";
import { SARAF_LOGO_URL, assetLogo, normalizeAsset } from "../lib/brand";
import {
  IN_PERSON_ADDRESS,
  IN_PERSON_REPRESENTATIVE_PHONE,
  SARAF_SUPPORT_PHONE,
} from "../lib/inPerson";

const SCRAMBLE_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function CyberCode({ code }) {
  const finalChars = String(code || "").padStart(4, "0").slice(-4).split("");
  const [chars, setChars] = useState(finalChars.map(() => "0"));

  useEffect(() => {
    setChars(finalChars.map(() => "0"));
    const intervals = [];
    const timeouts = [];

    finalChars.forEach((finalChar, index) => {
      const interval = window.setInterval(() => {
        setChars((prev) => {
          const next = [...prev];
          next[index] = SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)];
          return next;
        });
      }, 52 + index * 7);
      intervals.push(interval);

      const timeout = window.setTimeout(() => {
        window.clearInterval(interval);
        setChars((prev) => {
          const next = [...prev];
          next[index] = finalChar;
          return next;
        });
      }, 620 + index * 260);
      timeouts.push(timeout);
    });

    return () => {
      intervals.forEach((id) => window.clearInterval(id));
      timeouts.forEach((id) => window.clearTimeout(id));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  return (
    <div className="cyber-code num" aria-label={`کد مراجعه ${code}`}>
      {chars.map((char, index) => <span key={index}>{char}</span>)}
    </div>
  );
}

export default function InPersonPass({
  action,
  asset,
  code,
  onContinue,
  buttonClass = "btn-primary",
  showError,
}) {
  const selectedAsset = normalizeAsset(asset);
  const [downloaded, setDownloaded] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const actionFa = action === "buy" ? "پرداخت حضوری" : "دریافت حضوری";
  const coinLogo = assetLogo(selectedAsset);

  useEffect(() => setDownloaded(false), [action, selectedAsset, code]);

  async function download() {
    setDownloading(true);
    try {
      const result = await api.getInPersonPassLink({ action, asset: selectedAsset, code });
      const absoluteUrl = new URL(result.download_url, window.location.origin).toString();
      const accepted = await downloadTelegramFile(absoluteUrl, result.file_name);
      if (!accepted) {
        showError?.("دانلود کارت تایید نشد. لطفاً دوباره روی «دانلود کارت مراجعه» بزنید و دانلود را تایید کنید.");
        return;
      }
      setDownloaded(true);
    } catch (err) {
      showError?.(err instanceof ApiError ? err.message : "دانلود کارت مراجعه ناموفق بود.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="inperson-pass-wrap animate-in">
      <div className="inperson-pass">
        <div className="inperson-pass-head">
          <div className="inperson-brand-lockup">
            <img src={SARAF_LOGO_URL} alt="Saraf" />
            <div><b>صراف</b><span>کارت مراجعهٔ حضوری</span></div>
          </div>
          <div className="inperson-asset-lockup">
            <img src={coinLogo} alt={selectedAsset} />
            <b className="num">{selectedAsset}</b>
          </div>
        </div>

        <div className="inperson-action">{actionFa}</div>
        <div className="inperson-address"><MapPin size={18} weight="fill" /><span>{IN_PERSON_ADDRESS}</span></div>
        <div className="inperson-code"><span>کد مراجعه</span><CyberCode code={code} /></div>

        <div className="inperson-contact-grid">
          <div className="inperson-contact-item">
            <Phone size={17} weight="fill" />
            <span>شماره نماینده صراف</span>
            <strong className="num">{IN_PERSON_REPRESENTATIVE_PHONE}</strong>
          </div>
          <div className="inperson-contact-item">
            <Phone size={17} weight="fill" />
            <span>پشتیبانی صراف</span>
            <strong className="num">{SARAF_SUPPORT_PHONE}</strong>
          </div>
        </div>
      </div>

      <button className="btn btn-secondary" onClick={download} disabled={downloading}>
        {downloading ? <span className="spinner" /> : downloaded ? <CheckCircle size={18} weight="fill" /> : <DownloadSimple size={18} weight="bold" />}
        {downloading ? "در حال آماده‌سازی دانلود..." : downloaded ? "دانلود تایید شد" : "دانلود کارت مراجعه"}
      </button>

      <div className={`notice ${downloaded ? "" : "warn"}`}>
        {downloaded
          ? <><CheckCircle size={16} weight="fill" /> درخواست دانلود کارت توسط دستگاه تایید شد؛ کارت را هنگام مراجعه همراه داشته باشید.</>
          : <><Warning size={16} weight="fill" /> برای ادامه ابتدا کارت مراجعه را واقعاً دانلود و تایید کنید.</>}
      </div>
      <button className={`btn ${buttonClass}`} onClick={onContinue} disabled={!downloaded}>ادامه</button>
    </div>
  );
}
