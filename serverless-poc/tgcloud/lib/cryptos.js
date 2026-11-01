// Port of CoinGecko/Binance read-only price sources. No execution/trade handling.
import { fetch } from 'sdk';
import { isPositive } from './currencies.js';
const IDS = Object.freeze({
  btc: 'bitcoin', eth: 'ethereum', sol: 'solana',
  bnb: 'binancecoin', xrp: 'ripple', shib: 'shiba-inu',
});
const PAIRS = Object.freeze({
  btc: 'BTCUSDT', eth: 'ETHUSDT', sol: 'SOLUSDT',
  bnb: 'BNBUSDT', xrp: 'XRPUSDT', shib: 'SHIBUSDT',
});
const NAMES = Object.freeze({
  btc: 'بیت‌کوین', eth: 'اتریوم', sol: 'سولانا',
  bnb: 'بایننس‌کوین', xrp: 'ریپل', shib: 'شیبا اینو',
});
export function parseCoinGecko(data) {
  const result = {};
  for (const [symbol, id] of Object.entries(IDS)) {
    const p = data?.[id]?.usd;
    if (isPositive(p)) result[symbol] = p;
  }
  return result;
}
export function parseBinance(data) {
  const byPair = Object.fromEntries(
    Array.isArray(data) ? data.map(p => [p.symbol, Number(p.price)]) : []
  );
  const result = {};
  for (const [symbol, pair] of Object.entries(PAIRS))
    if (isPositive(byPair[pair])) result[symbol] = byPair[pair];
  return result;
}
export async function getCryptoPrices(http = fetch) {
  // Telegram Serverless isolates may not provide the browser URL constructor.
  const cg = 'https://api.coingecko.com/api/v3/simple/price?ids='+
    encodeURIComponent(Object.values(IDS).join(','))+'&vs_currencies=usd';
  const bn = 'https://api.binance.com/api/v3/ticker/price?symbols='+
    encodeURIComponent(JSON.stringify(Object.values(PAIRS)));
  let lastError = null;
  for (const [url, parse, source] of [[cg, parseCoinGecko, 'CoinGecko'], [bn, parseBinance, 'Binance']]) {
    try {
      const response = await http(url);
      if (!response?.ok) throw new Error('HTTP ' + response?.status);
      const prices = parse(await response.json());
      if (Object.keys(prices).length) return { prices, source };
    } catch (error) { lastError = error; console.warn('crypto provider unavailable', source, String(error)); }
  }
  throw new Error('نرخ رمزارزها در دسترس نیست.');
}
export const cryptoLabel = (symbol) => NAMES[symbol] ?? symbol.toUpperCase();
