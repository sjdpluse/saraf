// Original main:services/rate_engine.py quote basis and spread configuration.
// Read-only; no checkout, no order writes, and no Railway endpoint.
import { fetch } from 'sdk';
import {getReferenceRates} from './reference_rates.js';
import {getLocalMarketRates} from './local_market_service.js';
import {selectOriginalBasis} from './legacy_rate_engine.js';
import {VALID_CODES} from './currencies.js';

const URL='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-public-history?mode=spreads';
export async function originalSpreads(http=fetch){
 try{
  const res=await http(URL,{headers:{Accept:'application/json'}});
  if(!res?.ok)return {};
  const data=await res.json();
  if(!data?.spreads||typeof data.spreads!=='object')return {};
  const spreads={};
  for(const code of VALID_CODES){
   const rate=data.spreads[code],n=Number(rate);
   if(rate!=null&&Number.isFinite(n)&&n>=0&&n<=20)spreads[code]=n;
  }
  return spreads;
 }catch{return {};}
}
export async function originalLiveQuotes(codes=VALID_CODES){
 const refs=await getReferenceRates().catch(()=>({rates:{}}));
 const [markets,spread]=await Promise.all([
   getLocalMarketRates().then(x=>x.markets).catch(()=>({})),
   originalSpreads(),
 ]);
 const result={};
 for(const code of codes){
  if(!VALID_CODES.includes(code))continue;
  try{result[code]=selectOriginalBasis(code,refs.rates,markets,spread);}
  catch{/* Matches original rate_engine.get_full_quotes: skip unavailable pair. */}
 }
 return result;
}
export const originalCurrencyUnit=code=>
  ['pkr','irr','inr'].includes(code)?1000:1;
// Keep the historic export name for internal callers; source of truth is
// the 1:1 original Railway-format presentation module.
export {originalCurrencyText} from './legacy_display.js';
