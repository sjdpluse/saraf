// Railway-equivalent original Saraf order notices, without a new ledger.
// Monetary values and identity MUST come from the persisted usdt_orders and
// user_profiles records, not from browser/Telegram messages or live repricing.
const safe=(x,max=900)=>String(x??'-').slice(0,max)
 .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
 .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const fmt=(value,digits=2)=>Number(value||0).toLocaleString('en-US',{
 minimumFractionDigits:digits,maximumFractionDigits:digits,
});
const val=(value)=>Number(value||0);
const statusLabels={pending:'🟡 در انتظار',verified:'🔵 تأییدشده',
 trusted:'🟢 معتمد',restricted:'🔴 محدودشده'};
const riskLabels={low:'🟢 ریسک پایین',medium:'🟡 ریسک متوسط',
 high:'🔴 ریسک بالا'};

export function buildOriginalOrderReports(order,profile={},support='@SJDPLUS'){
 if(!order||!Number.isSafeInteger(Number(order.id))||Number(order.id)<=0)
   throw Error('ORIGINAL_ORDER_REPORT_INVALID');
 const asset=order.asset==='USDC'?'USDC':'USDT';
 const title=order.order_type==='buy'?'خرید':'فروش';
 const code=asset+'-'+String(order.id).padStart(5,'0');
 const amount=val(order.usdt_amount),rate=val(order.usd_rate);
 const afn=val(order.total_afn),totalUsd=val(order.total_usd);
 if(!amount||!rate||!afn||!totalUsd)throw Error('ORIGINAL_ORDER_REPORT_AMOUNT_INVALID');
 const wallet=safe(order.wallet_address,130);
 const exchange=safe(order.exchange_name,200),network=safe(order.network,60);
 const username=safe(order.username||'-',80);
 const chatId=safe(order.chat_id,20);
 const phone=safe(profile.phone||order.phone||'-',50);
 const name=safe([profile.first_name,profile.last_name].filter(Boolean).join(' ')||
   order.full_name||'-',160);
 const risk=safe(order.risk_level||'-',40);
 const method=safe(order.payment_method||order.receive_method||'-',50);
 const codePlace=order.in_person_code?'\nکد مراجعه حضوری: <code>'+
   safe(order.in_person_code,4)+'</code>':'';
 const status='⏳ در انتظار بررسی تیم صراف — این پیام تأیید پرداخت نیست.';
 const header='✅ <b>سفارش '+title+' '+asset+' شما ثبت شد</b>\n\n';
 const customer=order.order_type==='buy'
 ?header+'کد سفارش: <code>'+code+'</code>\n'+
  'دارایی: <b>'+asset+'</b> ('+(asset==='USDT'?'تتر':'یو‌اس‌دی کوین')+')\n'+
  'مقدار: <b>'+fmt(amount,2)+' '+asset+'</b>\n'+
  'نرخ: '+fmt(rate,2)+' افغانی\n'+
  'مبلغ قابل پرداخت: <b>'+fmt(afn,1)+' افغانی</b>\n'+
  'شبکه: '+network+'\nآدرس دریافت: <code>'+wallet+'</code>\n'+
  'صرافی: '+exchange+'\n'+method+codePlace+'\n\n'+
  asset+' شما پس از تأیید پرداخت و اجرای سفارش به آدرس فوق واریز خواهد شد.\n'+
  status+'\n\n🆘 پشتیبانی: '+safe(support,70)
 :header+'کد سفارش: <code>'+code+'</code>\n'+
  'دارایی: <b>'+asset+'</b>\nمقدار: <b>'+fmt(amount,2)+' '+asset+'</b>\n'+
  'نرخ: '+fmt(rate,2)+' افغانی\n'+
  'مبلغ قابل دریافت: <b>'+fmt(afn,0)+' افغانی</b>\n'+
  'صرافی: '+exchange+'\nشبکه: '+network+'\n'+
  'روش دریافت: '+method+codePlace+'\n'+
  (order.receive_method==='in_person'
   ?'برای دریافت حضوری، با پشتیبانی آدرس و زمان مراجعه را هماهنگ کنید.\n'
   :'مبلغ پس از تأیید انتقال به حساب ثبت‌شدهٔ شما واریز خواهد شد.\n')+
  status+'\n\n🆘 پشتیبانی: '+safe(support,70);
 const riskBanner='\n'+(riskLabels[order.risk_level]||'ریسک: '+risk)+
  (order.risk_reasons?'\nدلایل ریسک: '+safe(order.risk_reasons,250):'');
 const trust='\n👤 '+(statusLabels[profile.kyc_status]||statusLabels.pending)+
  ' | ✅ '+fmt(profile.successful_orders||0,0)+' معامله موفق'+
  ' | ⭐ '+fmt(profile.trust_score||0,0)+'/100';
 const common='\nکد: <code>'+code+'</code>\n'+
  'کاربر: @'+username+' ('+chatId+')\n'+
  'نام: '+name+'\n📞 تماس: '+phone+'\n'+
  'دارایی: '+asset+'\nمقدار: '+fmt(amount,2)+' '+asset+'\n'+
  'نرخ هر دالر: '+fmt(rate,2)+' افغانی\n'+
  'صرافی: '+exchange+'\nشبکه: '+network+
  '\nروش پرداخت / دریافت: '+method+codePlace;
 const source='\nمنبع سفارش: '+safe(order.source||'miniapp',40)+
  '\n⏳ در انتظار بررسی دستی مدیر؛ پرداخت خودکار انجام نشده است.';
 const admin=order.order_type==='buy'?
  '🆕 <b>سفارش خرید '+asset+'</b>'+riskBanner+trust+common+
  '\nآدرس ولت مشتری: <code>'+wallet+'</code>\n'+
  '💳 مبلغ پرداختی مشتری: <b>'+fmt(afn,1)+' افغانی</b> | <b>$'+fmt(totalUsd)+'</b>\n'+
  '💵 کارمزد صراف از مشتری: <b>$'+fmt(Math.max(0,totalUsd-amount))+
  '</b> | <b>'+fmt(Math.max(0,afn-amount*rate),1)+' افغانی</b>\n'+
  '📈 سود خالص صراف: <b>$'+fmt(order.saraf_profit_usd)+
  '</b> | <b>'+fmt(order.saraf_profit_afn,1)+' افغانی</b>\n\n'+
  '🏦 <b>تسویه با تأمین‌کننده</b>\n'+
  'اصل دارایی: $'+fmt(amount)+' | '+fmt(amount*rate,1)+' افغانی\n'+
  'سود تأمین‌کننده (۵۰٪ حاشیه): $'+fmt(order.supplier_profit_usd)+
  ' | '+fmt(order.supplier_profit_afn,1)+' افغانی\n'+
  '✅ مبلغ کامل تأمین‌کننده: $'+fmt(order.supplier_payout_usd)+
  ' | '+fmt(order.supplier_payout_afn,1)+' افغانی'+
  (order.receipt_file_id?'\n🧾 رسید پرداخت مشتری: دریافت‌شده (فایل جداگانه)':'')+
  source
  :'🆕 <b>سفارش فروش '+asset+'</b>'+riskBanner+trust+common+
  '\n💵 مبلغ قابل پرداخت: <b>'+fmt(afn,0)+' افغانی</b>\n'+
  'اثبات تراکنش: '+(order.tx_proof?
   (String(order.tx_proof).startsWith('https://')?
     'رسید بارگذاری‌شده (فایل جداگانه)':safe(order.tx_proof,450)):'-')+
  '\nاطلاعات پرداخت مشتری: '+safe(order.bank_info,450)+source;
 return {customer,admin,code};
}
