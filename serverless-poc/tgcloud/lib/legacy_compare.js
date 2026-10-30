// Exact original compare.py local-first historical logic.
// Uses original canonical Supabase market history (public price data only).
import { fetch } from 'sdk';
import {getReferenceRates} from './reference_rates.js';
import {getLocalMarketRates} from './local_market_service.js';
import {getMetalPrice,metalBreakdown} from './metals.js';
import {selectOriginalBasis,historicalOriginalBasis,applyOriginalSpread}
 from './legacy_rate_engine.js';
import {codeLabel} from './legacy_menus.js';

const ENDPOINT='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-public-history';
const PERIODS={1:'۲۴ ساعت گذشته',7:'هفتهٔ گذشته',30:'ماه گذشته',90:'سه ماه گذشته'};
const BASIS={local:'بازار واقعی صرافی‌های کابل (سرای شهزاده)',
 reference:'بازار آزاد جهانی'};
const fmt=(n,d=2)=>Number(n).toLocaleString('en-US',
 {minimumFractionDigits:d,maximumFractionDigits:d});
export async function fetchOriginalHistory(target,days,http=fetch){
 if(!['usd','eur','gbp','pkr','irr','aed','inr','sar','try','cny',
   'aud','cad','chf','sek','gold'].includes(target)
   ||![1,7,30,90].includes(Number(days)))throw Error('INVALID_COMPARE_REQUEST');
 const response=await http(ENDPOINT+'?target='+target+'&days='+days,
  {headers:{Accept:'application/json'}});
 if(!response?.ok)throw Error('HISTORY_SERVICE_UNAVAILABLE');
 const data=await response.json();
 if(data?.target!==target||Number(data.days)!==Number(days))
  throw Error('INVALID_HISTORICAL_RESPONSE');
 return data;
}
export function formatOriginalCompare(target,days,historical,current){
 const period=PERIODS[days];
 if(!period)throw Error('INVALID_COMPARE_PERIOD');
 if(target==='gold'){
  const old=Number(historical?.reference_old);
  const now=Number(current?.gold);
  if(!(now>0))throw Error('GOLD_RATE_NOT_AVAILABLE');
  if(!(old>0))return '📊 🥇 طلا (عیار ۲۴)\n\nنرخ فعلی: '+
   fmt(now,1)+' افغانی به ازای هر گرم\n\n'+
   'هنوز دادهٔ تاریخی کافی برای این بازهٔ زمانی ذخیره نشده است.';
  const change=(now-old)/old*100;
  return '📊 🥇 طلا (عیار ۲۴) — مقایسه با '+period+
   '\n\n🕰 '+period+': '+fmt(old,1)+' افغانی (هر گرم)'+
   '\n⏱ اکنون: '+fmt(now,1)+' افغانی'+
   '\nتغییر: '+(change>0?'🔺':change<0?'🔻':'⏸️')+
   ' '+(change>=0?'+':'')+fmt(change,2)+'٪';
 }
 const saved=historical?.spread_percent==null?{}:
  {[target]:Number(historical.spread_percent)};
 const quote=selectOriginalBasis(target,current.reference,current.local||{},saved);
 const old=historicalOriginalBasis(historical?.old_local,historical?.reference_old);
 const name=codeLabel(target);
 if(!(old.rate>0))return '📊 '+name+'\n\nخرید فعلی: '+
  fmt(quote.saraf_quote.buy)+' | فروش فعلی: '+
  fmt(quote.saraf_quote.sell)+' افغانی\n\n'+
  'هنوز دادهٔ تاریخی کافی برای این بازهٔ زمانی ذخیره نشده است.';
 const oldQuote=applyOriginalSpread(old.rate,target,saved);
 const change=(quote.saraf_quote.basis_rate-old.rate)/old.rate*100;
 return '📊 '+name+' — مقایسه با '+period+
  '\n\n🕰 '+period+'\nخرید: '+fmt(oldQuote.buy)+
  ' | فروش: '+fmt(oldQuote.sell)+' افغانی'+
  '\n\n⏱ اکنون\nخرید: '+fmt(quote.saraf_quote.buy)+
  ' | فروش: '+fmt(quote.saraf_quote.sell)+' افغانی'+
  '\nتغییر: '+(change>0?'🔺':change<0?'🔻':'⏸️')+
  ' '+(change>=0?'+':'')+fmt(change,2)+'٪'+
  '\n(بر اساس '+(BASIS[quote.saraf_quote.basis]||quote.saraf_quote.basis)+')'+
  (old.basis!==quote.saraf_quote.basis?
   '\n⚠️ منبع نرخ فعلی و گذشته متفاوت است.':'');
}
export async function getOriginalCompareReport(target,days){
 const history=await fetchOriginalHistory(target,days);
 if(target==='gold'){
  const [{rates},metal]=await Promise.all([
   getReferenceRates(),getMetalPrice('XAU')]);
  const rows=metalBreakdown('XAU',metal.price,rates.usd);
  return formatOriginalCompare(target,days,history,{
   gold:rows.find(r=>r.karat===24)?.afnGram});
 }
 const {rates}=await getReferenceRates().catch(()=>({rates:{}}));
 let market={};
 try{market=(await getLocalMarketRates()).markets;}catch{
  // Original rate_engine.py falls back to global reference source.
 }
 return formatOriginalCompare(target,days,history,{reference:rates,local:market});
}
