import { db } from 'sdk';
import { nativeQuotes } from '../schema.js';
import { actor, requireFinancialWrites } from '../lib/native_auth.js';
import { localUsdQuote, publicQuote } from '../lib/native_pricing.js';

export default async function (input,ctx) {
  const user=actor(ctx);
  requireFinancialWrites();
  const p=await localUsdQuote(input?.action,input?.asset,input?.amount);
  const [quote]=await db.insert(nativeQuotes).values({
    userId:user.id,action:p.action,asset:p.asset,
    amountCents:p.amountCents,usdRateBasisPoints:p.ratePoints,
    totalAfnTenth:p.totalAfnTenth,totalUsdCents:p.totalUsdCents,
    pricingJson:JSON.stringify(p),source:p.source,expiresAt:p.expiresAt,
    status:'active',createdAt:new Date().toISOString(),
  }).returning().run();
  return publicQuote(p,quote.id);
}
