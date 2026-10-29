// Saraf decimal arithmetic at monetary boundaries.
// All amounts are positive bounded integers in minor units, never persisted as float.
export function parseMinor(value, scale=2) {
  const raw=String(value ?? '').trim();
  if (!/^(?:0|[1-9]\d{0,8})(?:\.\d{1,6})?$/.test(raw))
    throw new Error('Invalid money amount');
  const parts=raw.split('.');
  const base=BigInt(parts[0]);
  const fract=parts[1] || '';
  const divisor=10n ** BigInt(scale);
  const scaled=BigInt((fract.padEnd(scale + 1,'0')).slice(0, scale + 1));
  const rounded=(scaled + 5n) / 10n;
  const units=base*divisor+rounded;
  if (units > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('Amount overflow');
  return Number(units);
}
export function roundHalfUp(n, d) {
  if (typeof n !== 'bigint' || typeof d !== 'bigint' || d <= 0n || n < 0n)
    throw new Error('Invalid positive integer ratio');
  return (n*2n+d)/(2n*d);
}
export function toMoneyCents(value) {
  const n=parseMinor(value,2);
  if(n<=0 || n>1_000_000)throw new Error('Amount out of permitted bounds');
  return n;
}
export function rateToBasisPoints(value) {
  const points=parseMinor(value,4);
  if(points<=0 || points>10_000_000)throw new Error('Invalid USD/AFN rate');
  return points;
}
export function afnTenthFor(amountCents, usdRateBasisPoints) {
  // cents/100 * rateBasisPoints/10_000 -> tenths => /100_000
  return Number(roundHalfUp(BigInt(amountCents)*BigInt(usdRateBasisPoints),100_000n));
}
export const cents = n => n/100;
export const tenths = n => n/10;
export function buyPricing(amountCents, ratePoints) {
  // Local market pricing, same economics as Python usdt_service.py:
  // market margin=max($2, 2.5%), supplier 50%, Saraf 30%, discount 20%.
  const rawMargin=roundHalfUp(BigInt(amountCents)*25n,1000n);
  const margin=Number(rawMargin > 200n ? rawMargin : 200n);
  const supplier=Number(roundHalfUp(BigInt(margin)*5n,10n));
  const saraf=Number(roundHalfUp(BigInt(margin)*3n,10n));
  const discount=margin-supplier-saraf;
  const totalUsdCents=amountCents+supplier+saraf;
  return {
    marginCents: margin, supplierCents: supplier, sarafCents: saraf,
    discountCents: discount, totalUsdCents,
    totalAfnTenth: afnTenthFor(totalUsdCents, ratePoints),
  };
}
