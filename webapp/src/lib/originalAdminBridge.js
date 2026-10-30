// Existing Saraf admin commands, moved from Railway to a signed Mini App.
// The original backend verifies auth_date + HMAC and server-only admin IDs;
// frontend identity and role indicators have ZERO authorization weight.
import {getInitData} from './telegram';
const URL='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-admin';
const ENABLED=import.meta.env.VITE_SARAF_ORIGINAL_ADMIN_UI_ENABLED==='true';
export async function originalAdminCommand(action,input={}){
 if(!ENABLED)throw new Error('دستورات مدیریت هنوز در سرور جدید فعال نشده‌اند.');
 const initData=getInitData();
 if(!initData)throw new Error('پنل مدیریت را از ربات اصلی صراف باز کنید.');
 const allowed=['stats','spreads','orders.pending','spread.set',
 'order.confirm','order.reject','order.complete','orders.confirmed',
 'broadcast.create','broadcast.status',
 'kyc.pending','kyc.review',
 'remittances.pending','remittances.transition'];
 if(!allowed.includes(action))throw new Error('دستور مدیریت پشتیبانی نمی‌شود.');
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),15000);
 try{
  const response=await fetch(URL,{method:'POST',credentials:'omit',
   headers:{'Content-Type':'application/json','X-Telegram-Init-Data':initData},
   mode:'cors',cache:'no-store',signal:controller.signal,
   body:JSON.stringify({action,input})});
  let json;
  try{json=await response.json();}catch{throw new Error('پاسخ سرور معتبر نیست.');}
  if(!response.ok||json?.error){
    if(response.status===403)throw new Error('این بخش فقط برای مدیران تأییدشدهٔ صراف است.');
    if(response.status===503)throw new Error('خدمات مدیریتی هنوز فعال نشده‌اند.');
    if(json?.error==='INVALID_ORDER_TRANSITION')
      throw new Error('وضعیت این سفارش برای تأیید مناسب نیست.');
    if(json?.error==='ORDER_NOT_FOUND')throw new Error('سفارش پیدا نشد.');
    throw new Error('عملیات انجام نشد. لطفاً دوباره بررسی کنید.');
  }
  return json;
 }finally{clearTimeout(timer);}
}
