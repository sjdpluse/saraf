// Presentation-only port of main:handlers/{currency,gold,silver,crypto,start}.py
// and main:persian_date.py. All rates come from existing read-only services.
// No financial ledger, order, webhook, credentials or Railway dependency.
import {CURRENCIES, VALID_CODES} from './currencies.js';
export const DIVIDER='━━━━━━━━━━';
const MONTHS=['حمل','ثور','جوزا','سرطان','اسد','سنبله','میزان','عقرب','قوس','جدی','دلو','حوت'];
const DIGITS='۰۱۲۳۴۵۶۷۸۹';
const pf=s=>String(s).replace(/[0-9]/g,d=>DIGITS[Number(d)]);
export const fmt=(n,d=2)=>Number(n).toLocaleString('en-US',{
 minimumFractionDigits:d,maximumFractionDigits:d});
export const currencyLabel=code=>CURRENCIES[code]
 ? CURRENCIES[code][0]+' '+CURRENCIES[code][1] : String(code).toUpperCase();
export const currencyUnit=code=>['pkr','irr','inr'].includes(code)?1000:1;

// Port of the exact Gregorian-to-Afghan-Jalali algorithm from persian_date.py.
// Explicit UTC+04:30 offset avoids Intl/timeZone/URL browser globals missing
// in Telegram Serverless's V8 runtime.
export function gregorianToJalali(gy,gm,gd){
 const gMonth=[31,28,31,30,31,30,31,31,30,31,30,31];
 const jMonth=[31,31,31,31,31,31,30,30,30,30,30,29];
 const y=gy-1600,m=gm-1,d=gd-1;
 let count=365*y+Math.floor((y+3)/4)-Math.floor((y+99)/100)+Math.floor((y+399)/400);
 for(let i=0;i<m;i++)count+=gMonth[i];
 if(m>1&&(gy%4===0&&gy%100!==0||gy%400===0))count++;
 count+=d;
 let jDays=count-79;
 const jNp=Math.floor(jDays/12053);
 jDays%=12053;
 let jy=979+33*jNp+4*Math.floor(jDays/1461);
 jDays%=1461;
 if(jDays>=366){
  jy+=Math.floor((jDays-1)/365);
  jDays=(jDays-1)%365;
 }
 for(let i=0;i<11;i++){
  if(jDays<jMonth[i])return [jy,i+1,jDays+1];
  jDays-=jMonth[i];
 }
 return [jy,12,jDays+1];
}
export function afghanDateTime(now=new Date()){
 const kabul=new Date(now.getTime()+270*60000);
 const [jy,jm,jd]=gregorianToJalali(kabul.getUTCFullYear(),
  kabul.getUTCMonth()+1,kabul.getUTCDate());
 const h=kabul.getUTCHours();
 const h12=h%12||12;
 const pad=n=>String(n).padStart(2,'0');
 return pf(jd+' '+MONTHS[jm-1]+' '+jy+'  —  '+pad(h12)+':'+
  pad(kabul.getUTCMinutes())+' '+(h<12?'ق.ظ':'ب.ظ'));
}
const scaled=(code,value)=>fmt(Number(value)*currencyUnit(code));
export function originalCurrencyText(code,quote,{withDate=true,forAll=false,date=afghanDateTime()}={}){
 if(!CURRENCIES[code]||!quote?.saraf_quote)throw Error('INVALID_CURRENCY_QUOTE');
 const name=CURRENCIES[code][1],flag=CURRENCIES[code][0];
 const lines=forAll?
  [DIVIDER,flag+' *('+currencyUnit(code)+') '+name+'*','']:
  ['آخرین بروزرسانی امروز؛',date,'',flag+' *('+currencyUnit(code)+') '+name+'*'];
 const local=quote.local;
 if(local&&Number(local.buy)>0&&Number(local.sell)>0){
  lines.push('🏛 *نرخ '+(local.market_label||'سرای شهزاده (کابل)')+'*',
   'خرید: '+scaled(code,local.buy)+'   |   فروش: '+scaled(code,local.sell));
  if(!forAll)lines.push(DIVIDER);
  lines.push('');
 }
 const saraf=quote.saraf_quote;
 lines.push('💱 *نرخ صرافی‌های محلی*',
  'خرید: '+scaled(code,saraf.buy)+'   |   فروش: '+scaled(code,saraf.sell));
 if(!forAll)lines.push(DIVIDER);
 lines.push('');
 if(Number(quote.reference_rate)>0){
  lines.push('🌍 *نرخ بازار آزاد جهانی*',
   scaled(code,quote.reference_rate)+' افغانی');
 }
 if(forAll)lines.push(DIVIDER);
 return lines.join('\n');
}
export function allCurrencyText(quotes,date=afghanDateTime()){
 const codes=VALID_CODES.filter(code=>quotes?.[code]);
 if(!codes.length)return '⚠️ در حال حاضر هیچ نرخی در دسترس نیست.';
 const blocks=codes.map(code=>originalCurrencyText(code,quotes[code],
  {withDate:false,forAll:true,date}));
 // Match original message budget (Telegram maximum message length is 4096).
 const text='💵 *(Saraf) نرخ ارزهای خارجی در برابر پول افغانی امروز — صراف*\n'+
  date+'\n\n'+blocks.join('\n\n');
 if(text.length<=4000)return text;
 // Do not truncate half a currency or leave unbalanced Markdown.
 let remaining='💵 *(Saraf) نرخ ارزهای خارجی در برابر پول افغانی امروز — صراف*\n'+
  date+'\n\n';
 for(const block of blocks){
  if((remaining+block+'\n\n').length>3950)break;
  remaining+=block+'\n\n';
 }
 return remaining.trimEnd()+'\n…';
}
export function goldPriceText(rows,usdPerOz,karat='all'){
 if(!Array.isArray(rows)||!(Number(usdPerOz)>0))throw Error('INVALID_GOLD_DISPLAY');
 const list=karat==='all'?rows:rows.filter(x=>x.karat===Number(karat));
 if(!list.length)throw Error('INVALID_GOLD_KARAT');
 if(karat==='all'){
  return '🥇 *نرخ لحظه‌یی طلا*\n\nقیمت جهانی: *'+fmt(usdPerOz)+
   ' دالر* برای هر اونس تروی\n\n'+
   list.map(r=>'▫️ عیار '+r.karat+': *'+fmt(r.afnGram,0)+
    ' افغانی* ('+fmt(r.usdGram)+'$) به ازای هر گرم — مثقال: '+
    fmt(r.afnMethqal,0)+' افغانی').join('\n');
 }
 const r=list[0];
 return '🥇 *طلای عیار '+r.karat+'*\n\nهر گرم: *'+fmt(r.afnGram,0)+
  ' افغانی* ('+fmt(r.usdGram)+'$)\nهر مثقال: *'+
  fmt(r.afnMethqal,0)+' افغانی* ('+fmt(r.usdMethqal)+'$)';
}
export function silverPriceText(rows,usdPerOz){
 const r=rows?.[0];
 if(!r||!(Number(usdPerOz)>0))throw Error('INVALID_SILVER_DISPLAY');
 return '🥈 *نرخ لحظه‌یی نقره (خالص)*\n\nقیمت جهانی: *'+fmt(usdPerOz)+
  ' دالر* برای هر اونس تروی\n\nهر گرم: *'+fmt(r.afnGram,1)+
  ' افغانی* ('+fmt(r.usdGram,4)+'$)\nهر مثقال: *'+fmt(r.afnMethqal,1)+
  ' افغانی* ('+fmt(r.usdMethqal)+'$)';
}
export function cryptoPriceText(prices,afnPerUsd=null,{date=afghanDateTime(),stale=false}={}){
 const names={btc:'بیت‌کوین',eth:'اتریوم',sol:'سولانا',
  bnb:'بایننس‌کوین',xrp:'ریپل',shib:'شیبا اینو'};
 const usd=n=>fmt(n,n<0.001?8:n<1?4:2);
 const lines=['🪙 *نرخ لحظه‌یی رمزارزها — صراف*',date,''];
 for(const [sym,price] of Object.entries(prices||{})){
  if(!(Number(price)>0))continue;
  lines.push(DIVIDER,'*'+(names[sym]||sym.toUpperCase())+' ('+sym.toUpperCase()+')*');
  let line=usd(price)+'$';
  if(Number(afnPerUsd)>0)line+='   |   '+usd(price*afnPerUsd)+' افغانی';
  lines.push(line);
 }
 lines.push(DIVIDER);
 if(stale)lines.push('ℹ️ منابع لحظه‌یی موقتاً در دسترس نیستند؛ آخرین نرخ ثبت‌شده نمایش داده شد.');
 return lines.join('\n');
}
export const converterIntro='🔄 *مبدل ارز جهانی*\n\nابتدا ارز مبدأ (چیزی که در اختیار دارید) را انتخاب کنید:';
export function conversionText(from,to,amount,result,unit){
 return '🔄 *نتیجهٔ تبدیل*\n\n'+fmt(amount)+' '+currencyLabel(from)+
  ' = *'+fmt(result,4)+' '+currencyLabel(to)+'*\n\nنرخ واحد: ۱ '+
  currencyLabel(from)+' = '+fmt(unit,6)+' '+currencyLabel(to);
}
