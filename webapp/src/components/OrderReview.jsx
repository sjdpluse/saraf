import { CheckCircle, ShieldCheck, Warning, ArrowRight } from "@phosphor-icons/react";
import { assetLogo, normalizeAsset } from "../lib/brand";

function Row({ label, value, mono = false }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(96px, 0.8fr) minmax(0, 1.5fr)", gap: 12, padding: "11px 0", borderBottom: "1px solid var(--color-border)" }}>
      <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}>{label}</span>
      <span className={mono ? "num" : ""} style={{ fontWeight: 700, fontSize: 12.5, overflowWrap: "anywhere", textAlign: "left" }}>{value || "—"}</span>
    </div>
  );
}

export default function OrderReview({
  action,
  asset,
  amount,
  quote,
  exchange,
  network,
  walletAddress,
  paymentLabel,
  receiveLabel,
  proofLabel,
  cardPreviewUrl,
  previewLoading,
  onBack,
  onConfirm,
  submitting,
}) {
  const selectedAsset = normalizeAsset(asset);
  const isBuy = action === "buy";
  const accent = isBuy ? "var(--color-buy)" : "var(--color-sell)";
  const afn = Number(quote?.total_afn || 0);
  const usd = Number(quote?.total_usd ?? amount ?? 0);

  return (
    <div className="animate-in" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="card" style={{ padding: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 44, height: 44, borderRadius: 14, background: "#fff", display: "grid", placeItems: "center", boxShadow: "0 2px 10px rgba(0,0,0,.06)" }}>
              <img src={assetLogo(selectedAsset)} alt={selectedAsset} style={{ width: 34, height: 34, objectFit: "contain", borderRadius: "50%" }} />
            </span>
            <div>
              <div style={{ fontWeight: 850, fontSize: 16 }}>بررسی نهایی درخواست</div>
              <div style={{ color: "var(--color-text-muted)", fontSize: 11.5, marginTop: 2 }}>
                پیش از ثبت، تمام معلومات را یک‌بار بررسی کنید
              </div>
            </div>
          </div>
          <span className="num" style={{ color: accent, background: isBuy ? "var(--color-buy-bg)" : "var(--color-sell-bg)", padding: "6px 10px", borderRadius: 999, fontWeight: 800, fontSize: 11.5 }}>
            {isBuy ? "BUY" : "SELL"} {selectedAsset}
          </span>
        </div>

        <div className="quote-total" style={{ background: "var(--color-bg-elevated)", borderRadius: 18, padding: 14, marginBottom: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10 }}>
            <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}>مقدار معامله</span>
            <strong className="num" style={{ fontSize: 20, color: accent }}>{Number(amount).toLocaleString()} {selectedAsset}</strong>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
            <div style={{ background: "#fff", border: "1px solid var(--color-border)", borderRadius: 14, padding: 11 }}>
              <div style={{ color: "var(--color-text-muted)", fontSize: 10.5 }}>ارزش دالری</div>
              <div className="num" style={{ fontWeight: 800, marginTop: 3 }}>${usd.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
            </div>
            <div style={{ background: "#fff", border: "1px solid var(--color-border)", borderRadius: 14, padding: 11 }}>
              <div style={{ color: "var(--color-text-muted)", fontSize: 10.5 }}>{isBuy ? "مبلغ قابل پرداخت" : "مبلغ قابل دریافت"}</div>
              <div className="num" style={{ fontWeight: 800, marginTop: 3 }}>{afn.toLocaleString()} ؋</div>
            </div>
          </div>
        </div>

        <Row label="نوع درخواست" value={`${isBuy ? "خرید" : "فروش"} ${selectedAsset}`} />
        <Row label="صرافی / کیف پول" value={exchange} />
        <Row label="شبکه" value={network} mono />
        {walletAddress && <Row label={isBuy ? "آدرس دریافت" : "آدرس واریز صراف"} value={walletAddress} mono />}
        {isBuy && <Row label="روش پرداخت" value={paymentLabel} />}
        {!isBuy && <Row label="روش دریافت" value={receiveLabel} />}
        {!isBuy && proofLabel && <Row label="اثبات تراکنش" value={proofLabel} mono />}
        <Row label="نرخ دالر" value={`${Number(quote?.usd_rate || 0).toLocaleString()} افغانی`} mono />
        {isBuy && Number(quote?.fee_afn || 0) > 0 && <Row label="کارمزد" value={`${Number(quote.fee_afn).toLocaleString()} افغانی`} mono />}
      </div>

      <div className="card" style={{ padding: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, fontWeight: 800, fontSize: 13 }}>
          <ShieldCheck size={18} weight="fill" style={{ color: "var(--color-primary)" }} />
          پیش‌نمایش کارت مشتری
        </div>
        {previewLoading && (
          <div style={{ minHeight: 180, display: "grid", placeItems: "center", background: "var(--color-bg-elevated)", borderRadius: 16 }}>
            <span className="spinner" />
          </div>
        )}
        {!previewLoading && cardPreviewUrl && (
          <img src={cardPreviewUrl} alt="پیش‌نمایش کارت مشتری" style={{ width: "100%", display: "block", borderRadius: 16, border: "1px solid var(--color-border)" }} />
        )}
        {!previewLoading && !cardPreviewUrl && (
          <div className="notice warn"><Warning size={16} weight="fill" />پیش‌نمایش کارت در دسترس نیست. معلومات سفارش را بررسی کنید و دوباره تلاش نمایید.</div>
        )}
      </div>

      <div className="notice warn" style={{ alignItems: "flex-start" }}>
        <Warning size={17} weight="fill" style={{ flexShrink: 0, marginTop: 1 }} />
        پس از زدن دکمهٔ تایید، درخواست برای بررسی تیم صراف ثبت می‌شود. شبکه و آدرس ولت را با دقت کنترل کنید.
      </div>

      <button className={`btn ${isBuy ? "btn-buy" : "btn-sell"}`} onClick={onConfirm} disabled={submitting || previewLoading || !cardPreviewUrl}>
        {submitting ? <span className="spinner" /> : <><CheckCircle size={18} weight="fill" /> تایید و درخواست {isBuy ? "خرید" : "فروش"} {selectedAsset}</>}
      </button>
      <button className="btn btn-outline" onClick={onBack} disabled={submitting}>
        <ArrowRight size={17} /> بازگشت و اصلاح معلومات
      </button>
    </div>
  );
}
