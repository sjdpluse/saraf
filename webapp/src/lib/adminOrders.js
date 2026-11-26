export const statusLabels = {
  pending: 'در انتظار بررسی', confirmed: 'آمادهٔ تسویه',
  completed: 'تکمیل‌شده', cancelled: 'لغوشده', rejected: 'ردشده',
};
export const riskLabels = {low: 'ریسک پایین', medium: 'ریسک متوسط', high: 'ریسک بالا'};
export const amount = value => value == null || value === '' || !Number.isFinite(Number(value))
  ? '—' : Number(value).toLocaleString('fa-AF', {maximumFractionDigits: 6});

export function orderCode(order) {
  return (order.asset || 'USDT') + '-' + String(order.id).padStart(5, '0');
}

export function orderNumber(value) {
  const digits = String(value).trim().replace(/[۰-۹]/g, c => c.charCodeAt(0) - 0x6f0)
    .replace(/[٠-٩]/g, c => c.charCodeAt(0) - 0x660);
  const match = /^(?:(?:USDT|USDC)-)?(\d{1,16})$/i.exec(digits);
  const id = match && Number(match[1]);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

const kabul = new Intl.DateTimeFormat('fa-AF', {
  timeZone: 'Asia/Kabul', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
});
export function kabulTime(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : kabul.format(date);
}
