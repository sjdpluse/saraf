// Original /start and /stop registration against existing Supabase users.
// Explicit, signed Mini App confirmation; no guessed bot chat IDs.
import {getInitData} from './telegram';
const URL='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-notifications';
const ENABLED=import.meta.env.VITE_SARAF_ORIGINAL_NOTIFICATIONS_ENABLED==='true';
export async function originalNotificationPreferences(action){
 if(!ENABLED)throw new Error('تنظیم دریافت پیام همگانی هنوز به سرور جدید منتقل نشده است.');
 if(!['read','activate','deactivate'].includes(action))throw new Error('درخواست نامعتبر است.');
 const raw=getInitData();
 if(!raw)throw new Error('مینی‌اپ را از ربات اصلی باز کنید.');
 const controller=new AbortController(),t=setTimeout(()=>controller.abort(),15000);
 try{
  const res=await fetch(URL,{method:'POST',mode:'cors',
    credentials:'omit',cache:'no-store',
    headers:{'Content-Type':'application/json','X-Telegram-Init-Data':raw},
    body:JSON.stringify({action}),signal:controller.signal});
  const data=await res.json();
  if(!res.ok||data?.error)throw new Error('ذخیره تنظیمات دریافت پیام ناموفق بود.');
  return data;
 }finally{clearTimeout(t);}
}
