import { actor } from '../lib/native_auth.js';
import { remittanceQuote } from '../lib/native_remittances.js';
export default async function(input,ctx) {
  actor(ctx);
  const quoted=await remittanceQuote(input);
  const { _privateAmountCents,_privateRatePoints,_privatePayoutTenth,...publicResult }=quoted;
  return publicResult;
}
