// Mirrors gold_service.py / silver_service.py (display-only, no buy/sell fees).
import { fetch } from 'sdk';
import { isPositive, GOLD_KARATS } from './currencies.js';
export const GRAMS_PER_TROY_OUNCE = 31.1034768;
export const GRAMS_PER_METHQAL = 4.608;
const round = (n, digits) => Number(n.toFixed(digits));

export function parseMetalPrice(data) {
  for (const key of ['price', 'rate', 'value']) {
    const price = Number(data?.[key]);
    if (isPositive(price)) return price;
  }
  throw new Error('قیمت معتبر دریافت نشد.');
}
export async function getMetalPrice(symbol, http = fetch) {
  if (symbol !== 'XAU' && symbol !== 'XAG') throw new Error('نماد فلز نامعتبر است.');
  const response = await http(`https://api.gold-api.com/price/${symbol}`);
  if (!response?.ok) throw new Error('منبع نرخ فلز در دسترس نیست.');
  return { price: parseMetalPrice(await response.json()), source: 'gold-api.com' };
}
export function metalBreakdown(symbol, usdPerOz, afnPerUsd) {
  if (!['XAU', 'XAG'].includes(symbol) || !isPositive(usdPerOz) || !isPositive(afnPerUsd))
    throw new Error('نرخ فلز یا ارز نامعتبر است.');
  const afnGram24 = usdPerOz * afnPerUsd / GRAMS_PER_TROY_OUNCE;
  const usdGram24 = usdPerOz / GRAMS_PER_TROY_OUNCE;
  const karats = symbol === 'XAU' ? GOLD_KARATS : [24];
  return karats.map(karat => ({
    karat,
    afnGram: round(afnGram24 * karat / 24, 1),
    usdGram: round(usdGram24 * karat / 24, 2),
    afnMethqal: round(afnGram24 * karat / 24 * GRAMS_PER_METHQAL, 1),
    usdMethqal: round(usdGram24 * karat / 24 * GRAMS_PER_METHQAL, 2),
  }));
}
