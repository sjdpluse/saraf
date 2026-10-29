// Read-only gold/silver price fetch; the pure calculators mirror the
// original main:services/{gold,silver}_service.py rounding and purity.
import { fetch } from 'sdk';
import { isPositive } from './currencies.js';
export { GRAMS_PER_TROY_OUNCE, GRAMS_PER_METHQAL, metalBreakdown } from './legacy_calculators.js';

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
