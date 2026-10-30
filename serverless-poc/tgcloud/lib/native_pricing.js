// Financial quote engine port of usdt_service.py. No external secrets.
// The local Sarai Shahzada rate must be available; global fallback is not
// accepted for money settlement. Prices are fixed at the time of the quote.
import { getLocalMarketRates } from './local_market_service.js';
import { MIN_STABLECOIN_USD, MAX_STABLECOIN_USD, QUOTE_TTL_SECONDS } from './native_config.js';
import { toMoneyCents, rateToBasisPoints, afnTenthFor, buyPricing, cents, tenths } from './native_money.js';
import { invalid, checkAction, checkAsset } from './native_auth.js';
export function validateAmount(raw) {
  let minor;
  try { minor=toMoneyCents(raw); }
  catch (_) { invalid('مقدار سفارش معتبر نیست.', 'INVALID_AMOUNT'); }
  if (minor < MIN_STABLECOIN_USD*100 || minor > MAX_STABLECOIN_USD*100)
    invalid('مقدار خارج از محدوده سفارش است.', 'AMOUNT_OUT_OF_RANGE');
  return minor;
}
export async function localUsdQuote(action, asset, amount) {
  const side=checkAction(action), coin=checkAsset(asset);
  const amountCents=validateAmount(amount);
  const { markets, fetchedAt }=await getLocalMarketRates();
  const row=markets?.sarai_shahzada?.usd;
  if (!row || !Number.isFinite(row.buy) || !Number.isFinite(row.sell) ||
      row.buy <= 0 || row.sell < row.buy) {
    invalid('نرخ معتبر و تازه سرای شهزاده موجود نیست.', 'MARKET_UNAVAILABLE');
  }
  // Sell uses Saraf quote (local mid less 0.3%), buy uses local ask.
  const usdRate=side==='buy' ? row.sell : (row.buy+row.sell)/2*0.997;
  let points;
  try {points=rateToBasisPoints(usdRate);}
  catch (_) {invalid('نرخ دالر معتبر نیست.', 'MARKET_UNAVAILABLE');}
  const priced=side==='buy' ? buyPricing(amountCents, points) : {
    totalUsdCents:amountCents, totalAfnTenth:afnTenthFor(amountCents,points),
    marginCents:0,supplierCents:0,sarafCents:0,discountCents:0,
  };
  const expiresAt=Math.floor(Date.now()/1000)+QUOTE_TTL_SECONDS;
  return { action:side,asset:coin,amountCents, ratePoints:points,
    totalAfnTenth:priced.totalAfnTenth,totalUsdCents:priced.totalUsdCents,
    expiresAt, source:'sarafi.af:sarai_shahzada', sourceFetchedAt:fetchedAt,
    ...priced,
  };
}
export function publicQuote(p, id=null) {
  const amount=cents(p.amountCents), usd_rate=p.ratePoints/10000;
  const base_afn=tenths(afnTenthFor(p.amountCents,p.ratePoints));
  return {
    quote_id:id,action:p.action,asset:p.asset,amount,
    usd_rate,base_afn,total_afn:tenths(p.totalAfnTenth),
    total_usd:cents(p.totalUsdCents),payable_usd:cents(p.totalUsdCents),
    receivable_usd:cents(p.totalUsdCents),fee_afn:0,fee_percent:0,
    market_margin_usd:cents(p.marginCents),supplier_profit_usd:cents(p.supplierCents),
    saraf_profit_usd:cents(p.sarafCents),customer_discount_usd:cents(p.discountCents),
    pricing_model:'local_margin_share_50_30_20',basis:'local',
    expires_at:new Date(p.expiresAt*1000).toISOString(),source:p.source,
  };
}
