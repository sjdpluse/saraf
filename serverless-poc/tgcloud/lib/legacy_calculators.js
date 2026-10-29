// Pure parity port of original main:handlers/currency.py and
// services/{gold,silver}_service.py. Read-only calculators, never order quotes.
export const GRAMS_PER_TROY_OUNCE = 31.1034768;
export const GRAMS_PER_METHQAL = 4.608;
const GOLD_KARATS = [24, 22, 21, 18];
const round = (number, places) => Number(number.toFixed(places));
const positive = n => typeof n === 'number' && Number.isFinite(n) && n > 0;

export function originalCurrencyCalculation(amount, quote) {
  if (!positive(amount)) throw Error('INVALID_AMOUNT');
  const saraf = quote?.saraf_quote;
  if (!positive(saraf?.buy) || !positive(saraf?.sell))
    throw Error('SARAF_RATE_UNAVAILABLE');
  const pair = rates => ({
    // Original Python: selling foreign currency receives AFN at BUY rate;
    // buying foreign currency pays AFN at SELL rate.
    sell_afn: round(amount * rates.buy, 1),
    buy_afn: round(amount * rates.sell, 1),
  });
  const local = quote?.local;
  return {
    local: positive(local?.buy) && positive(local?.sell) ? pair(local) : null,
    local_market_label: local?.market_label || 'سرای شهزاده (کابل)',
    saraf: pair(saraf),
  };
}

export function metalBreakdown(symbol, usdPerOz, afnPerUsd) {
  if (!['XAU', 'XAG'].includes(symbol) ||
      !positive(usdPerOz) || !positive(afnPerUsd))
    throw Error('INVALID_METAL_PRICE');
  const afnGram24 = usdPerOz * afnPerUsd / GRAMS_PER_TROY_OUNCE;
  const usdGram24 = usdPerOz / GRAMS_PER_TROY_OUNCE;
  return (symbol === 'XAU' ? GOLD_KARATS : [24]).map(karat => {
    const factor = karat / 24;
    const afn = afnGram24 * factor, usd = usdGram24 * factor;
    return {
      karat,
      // The original gold service uses 2 USD decimals, silver uses 4.
      afnGram: round(afn, 1),
      usdGram: round(usd, symbol === 'XAG' ? 4 : 2),
      afnMethqal: round(afn * GRAMS_PER_METHQAL, 1),
      usdMethqal: round(usd * GRAMS_PER_METHQAL, 2),
    };
  });
}

export function originalMetalCalculation(symbol, rows, karat, grams, mode) {
  if (!['XAU','XAG'].includes(symbol) || !['buy','sell'].includes(mode) ||
      !positive(grams) || (symbol === 'XAG' && karat !== 24) ||
      (symbol === 'XAU' && !GOLD_KARATS.includes(karat)))
    throw Error('INVALID_METAL_CALCULATION');
  const row = rows.find(x => x.karat === karat);
  if (!row || !positive(row.afnGram) || !positive(row.usdGram))
    throw Error('METAL_RATE_UNAVAILABLE');
  // The original service calculates from the *rounded per-gram* values,
  // then rounds both base and final amounts (not the unrounded ounce rate).
  const pct = mode === 'buy' ? 5 : 2; // ORIGINAL config.py defaults
  const factor = mode === 'buy' ? 1 + pct / 100 : 1 - pct / 100;
  return {
    karat, grams, is_buying: mode === 'buy',
    base_afn: round(row.afnGram * grams, 1),
    base_usd: round(row.usdGram * grams, 2),
    adjustment_pct: pct,
    adjustment_label: mode === 'buy' ? 'اجرت ساخت' : 'کسر صرافی',
    final_afn: round(row.afnGram * grams * factor, 1),
    final_usd: round(row.usdGram * grams * factor, 2),
  };
}
