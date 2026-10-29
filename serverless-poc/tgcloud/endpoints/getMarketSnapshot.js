// Live, display-only 24h crypto market changes for the ORIGINAL React Mini App.
// No payment or execution quote uses these values. Mirrors services/market_snapshot.py.
import { fetch } from 'sdk';
const IDS = {
  USDT: 'tether', USDC: 'usd-coin', BTC: 'bitcoin', ETH: 'ethereum',
  SOL: 'solana', BNB: 'binancecoin', XRP: 'ripple', TON: 'the-open-network',
  ADA: 'cardano', DOGE: 'dogecoin', TRX: 'tron', AVAX: 'avalanche-2',
  DOT: 'polkadot', LINK: 'chainlink', LTC: 'litecoin', BCH: 'bitcoin-cash',
  XLM: 'stellar', SHIB: 'shiba-inu', UNI: 'uniswap', ATOM: 'cosmos',
};
const valid = value => typeof value === 'number' && Number.isFinite(value);

export default async function (_input, ctx) {
  if (!Number.isSafeInteger(ctx?.initData?.user?.id) || ctx.initData.user.id <= 0) {
    throw new Error('Unauthorized');
  }
  const url = 'https://api.coingecko.com/api/v3/simple/price?ids=' +
    encodeURIComponent(Object.values(IDS).join(',')) +
    '&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true';
  const now = Date.now() / 1000;
  let payload;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('upstream status ' + response.status);
    payload = await response.json();
  } catch (error) {
    console.warn('CoinGecko 24h market unavailable', String(error));
    return { status: 'unavailable', source: 'CoinGecko', assets: [] };
  }
  if (!payload || typeof payload !== 'object') {
    return { status: 'unavailable', source: 'CoinGecko', assets: [] };
  }
  const assets = Object.entries(IDS).map(([symbol, id]) => {
    const row = payload[id] || {};
    const updatedAt = row.last_updated_at;
    const delta = row.usd_24h_change;
    const age = now - updatedAt;
    return {
      symbol,
      updated_at: valid(updatedAt) ? updatedAt : null,
      change_24h: valid(delta) && valid(updatedAt) && age >= -60 && age <= 900
        ? delta : null,
    };
  });
  return {
    source: 'CoinGecko', assets,
    status: assets.some(item => item.change_24h != null) ? 'fresh' : 'unavailable',
  };
}
