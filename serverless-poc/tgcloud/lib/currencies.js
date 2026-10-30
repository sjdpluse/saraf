// Mirrors TRACKED_CURRENCIES in config.py; display-only reference prices.
export const CURRENCIES = Object.freeze({
  usd: ['🇺🇸', 'دالر امریکایی'],
  eur: ['🇪🇺', 'یورو'],
  gbp: ['🇬🇧', 'پوند انگلیسی'],
  pkr: ['🇵🇰', 'کلدار پاکستانی'],
  irr: ['🇮🇷', 'تومان ایرانی'],
  aed: ['🇦🇪', 'درهم امارات'],
  inr: ['🇮🇳', 'روپیه هندی'],
  sar: ['🇸🇦', 'ریال سعودی'],
  try: ['🇹🇷', 'لیرهٔ ترکی'],
  cny: ['🇨🇳', 'یوان چین'],
  aud: ['🇦🇺', 'دالر آسترالیا'],
  cad: ['🇨🇦', 'دالر کانادا'],
  chf: ['🇨🇭', 'فرانک سویس'],
  sek: ['🇸🇪', 'کرون سویدن'],
});
export const VALID_CODES = Object.freeze(Object.keys(CURRENCIES));
export const label = (code) => {
  const item = CURRENCIES[code];
  return item ? `${item[0]} ${item[1]}` : String(code).toUpperCase();
};
export const money = (value, digits = 2) =>
  Number(value).toLocaleString('en-US', {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  });
export const isPositive = (value) => typeof value === 'number' &&
  Number.isFinite(value) && value > 0;
export function currencyKeyboard() {
  const rows = [];
  for (let i = 0; i < VALID_CODES.length; i += 2) {
    rows.push(VALID_CODES.slice(i, i + 2)
      .map(code => ({ text: label(code), callback_data: `ref:${code}` })));
  }
  rows.push([{ text: '🔄 نمایش نرخ تمام ارزها', callback_data: 'ref:all' }]);
  return { inline_keyboard: rows };
}
export function mainKeyboard() {
  return {
    keyboard: [
      [{text: '💵 نرخ ارزها'}, {text: '🥇 نرخ طلا'}],
      [{text: '🏛 نرخ بازار کابل'}],
      [{text: '🥈 نرخ نقره'}, {text: '🪙 نرخ رمزارزها'}],
      [{text: '🔄 مبدل ارز جهانی'}, {text: 'ℹ️ درباره ربات'}],
      [{text: '👤 پروفایل'}, {text: '📦 سفارش‌های من'}],
      [{text: '💸 حواله‌های من'}],
    ],
    resize_keyboard: true,
  };
}
export const GOLD_KARATS = Object.freeze([24, 22, 21, 18]);
export const goldKeyboard = () => ({
  inline_keyboard: [
    ...GOLD_KARATS.map(karat => [{ text: `عیار ${karat}`, callback_data: `goldref:${karat}` }]),
    [{text: '🔄 تمام عیارها', callback_data: 'goldref:all'}],
  ],
});
