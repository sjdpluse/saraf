// Exact original services/risk_engine.py decision tree, no new policy.
// Private server-side thresholds from original config.py and env overrides.
const limit=(raw,defaultValue)=>{
 const n=Number(raw??defaultValue);
 if(!Number.isFinite(n)||n<0)throw Error('ORIGINAL_RISK_CONFIG_INVALID');
 return n;
};
export function originalRiskLevel(profile,amount,env={}){
 if(!profile)return {level:'high',reasons:['پروفایل احراز هویت یافت نشد']};
 const status=String(profile.kyc_status||'pending');
 const successful=Number(profile.successful_orders)||0;
 const cancelled=Number(profile.cancelled_orders)||0;
 const paymentChanges=Number(profile.payment_info_change_count)||0;
 const highAmount=limit(env.USDT_RISK_HIGH_AMOUNT_THRESHOLD,1000);
 const newUser=limit(env.USDT_RISK_NEW_USER_ORDER_THRESHOLD,3);
 const cancelLimit=limit(env.USDT_RISK_CANCEL_COUNT_THRESHOLD,3);
 const changesLimit=limit(env.USDT_RISK_PAYMENT_CHANGE_THRESHOLD,3);
 if(status==='restricted')return {level:'high',reasons:[
  profile.restricted_reason||'کاربر توسط ادمین محدود شده است',
 ]};
 const high=[];
 if(cancelled>=cancelLimit)high.push(`${cancelled} معاملهٔ لغوشده/مشکوک در سابقه`);
 if(paymentChanges>=changesLimit)high.push(`${paymentChanges} بار تغییر اطلاعات پرداخت`);
 if(high.length)return {level:'high',reasons:high};
 const medium=[];
 if(status==='pending')medium.push('هویت هنوز توسط ادمین تایید نشده');
 if(successful<newUser&&Number(amount)>=highAmount)
  medium.push(`کاربر کم‌تجربه (${successful} معاملهٔ موفق) + مبلغ بالا (${amount} USDT)`);
 return medium.length?{level:'medium',reasons:medium}:{level:'low',reasons:[]};
}
