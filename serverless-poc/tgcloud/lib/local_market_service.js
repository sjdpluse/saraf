// Live market data, not an executable Saraf quote. No stale response is accepted.
import { fetch } from 'sdk';
import { parseLocalMarketHtml, MARKET_LABELS } from './local_market_parser.js';

export async function getLocalMarketRates() {
  const response = await fetch('https://sarafi.af/fa/exchange-rates/sarai-shahzada', {
    headers: {
      'Accept-Language': 'fa,en;q=0.8',
      'User-Agent': 'Mozilla/5.0 Saraf/1.0',
    },
  });
  if (!response?.ok) throw new Error('بازار محلی در دسترس نیست.');
  const html = await response.text();
  const markets = parseLocalMarketHtml(html);
  if (!Object.values(markets).some(market => Object.keys(market).length)) {
    throw new Error('هیچ نرخی از جدول سرای شهزاده دریافت نشد.');
  }
  return { markets, labels: MARKET_LABELS, fetchedAt: new Date().toISOString(),
    source: 'sarafi.af (public, informational)', isReferenceOnly: true };
}
