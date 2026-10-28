// Test-only Mini App RPC. Telegram validates Mini App initData BEFORE this handler.
// No Supabase credentials, financial operations, payment handlers or PII are exposed.
import { getReferenceRates } from '../lib/reference_rates.js';
import { getMetalPrice, metalBreakdown } from '../lib/metals.js';
import { getCryptoPrices } from '../lib/cryptos.js';
import { CURRENCIES, VALID_CODES } from '../lib/currencies.js';

export default async function (input, ctx) {
  // Defense in depth. The platform authenticates endpoint callers.
  const userId = ctx?.initData?.user?.id;
  if (!Number.isSafeInteger(userId) || userId <= 0) {
    throw new Error('Unauthorized Mini App call');
  }
  const kind = String(input?.kind || '').trim().toLowerCase();
  if (kind === 'currencies') {
    const { rates, source, fetchedAt } = await getReferenceRates();
    return {
      kind, source, fetchedAt, isReferenceOnly: true,
      items: VALID_CODES
        .filter(code => Number.isFinite(rates[code]))
        .map(code => ({
          code: code.toUpperCase(),
          name: CURRENCIES[code][1],
          flag: CURRENCIES[code][0],
          afnPerUnit: rates[code],
        })),
    };
  }
  if (kind === 'gold' || kind === 'silver') {
    const symbol = kind === 'gold' ? 'XAU' : 'XAG';
    const [rateResult, metal] = await Promise.all([
      getReferenceRates(), getMetalPrice(symbol),
    ]);
    return {
      kind, source: `${metal.source} + ${rateResult.source}`,
      fetchedAt: rateResult.fetchedAt, isReferenceOnly: true,
      usdPerTroyOunce: metal.price,
      items: metalBreakdown(symbol, metal.price, rateResult.rates.usd),
    };
  }
  if (kind === 'crypto') {
    const { prices, source } = await getCryptoPrices();
    return {
      kind, source, fetchedAt: new Date().toISOString(), isReferenceOnly: true,
      items: Object.entries(prices).map(([code, usd]) => ({
        code: code.toUpperCase(), usd,
      })),
    };
  }
  // Validate user input explicitly; no writes or financial trade operations.
  throw new Error('Unsupported read-only market kind');
}
