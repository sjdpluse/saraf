export const REMITTANCE_STATUS = {
  awaiting_transfer: "منتظر انتقال کریپتو",
  transfer_submitted: "در حال تأیید بلاکچین",
  payout_ready: "آماده پرداخت",
  completed: "تکمیل شده",
  on_hold: "در حال بررسی",
  cancelled: "لغو شده",
};
export function remittanceStatusClass(status) {
  return status === "completed" ? "completed" : status === "cancelled" ? "cancelled" : status === "payout_ready" ? "confirmed" : "pending";
}
export function formatAmount(value, digits = 2) {
  return Number(value || 0).toLocaleString("fa-AF", { maximumFractionDigits: digits });
}
