// Migration of the ORIGINAL Saraf inline callbacks, not a new finance feature.
// Original Python handlers: currency, converter, gold, silver, compare, start.
import { api } from 'sdk';
import { VALID_CODES, money } from '../lib/currencies.js';
import { getReferenceRates, convertUsingAfnRates } from '../lib/reference_rates.js';
import { getMetalPrice, metalBreakdown } from '../lib/metals.js';
import { getOriginalCompareReport } from '../lib/legacy_compare.js';
import { originalLiveQuotes,originalCurrencyText } from '../lib/legacy_live_rates.js';
import { codeLabel,hasValidCurrency,validKarat,currencyList,currencyQuote,
  goldCalcMode,goldCalcKarat,comparePeriod,converterFrom,converterTo,
  converterAmounts,aboutKeyboard,originalStablecoinMenu } from '../lib/legacy_menus.js';
const fmt=(n,d=2)=>Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const edit=(chat,id,text,markup)=>api.editMessageText({
  chat_id:chat,message_id:id,text,...(markup?{reply_markup:markup}:{})});
const prompt=(chat,tag,text)=>api.sendMessage({
  chat_id:chat,text:text+'\n['+tag+']',
  reply_markup:{force_reply:true,selective:true},
});
async function convert(chat,id,from,to,amount){
  const {rates}=await getReferenceRates();
  const {result,unit}=convertUsingAfnRates(rates,from,to,amount);
  return edit(chat,id,'🔄 نتیجهٔ تبدیل\n\n'+fmt(amount)+' '+codeLabel(from)+
    ' = '+fmt(result,4)+' '+codeLabel(to)+
    '\nنرخ واحد: ۱ '+codeLabel(from)+' = '+fmt(unit,6)+' '+codeLabel(to));
}
const ABOUT={
  home:'🏦 صراف\nیک تجربهٔ مالی هوشمند، ساده و ساخته‌شده برای افغانستان.\n\nنرخ را ببین. محاسبه کن. با آگاهی تصمیم بگیر.',
  markets:'📊 بازارها و نرخ‌ها\nارزهای خارجی، طلا، نقره و رمزارزها',
  tools:'🧮 ابزارهای مالی صراف\nمبدل ارز، مقایسه با گذشته، ماشین‌حساب طلا و نقره',
  usdt:'🪙 خدمات USDT / USDC\nنسخه اصلی Mini App در حال انتقال است.',
  security:'🛡 امنیت و تایید هویت\nبررسی اسناد و سفارش‌ها طبق روال اصلی',
  developer:'👨‍💻 سجاد محمدی — بنیان‌گذار و سازندهٔ صراف\nارتباط: @SJDPLUS',
  disclaimer:'⚠️ شرایط استفاده\nنرخ‌های عمومی توصیهٔ سرمایه‌گذاری نیستند.\n© 2026 صراف',
};
export default async function(query){
  const chat=query?.message?.chat?.id,id=query?.message?.message_id;
  if(!Number.isSafeInteger(chat)||!Number.isSafeInteger(id)||
    query.message.chat.type!=='private'||query.from?.id!==chat)return;
  const data=String(query.data||''),parts=data.split(':'),type=parts[0],a=parts[1];
  try{
    await api.answerCallbackQuery({callback_query_id:query.id});
    if(type==='about'){
      if(a==='open_usdt')return api.sendMessage({chat_id:chat,
        text:'🪙 خرید و فروش USDT / USDC\nدارایی و نوع معامله را انتخاب کنید:',
        reply_markup:originalStablecoinMenu()});
      if(ABOUT[a])return edit(chat,id,ABOUT[a],aboutKeyboard(a));
    }
    if(type==='cur'||type==='ref'){
      if(a==='list')return edit(chat,id,'کدام ارز مدنظر شماست؟',currencyList());
      const quotes=await originalLiveQuotes(a==='all'?VALID_CODES:[a]);
      if(a==='all')return edit(chat,id,'💵 نرخ خرید و فروش ارزها\n\n'+
        VALID_CODES.filter(c=>quotes[c]).map(c=>
          codeLabel(c)+'\n'+originalCurrencyText(c,quotes[c])).join('\n\n'));
      if(!hasValidCurrency(a)||!quotes[a])return;
      return edit(chat,id,codeLabel(a)+'\n'+originalCurrencyText(a,quotes[a]),
        currencyQuote(a));
    }
    if(type==='curcalc'&&hasValidCurrency(a))
      return prompt(chat,'currency:'+a,'مقدار ارز را وارد کنید؛ مثال 100');
    if(type==='gold'||type==='goldref'){
      if(a==='calc')return edit(chat,id,'می‌خواهید طلا بخرید یا بفروشید؟',goldCalcMode());
      if(a==='all'||validKarat(a)){
        const [{rates},m]=await Promise.all([getReferenceRates(),getMetalPrice('XAU')]);
        const rows=metalBreakdown('XAU',m.price,rates.usd)
          .filter(r=>a==='all'||r.karat===Number(a));
        return edit(chat,id,'🥇 نرخ لحظه‌یی طلا\nقیمت جهانی هر اونس: $'+
          fmt(m.price,2)+'\n'+rows.map(r=>'عیار '+r.karat+
          ': هر گرم '+fmt(r.afnGram,1)+'، هر مثقال '+fmt(r.afnMethqal,1)+' افغانی').join('\n'));
      }
    }
    if(type==='goldcalc_mode'&&['buy','sell'].includes(a))
      return edit(chat,id,'عیار طلا را انتخاب کنید:',goldCalcKarat(a));
    if(type==='goldcalc_karat'&&['buy','sell'].includes(a)&&validKarat(parts[2]))
      return prompt(chat,'gold:'+a+':'+parts[2],'چند گرم طلا؟ مثال 4.6');
    if(type==='silvercalc_mode'&&['buy','sell'].includes(a))
      return prompt(chat,'silver:'+a,'چند گرم نقره؟ مثال 4.6');
    if(type==='convfrom'){
      if(a==='back')return edit(chat,id,'🔄 ارز مبدأ را انتخاب کنید:',converterFrom());
      if(hasValidCurrency(a))return edit(chat,id,'ارز مبدأ: '+codeLabel(a)+
        '\nارز مقصد را انتخاب کنید:',converterTo(a));
    }
    if(type==='convto'&&hasValidCurrency(a)&&hasValidCurrency(parts[2])&&a!==parts[2])
      return edit(chat,id,codeLabel(a)+' ➜ '+codeLabel(parts[2])+
        '\nچه مقداری را تبدیل می‌کنید؟',converterAmounts(a,parts[2]));
    if(type==='convamt'&&hasValidCurrency(a)&&hasValidCurrency(parts[2])){
      if(parts[3]==='custom')return prompt(chat,'converter:'+a+':'+parts[2],
        'مقدار موردنظر را عددی بنویسید؛ مثال 250');
      const num=Number(parts[3]);
      if(Number.isFinite(num)&&num>0&&num<=1e9)return convert(chat,id,a,parts[2],num);
    }
    if(type==='cmp_target'&&(a==='gold'||hasValidCurrency(a)))
      return edit(chat,id,(a==='gold'?'🥇 طلا (عیار ۲۴)':codeLabel(a))+
        '\nبا چه زمانی مقایسه شود؟',comparePeriod(a));
    if(type==='cmp_period'){
      const days=Number(parts[2]);
      if(![1,7,30,90].includes(days))return;
      if(a!=='gold'&&!hasValidCurrency(a))return;
      const report=await getOriginalCompareReport(a,days);
      return edit(chat,id,report);
    }
    // Old Python messages may contain usdt_* callback buttons after cutover.
    // The old in-chat state cannot be trusted in a stateless JS invocation.
    // Recover the ORIGINAL action in the signed Mini App; never submit money
    // from a stale callback or invent a completed payment.
    if(type.startsWith('usdt_')){
      const known=new Set(['usdt_action','usdt_continue','usdt_pay',
        'usdt_paid','usdt_net','usdt_buy_exch','usdt_exch','usdt_rate']);
      if(!known.has(type))return;
      const asset=type==='usdt_action'&&['USDT','USDC'].includes(a)?a:null;
      const side=type==='usdt_action'?parts[2]:
        ['usdt_continue','usdt_pay','usdt_paid','usdt_net'].includes(type)?a:null;
      return api.sendMessage({chat_id:chat,
        text:'🪙 برای ادامهٔ درخواست '+(asset||'USDT / USDC')+
          ' از اپلیکیشن اصلی صراف استفاده کنید. '+
          'وضعیت یا پرداخت از پیام قدیمی تأیید نمی‌شود.',
        reply_markup:originalStablecoinMenu(),
      });
    }
  }catch(error){
    console.warn('Saraf callback migration',String(error));
    await api.sendMessage({chat_id:chat,text:'⚠️ دریافت معلومات ناموفق بود؛ دوباره امتحان کنید.'});
  }
}
