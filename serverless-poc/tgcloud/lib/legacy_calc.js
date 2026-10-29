// Original handlers/{converter,currency,gold,silver}.py free-form amount
// entry, carried across Telegram Serverless invocations with ForceReply.
// This does not persist financial transactions or create a new ledger.
import { api } from 'sdk';
import { getReferenceRates,convertUsingAfnRates } from './reference_rates.js';
import { getMetalPrice,metalBreakdown } from './metals.js';
import { hasValidCurrency,validKarat,codeLabel } from './legacy_menus.js';
const money=(v,d=2)=>Number(v).toLocaleString('en-US',
 {minimumFractionDigits:d,maximumFractionDigits:d});
export function parseOriginalCalcReply(message){
 const prompt=String(message?.reply_to_message?.text||'');
 const m=/\[(currency|converter|gold|silver):([a-zA-Z0-9:]+)\]\s*$/.exec(prompt);
 if(!m)return null;
 const raw=String(message.text||'').trim().replace(',','.');
 const amount=/^\d+(?:\.\d+)?$/.test(raw)?Number(raw):NaN;
 return {kind:m[1],args:m[2].split(':'),amount};
}
export async function handleOriginalCalcReply(message){
 const input=parseOriginalCalcReply(message);
 if(!input)return false;
 const chat=message?.chat?.id;
 if(!Number.isSafeInteger(chat)||chat!==message?.from?.id)return false;
 const {kind,args,amount}=input;
 if(!Number.isFinite(amount)||amount<=0||amount>1e9){
  await api.sendMessage({chat_id:chat,text:'⚠️ لطفاً یک عدد مثبت معتبر بنویسید (مثال: 100).'});
  return true;
 }
 try{
  let text;
  if(kind==='converter'){
   const [from,to]=args;
   if(!hasValidCurrency(from)||!hasValidCurrency(to)||from===to)throw Error('ارز معتبر نیست.');
   const {rates}=await getReferenceRates();
   const {result,unit}=convertUsingAfnRates(rates,from,to,amount);
   text='🔄 نتیجهٔ تبدیل\n'+money(amount)+' '+codeLabel(from)+' = '+
    money(result,4)+' '+codeLabel(to)+'\nنرخ واحد: '+money(unit,6);
  }else if(kind==='currency'){
   if(args.length!==1||!hasValidCurrency(args[0]))throw Error('ارز نامعتبر است.');
   const {rates}=await getReferenceRates();
   const rate=rates[args[0]];
   if(!rate)throw Error('نرخ معتبر وجود ندارد.');
   text='🧮 نتیجهٔ محاسبهٔ '+codeLabel(args[0])+
    '\nمقدار: '+money(amount)+'\nمعادل مرجع جهانی: '+money(amount*rate,1)+' افغانی';
  }else {
   const mode=args[0],symbol=kind==='gold'?'XAU':'XAG';
   const karat=kind==='gold'?Number(args[1]):24;
   if(!['buy','sell'].includes(mode)||!validKarat(karat))throw Error('عیار یا نوع معامله نامعتبر است.');
   const [r,m]=await Promise.all([getReferenceRates(),getMetalPrice(symbol)]);
   const row=metalBreakdown(symbol,m.price,r.rates.usd).find(x=>x.karat===karat);
   if(!row)throw Error('نرخ عیار موجود نیست.');
   // Original config.py default percentages. These are calculator outputs,
   // NOT executable trading quotes.
   const pct=mode==='buy'?5:2;
   const base=amount*row.afnGram,final=base*(mode==='buy'?1+pct/100:1-pct/100);
   text='🧮 نتیجهٔ محاسبهٔ '+(mode==='buy'?'خرید':'فروش')+
    (symbol==='XAU'?' طلا':' نقره')+'\nعیار: '+karat+
    ' | مقدار: '+money(amount)+' گرم\nقیمت پایه: '+money(base,1)+
    ' افغانی\n'+(mode==='buy'?'اجرت ساخت':'کسر صرافی')+
    ': '+pct+'٪\nمبلغ نهایی: '+money(final,1)+' افغانی';
  }
  await api.sendMessage({chat_id:chat,text});
 }catch(error){
  await api.sendMessage({chat_id:chat,text:'⚠️ '+String(error?.message||'محاسبه ناموفق بود.')});
 }
 return true;
}
