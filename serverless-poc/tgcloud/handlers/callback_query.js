// Migration of the ORIGINAL Saraf inline callbacks, not a new finance feature.
// Original Python handlers: currency, converter, gold, silver, compare, start.
import { api } from 'sdk';
import { VALID_CODES, money } from '../lib/currencies.js';
import { getReferenceRates, convertUsingAfnRates } from '../lib/reference_rates.js';
import { getMetalPrice, metalBreakdown } from '../lib/metals.js';
import { getOriginalCompareReport } from '../lib/legacy_compare.js';
import { originalLiveQuotes } from '../lib/legacy_live_rates.js';
import {originalCurrencyText,allCurrencyText,goldPriceText,conversionText,afghanDateTime,converterIntro,currencyLabel} from '../lib/legacy_display.js';
import {ABOUT} from '../lib/legacy_about.js';
import { codeLabel,hasValidCurrency,validKarat,currencyList,currencyQuote,
  goldCalcMode,goldCalcKarat,comparePeriod,converterFrom,converterTo,
  converterAmounts,aboutKeyboard,originalStablecoinMenu } from '../lib/legacy_menus.js';
const fmt=(n,d=2)=>Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const edit=(chat,id,text,markup,markdown=false)=>api.editMessageText({
  chat_id:chat,message_id:id,text,...(markup?{reply_markup:markup}:{}),
  ...(markdown?{parse_mode:'Markdown'}:{})});
const prompt=(chat,tag,text)=>api.sendMessage({
  chat_id:chat,text:text+'\n['+tag+']',
  reply_markup:{force_reply:true,selective:true},
});
async function convert(chat,id,from,to,amount){
  const {rates}=await getReferenceRates();
  const {result,unit}=convertUsingAfnRates(rates,from,to,amount);
  return edit(chat,id,conversionText(from,to,amount,result,unit),undefined,true);
}
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
      if(ABOUT[a])return edit(chat,id,ABOUT[a],aboutKeyboard(a),true);
    }
    if(type==='cur'||type==='ref'){
      if(a==='list')return edit(chat,id,'کدام ارز مدنظر شماست؟ یا «نمایش همهٔ نرخ‌ها» را بزنید.',currencyList());
      const quotes=await originalLiveQuotes(a==='all'?VALID_CODES:[a]);
      if(a==='all')return edit(chat,id,allCurrencyText(quotes),undefined,true);
      if(!hasValidCurrency(a))return;
      if(!quotes[a])return edit(chat,id,'⚠️ در حال حاضر نرخ این ارز در دسترس نیست.');
      return edit(chat,id,originalCurrencyText(a,quotes[a]),currencyQuote(a),true);
    }
    if(type==='curcalc'&&hasValidCurrency(a))
      return prompt(chat,'currency:'+a,currencyLabel(a).replace(/^[^ ]+ /,'')+
        ' شما به افغانی چند می‌شود؟\n'+afghanDateTime()+
        '\n\nلطفاً مقدار را فقط بصورت عدد بنویسید. مثلاً (100)');
    if(type==='gold'||type==='goldref'){
      if(a==='calc')return edit(chat,id,'می‌خواهید طلا بخرید یا بفروشید؟',goldCalcMode());
      if(a==='all'||validKarat(a)){
        const [{rates},m]=await Promise.all([getReferenceRates(),getMetalPrice('XAU')]);
        const rows=metalBreakdown('XAU',m.price,rates.usd);
        return edit(chat,id,goldPriceText(rows,m.price,a),undefined,true);
      }
    }
    if(type==='goldcalc_mode'&&['buy','sell'].includes(a))
      return edit(chat,id,'عیار طلای مورد نظر برای '+(a==='buy'?'خرید':'فروش')+
        ' را انتخاب کنید:',goldCalcKarat(a));
    if(type==='goldcalc_karat'&&['buy','sell'].includes(a)&&validKarat(parts[2]))
      return prompt(chat,'gold:'+a+':'+parts[2],'چند گرم طلای عیار '+parts[2]+
        ' می‌خواهید '+(a==='buy'?'خرید':'فروش')+
        ' کنید؟ لطفاً فقط عدد را بنویسید (مثال: 10 یا 4.6)');
    if(type==='silvercalc_mode'&&['buy','sell'].includes(a))
      return prompt(chat,'silver:'+a,'چند گرم نقره می‌خواهید '+
        (a==='buy'?'خرید':'فروش')+
        ' کنید؟ لطفاً فقط عدد را بنویسید (مثال: 10 یا 4.6)');
    if(type==='convfrom'){
      if(a==='back')return edit(chat,id,converterIntro,converterFrom(),true);
      if(hasValidCurrency(a))return edit(chat,id,'ارز مبدأ: '+codeLabel(a)+
        '\n\nحالا ارز مقصد را انتخاب کنید:',converterTo(a));
    }
    if(type==='convto'&&hasValidCurrency(a)&&hasValidCurrency(parts[2])&&a!==parts[2])
      return edit(chat,id,codeLabel(a)+' ➜ '+codeLabel(parts[2])+
        '\n\nچه مقداری را می‌خواهید تبدیل کنید؟',converterAmounts(a,parts[2]));
    if(type==='convamt'&&hasValidCurrency(a)&&hasValidCurrency(parts[2])){
      if(parts[3]==='custom')return prompt(chat,'converter:'+a+':'+parts[2],
        'لطفاً مقدار مورد نظر را فقط به‌صورت عدد بنویسید (مثال: 250)');
      const num=Number(parts[3]);
      if(Number.isFinite(num)&&num>0&&num<=1e9)return convert(chat,id,a,parts[2],num);
    }
    if(type==='cmp_target'&&(a==='gold'||hasValidCurrency(a)))
      return edit(chat,id,(a==='gold'?'🥇 طلا (عیار ۲۴)':codeLabel(a))+
        '\n\nبا چه زمانی مقایسه شود؟',comparePeriod(a));
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
      if(type==='usdt_rate'){
        // Original completed-order rating remains signed in the React
        // order history; never trust an old callback to write a rating.
        return api.sendMessage({chat_id:chat,
          text:'⭐ برای امتیازدهی به سفارش‌های تکمیل‌شده، تاریخچهٔ رسمی سفارش‌های خود را باز کنید.',
          reply_markup:{inline_keyboard:[[
            {text:'⭐ سفارش‌های من و امتیازدهی',
             web_app:{url:'https://app8533795882.tgcloud.ai/?action=orders'}},
          ]]},
        });
      }
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
