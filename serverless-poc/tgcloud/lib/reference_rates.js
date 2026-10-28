// Read-only international reference rates (no local-market spread and no trade quote).
// Port of services/currency_service.py. All returned numbers are AFN per 1 foreign unit.
import { fetch } from 'sdk';
import { VALID_CODES, isPositive } from './currencies.js';

const SOURCES = [
  'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/afn.json',
  'https://latest.currency-api.pages.dev/v1/currencies/afn.json',
  'https://api.exchangerate-api.com/v4/latest/USD',
];
const round4 = value => Math.round((value + Number.EPSILON) * 10000) / 10000;

export function decodeAfnBase(data) {
  const source = data?.afn;
  if (!source || typeof source !== 'object') return null;
  const rates = {};
  for (const code of VALID_CODES) {
    if (isPositive(source[code])) rates[code] = round4(1 / source[code]);
  }
  return isPositive(rates.usd) ? rates : null;
}
export function decodeUsdBase(data) {
  const source = data?.rates;
  const afn = source?.AFN;
  if (!isPositive(afn)) return null;
  const rates = {};
  for (const code of VALID_CODES) {
    const n = source[code.toUpperCase()];
    if (code === 'usd') rates.usd = round4(afn);
    else if (isPositive(n)) rates[code] = round4(afn / n);
  }
  return rates;
}
export async function requestJson(url, http = fetch) {
  const response = await http(url, { headers: { Accept: 'application/json' } });
  if (!response?.ok) throw new Error(`upstream status ${response?.status ?? 'unknown'}`);
  return response.json();
}
export async function getReferenceRates(http = fetch) {
  let lastError;
  for (let i = 0; i < SOURCES.length; i++) {
    try {
      const raw = await requestJson(SOURCES[i], http);
      const rates = i < 2 ? decodeAfnBase(raw) : decodeUsdBase(raw);
      if (rates) {
        return {
          rates, source: i === 2 ? 'exchangerate-api.com' : 'fawazahmed0/currency-api',
          fetchedAt: new Date().toISOString(),
        };
      }
      lastError = new Error('invalid rate response');
    } catch (error) {
      lastError = error;
      console.warn('reference rate source unavailable', i, String(error));
    }
  }
  throw new Error('هیچ منبع نرخ ارز در دسترس نیست.');
}
export function convertUsingAfnRates(rates, from, to, amount) {
  const a = String(from || '').toLowerCase();
  const b = String(to || '').toLowerCase();
  if (!isPositive(amount) || !Number.isFinite(amount) || amount > 1e9)
    throw new Error('مبلغ باید یک عدد مثبت و معتبر باشد.');
  if (a !== 'afn' && (!VALID_CODES.includes(a) || !isPositive(rates[a])))
    throw new Error('ارز مبدأ پشتیبانی نمی‌شود.');
  if (b !== 'afn' && (!VALID_CODES.includes(b) || !isPositive(rates[b])))
    throw new Error('ارز مقصد پشتیبانی نمی‌شود.');
  const unit = (a === 'afn' ? 1 : rates[a]) / (b === 'afn' ? 1 : rates[b]);
  return { result: amount * unit, unit };
}
