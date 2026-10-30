// Faithful non-transactional calculator replies from the ORIGINAL Python
// bot. State is a Telegram ForceReply to the bot's prompt, not shadow SQLite.
import { api } from 'sdk';
import { getReferenceRates, convertUsingAfnRates } from './reference_rates.js';
import { getMetalPrice, metalBreakdown } from './metals.js';
import { originalLiveQuotes } from './legacy_live_rates.js';
import { originalCurrencyCalculation, originalMetalCalculation } from './legacy_calculators.js';
import { hasValidCurrency, validKarat, codeLabel } from './legacy_menus.js';
const money=(v,d=2)=>Number(v).toLocaleString('en-US',
 {minimumFractionDigits:d,maximumFractionDigits:d});

export function parseOriginalCalcReply(message) {
 const prompt=String(message?.reply_to_message?.text||'');
 const m=/\[(currency|converter|gold|silver):([a-zA-Z0-9:]+)\]\s*$/.exec(prompt);
 if(!m)return null;
 const raw=String(message.text||'').trim().replace(',','.');
 const amount=/^\d+(?:\.\d+)?$/.test(raw)?Number(raw):NaN;
 return {kind:m[1],args:m[2].split(':'),amount};
}
export async function handleOriginalCalcReply(message) {
 const input=parseOriginalCalcReply(message);
 if(!input)return false;
 const chat=message?.chat?.id;
 if(!Number.isSafeInteger(chat)||chat!==message?.from?.id)return false;
 const {kind,args,amount}=input;
 if(!Number.isFinite(amount)||amount<=0||amount>1e9){
  await api.sendMessage({chat_id:chat,text:'⚠️ لطفاً یک عدد مثبت معتبر بنویسید (مثال: 100).'});
  return true;
 }
 try {
  let result;
  if(kind==='converter') {
   const [from,to]=args;
   if(args.length!==2||!hasValidCurrency(from)||!hasValidCurrency(to)||from===to)
     throw Error('ارز معتبر نیست.');
   const {rates}=await getReferenceRates();
   const {result:converted,unit}=convertUsingAfnRates(rates,from,to,amount);
   result='🔄 نتیجهٔ تبدیل\n'+money(amount)+' '+codeLabel(from)+' = '+
    money(converted,4)+' '+codeLabel(to)+'\nنرخ واحد: '+money(unit,6);
  } else if(kind==='currency') {
   if(args.length!==1||!hasValidCurrency(args[0]))throw Error('ارز نامعتبر است.');
   // Original handlers/currency.py uses local Sarai Shahzada bid/ask,
   // plus Saraf's stored spread; NOT the international mid-market reference.
   const quotes=await originalLiveQuotes([args[0]]);
   const q=quotes[args[0]];
   if(!q)throw Error('نرخ ارز در دسترس نیست.');
   const calc=originalCurrencyCalculation(amount,q);
   result='🧮 نتیجهٔ محاسبه — '+money(amount)+' '+codeLabel(args[0])+'\n';
   if(calc.local) {
    result+='\n🏛 بر اساس نرخ '+calc.local_market_label+'\n'+
     'اگر بفروشید: '+money(calc.local.sell_afn,1)+' افغانی\n'+
     'اگر بخرید: '+money(calc.local.buy_afn,1)+' افغانی\n';
   }
   result+='\n💱 بر اساس نرخ صرافی‌های محلی\n'+
    'اگر بفروشید: '+money(calc.saraf.sell_afn,1)+' افغانی\n'+
    'اگر بخرید: '+money(calc.saraf.buy_afn,1)+' افغانی';
  } else {
   const mode=args[0],symbol=kind==='gold'?'XAU':'XAG';
   const karat=kind==='gold'?Number(args[1]):24;
   if(!['buy','sell'].includes(mode)||!validKarat(karat)||
     (kind==='silver'&&args.length!==1)||
     (kind==='gold'&&args.length!==2))throw Error('عیار یا نوع معامله نامعتبر است.');
   const [r,m]=await Promise.all([getReferenceRates(),getMetalPrice(symbol)]);
   const rows=metalBreakdown(symbol,m.price,r.rates.usd);
   const x=originalMetalCalculation(symbol,rows,karat,amount,mode);
   result='🧮 نتیجهٔ محاسبهٔ '+(mode==='buy'?'خرید':'فروش')+
    (symbol==='XAU'?' طلا':' نقره')+'\n'+
    (symbol==='XAU'?'عیار: '+karat+' | ':'')+'مقدار: '+amount+' گرم\n'+
    'قیمت پایه: '+money(x.base_afn,symbol==='XAU'?0:1)+' افغانی ('+
    money(x.base_usd)+'$)\n'+x.adjustment_label+': '+
    money(x.adjustment_pct,1)+'٪\n\n💰 مبلغ نهایی: '+
    money(x.final_afn,symbol==='XAU'?0:1)+' افغانی ('+
    money(x.final_usd)+'$)';
  }
  await api.sendMessage({chat_id:chat,text:result});
 }catch(error) {
  console.warn('Original calculator failed',String(error?.message||'unknown'));
  await api.sendMessage({chat_id:chat,text:'⚠️ محاسبه ناموفق بود؛ نرخ معتبر در دسترس نیست یا معلومات اشتباه است.'});
 }
 return true;
}
