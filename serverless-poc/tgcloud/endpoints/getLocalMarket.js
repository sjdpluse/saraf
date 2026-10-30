// The original React Saraf market view calls this endpoint through Telegram RPC.
// No price from this endpoint can be used to create an order.
import { getLocalMarketRates } from '../lib/local_market_service.js';
export default async function (_input, ctx) {
  const id = ctx?.initData?.user?.id;
  if (!Number.isSafeInteger(id) || id <= 0) throw new Error('Unauthorized');
  const { markets, labels, fetchedAt, source } = await getLocalMarketRates();
  const rows = ['sarai_shahzada', 'khorasan_market', 'da_afg_bank']
    .flatMap(market =>
      Object.entries(markets[market] || {}).map(([code, quote]) => ({
        market, marketLabel: labels[market], code: code.toUpperCase(),
        buy: quote.buy, sell: quote.sell,
      })),
    );
  return { kind: 'local', source, fetchedAt, isReferenceOnly: true, items: rows };
}
