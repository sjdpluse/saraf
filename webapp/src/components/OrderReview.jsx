import { CheckCircle, ShieldCheck, Warning, ArrowRight, CurrencyDollar, Wallet } from "@phosphor-icons/react";
import { assetLogo, normalizeAsset } from "../lib/brand";

function DetailRow({ label, value, mono = false }) {
  return (
    <div className="review-detail-row">
      <span>{label}</span>
      <strong className={mono ? "num" : ""}>{value || "—"}</strong>
    </div>
  );
}

export default function OrderReview({ action, asset, amount, quote, exchange, network, walletAddress, paymentLabel, paymentProofLabel, receiveLabel, payoutInfo, proofLabel, inPersonCode, cardPreviewUrl, previewLoading, onBack, onConfirm, submitting }) {
  const selectedAsset = normalizeAsset(asset);
  const isBuy = action === "buy";
  const afn = Number(quote?.total_afn || 0);
  const dollarAmount = Number(isBuy ? (quote?.payable_usd ?? quote?.total_usd ?? amount ?? 0) : (quote?.receivable_usd ?? quote?.total_usd ?? amount ?? 0));
  const resolvedPaymentProof = paymentProofLabel || (isBuy ? (paymentLabel === "پرداخت حضوری" ? "پرداخت حضوری — بدون رسید آنلاین" : "رسید پرداخت بارگذاری‌شده") : null);

  return (
    <div className="animate-in review-stack">
      <div className={`card review-hero ${isBuy ? "buy" : "sell"}`}>
        <div className="review-hero-head">
          <div className="review-asset-title">
            <span className="review-asset-logo"><img src={assetLogo(selectedAsset)} alt={selectedAsset} /></span>
            <div><h2>بررسی نهایی درخواست</h2><p>معلومات را پیش از ثبت نهایی کنترل کنید</p></div>
          </div>
          <span className="review-type-pill num">{isBuy ? "BUY" : "SELL"} {selectedAsset}</span>
        </div>

        <div className="review-amount-block">
          <span className="review-amount-label">مقدار معامله</span>
          <div className="review-amount-value"><img src={assetLogo(selectedAsset)} alt="" /><strong className="num">{Number(amount).toLocaleString()} {selectedAsset}</strong></div>
        </div>

        <div className="review-money-grid">
          <div className="review-money-card"><CurrencyDollar size={20} weight="bold" /><span>{isBuy ? "قابل پرداخت به دالر" : "قابل دریافت به دالر"}</span><strong className="num">${dollarAmount.toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong></div>
          <div className="review-money-card"><Wallet size={20} weight="bold" /><span>{isBuy ? "قابل پرداخت به افغانی" : "قابل دریافت به افغانی"}</span><strong className="num">{afn.toLocaleString()} ؋</strong></div>
        </div>
      </div>

      <div className="card review-details-card">
        <div className="review-section-title">جزئیات معامله</div>
        <DetailRow label="نوع درخواست" value={`${isBuy ? "خرید" : "فروش"} ${selectedAsset}`} />
        <DetailRow label="صرافی / کیف پول" value={exchange} />
        <DetailRow label="شبکه" value={network} mono />
        {walletAddress && <DetailRow label={isBuy ? "آدرس دریافت" : "آدرس واریز صراف"} value={walletAddress} mono />}
        {isBuy && <DetailRow label="روش پرداخت" value={paymentLabel} />}
        {isBuy && resolvedPaymentProof && <DetailRow label="وضعیت پرداخت / رسید" value={resolvedPaymentProof} />}
        {!isBuy && <DetailRow label="روش دریافت" value={receiveLabel} />}
        {!isBuy && payoutInfo && <DetailRow label="معلومات حساب دریافت" value={payoutInfo} mono />}
        {!isBuy && proofLabel && <DetailRow label="اثبات تراکنش" value={proofLabel} mono />}
        {inPersonCode && <DetailRow label="کد مراجعهٔ حضوری" value={inPersonCode} mono />}
        <DetailRow label="نرخ دالر" value={`${Number(quote?.usd_rate || 0).toLocaleString()} افغانی`} mono />
        {isBuy && Number(quote?.fee_afn || 0) > 0 && <DetailRow label="کارمزد" value={`${Number(quote.fee_afn).toLocaleString()} افغانی`} mono />}
      </div>

      <div className="card" style={{ padding: 14 }}>
        <div className="review-section-title"><ShieldCheck size={18} weight="fill" /> پیش‌نمایش کارت مشتری</div>
        {previewLoading && <div className="review-preview-placeholder"><span className="spinner" /></div>}
        {!previewLoading && cardPreviewUrl && <img src={cardPreviewUrl} alt="پیش‌نمایش کارت مشتری" className="review-card-preview" />}
        {!previewLoading && !cardPreviewUrl && <div className="notice warn"><Warning size={16} weight="fill" />پیش‌نمایش کارت در دسترس نیست.</div>}
      </div>

      <div className="notice warn"><Warning size={17} weight="fill" /> پس از تایید، درخواست برای بررسی تیم صراف ثبت می‌شود. شبکه، آدرس و مبلغ را دقیق کنترل کنید.</div>
      <button className={`btn ${isBuy ? "btn-buy" : "btn-sell"}`} onClick={onConfirm} disabled={submitting || previewLoading || !cardPreviewUrl}>{submitting ? <span className="spinner" /> : <><CheckCircle size={18} weight="fill" /> تایید و درخواست {isBuy ? "خرید" : "فروش"} {selectedAsset}</>}</button>
      <button className="btn btn-outline" onClick={onBack} disabled={submitting}><ArrowRight size={17} /> بازگشت و اصلاح معلومات</button>
    </div>
  );
}
