// Exact original POST /api/usdt/kyc shape, relayed to Supabase Edge
// with signed ORIGINAL @sarafiaf_bot initData and private file storage.
// Off unless the old admin KYC review flow has been verified end-to-end.
import { getInitData } from './telegram';
const URL='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-legacy-kyc';
export async function uploadOriginalIdentity(form) {
 if(import.meta.env.VITE_SARAF_ORIGINAL_KYC_ENABLED!=='true')
   throw Object.assign(new Error('ثبت مدارک هنوز به سرور جدید منتقل نشده است.'),{code:'NOT_MIGRATED',status:503});
 if(!(form instanceof FormData))
   throw Object.assign(new Error('فرمت اسناد معتبر نیست.'),{code:'INVALID_INPUT',status:400});
 const identity=getInitData();
 if(!identity)throw Object.assign(new Error('Mini App را از ربات اصلی باز کنید.'),{code:'INVALID_TELEGRAM_AUTH',status:401});
 const files=['id_document','selfie'].map(k=>form.get(k));
 if(files.some(f=>!(f instanceof File)||f.size>8*1024*1024||f.size<12))
   throw Object.assign(new Error('دو تصویر معتبر زیر ۸ مگابایت لازم است.'),{code:'INVALID_IMAGE',status:400});
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),45000);
 try{
  const res=await fetch(URL,{method:'POST',body:form,mode:'cors',
    cache:'no-store',credentials:'omit',
    headers:{'X-Telegram-Init-Data':identity},signal:ctrl.signal,
  });
  let result;
  try{result=await res.json()}catch{throw new Error('پاسخ آپلود معتبر نیست.');}
  if(!res.ok||result?.error){
   throw Object.assign(new Error('ثبت اسناد موفق نشد؛ دوباره تلاش کنید.'),
    {code:result?.error||'UPLOAD_FAILED',status:res.status});
  }
  return result.data;
 }finally{clearTimeout(timer);}
}
