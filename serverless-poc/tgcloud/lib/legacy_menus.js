// 1:1 migration of the ORIGINAL bot's non-transactional inline keyboard labels
// and callback_data, sourced from main:keyboards.py. No new business workflow.
import { CURRENCIES, VALID_CODES } from './currencies.js';

const button=(text,callback_data)=>({text,callback_data});
const grouped=(items,size=2)=> {
  const groups=[];
  for(let i=0;i<items.length;i+=size)groups.push(items.slice(i,i+size));
  return groups;
};
export const codeLabel=code=>{
  const c=CURRENCIES[code];
  return c ? c[0]+' '+c[1] : String(code||'').toUpperCase();
};
export const currencyList=()=>({
  inline_keyboard:[
    ...grouped(VALID_CODES.map(c=>button(codeLabel(c),'cur:'+c))),
    [button('🔄 نمایش همهٔ نرخ‌ها','cur:all')],
  ],
});
export const currencyQuote=code=>({
  inline_keyboard:[[button('🧮 صراف','curcalc:'+code)]],
});
export const goldList=()=>({
  inline_keyboard:[
    ...[24,22,21,18].map(k=>[button('عیار '+k,'gold:'+k)]),
    [button('🔄 نمایش همهٔ عیارها','gold:all')],
    [button('🧮 ماشین‌حساب خرید/فروش طلا','gold:calc')],
  ],
});
export const goldCalcMode=()=>({
  inline_keyboard:[[button('🟢 خرید طلا','goldcalc_mode:buy'),
                    button('🔴 فروش طلا','goldcalc_mode:sell')]],
});
export const goldCalcKarat=mode=>({
  inline_keyboard:[24,22,21,18].map(k=>[button('عیار '+k,'goldcalc_karat:'+mode+':'+k)]),
});
export const silverCalcMode=()=>({
  inline_keyboard:[[button('🟢 خرید نقره','silvercalc_mode:buy'),
                    button('🔴 فروش نقره','silvercalc_mode:sell')]],
});
export const compareTarget=()=>({
  inline_keyboard:[
    ...grouped(VALID_CODES.map(c=>button(codeLabel(c),'cmp_target:'+c))),
    [button('🥇 طلا (عیار ۲۴)','cmp_target:gold')],
  ],
});
export const comparePeriod=target=>({
  inline_keyboard:[
    [button('⏱ ۲۴ ساعت پیش','cmp_period:'+target+':1'),
     button('📅 ۷ روز پیش','cmp_period:'+target+':7')],
    [button('🗓 ۳۰ روز پیش','cmp_period:'+target+':30'),
     button('📆 ۹۰ روز پیش','cmp_period:'+target+':90')],
  ],
});
export const converterFrom=()=>({
  inline_keyboard:grouped(VALID_CODES.map(c=>button(codeLabel(c),'convfrom:'+c))),
});
export const converterTo=from=>({
  inline_keyboard:[
    ...grouped(VALID_CODES.filter(c=>c!==from).map(c=>button(codeLabel(c),'convto:'+from+':'+c))),
    [button('🔙 تغییر ارز مبدأ','convfrom:back')],
  ],
});
export const converterAmounts=(from,to)=>({
  // Original labels and preset values; the destination pair is encoded to
  // preserve callback behavior across stateless Telegram JS invocations.
  inline_keyboard:[
    ...grouped([1,10,50,100,500,1000].map(a=>button(a.toLocaleString('en-US'),
      'convamt:'+from+':'+to+':'+a)),3),
    [button('✏️ مقدار دلخواه','convamt:'+from+':'+to+':custom')],
  ],
});
export const originalBotMenu=()=>({
  keyboard:[
    [{text:'خرید و فروش | USDT/USDC'}],
    [{text:'Saraf - JustMarkets'}],
    [{text:'💵 نرخ ارزها'},{text:'🥇 نرخ طلا'}],
    [{text:'🥈 نرخ نقره'},{text:'🔄 مبدل ارز جهانی'}],
    [{text:'🪙 نرخ رمزارزها'},{text:'📊 مقایسه با گذشته'}],
    [{text:'ℹ️ درباره ربات'}],
  ],
  resize_keyboard:true,
});
export const aboutKeyboard=(page='home')=>{
 if(page==='home')return {
  inline_keyboard:[
    [button('📊 بازارها و نرخ‌ها','about:markets'),
     button('🧮 ابزارهای مالی','about:tools')],
    [button('🪙 خدمات USDT / USDC','about:usdt'),
     button('🛡 امنیت و تایید هویت','about:security')],
    [button('👨‍💻 توسعه و برند','about:developer'),
     button('⚠️ شرایط استفاده','about:disclaimer')],
  ],
 };
 return {
  inline_keyboard:[
    ...(page==='usdt'?[[button('🚀 ورود به خدمات USDT / USDC','about:open_usdt')]]:[]),
    [button('🔙 بازگشت به درباره صراف','about:home')],
  ],
 };
};
export const hasValidCurrency=c=>VALID_CODES.includes(c);
export const validKarat=k=>[24,22,21,18].includes(Number(k));
