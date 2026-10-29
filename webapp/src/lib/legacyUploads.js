// Migrates the TWO existing Python upload endpoints; preserves FormData
// and original return shapes. No Railway fallback, no public storage bucket.
import { getInitData } from './telegram';
const URL='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-legacy-uploads';
export async function uploadOriginalImage(kind,form){
 if(!['receipt','beneficiary'].includes(kind))
  throw Object.assign(new Error('نوع آپلود نامعتبر است.'),{code:'INVALID_UPLOAD_KIND',status:400});
 if(import.meta.env.VITE_SARAF_ORIGINAL_UPLOADS_ENABLED!=='true')
  throw Object.assign(new Error('آپلود اسناد هنوز کامل منتقل نشده است.'),{code:'NOT_MIGRATED',status:503});
 const initData=getInitData();
 if(!initData)
  throw Object.assign(new Error('لطفاً Mini App را از ربات اصلی باز کنید.'),{code:'INVALID_TELEGRAM_AUTH',status:401});
 if(!(form instanceof FormData))
  throw Object.assign(new Error('فایل معتبر نیست.'),{code:'INVALID_UPLOAD_FILE',status:400});
 const file=form.get('file');
 if(!(file instanceof File)||file.size<12||file.size>(kind==='receipt'?8:10)*1024*1024)
  throw Object.assign(new Error('فایل تصویری معتبر انتخاب کنید.'),{code:'INVALID_UPLOAD_FILE',status:400});
 form.set('kind',kind);
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),45000);
 try{
  const r=await fetch(URL,{method:'POST',body:form,
   headers:{'X-Telegram-Init-Data':initData},credentials:'omit',
   cache:'no-store',mode:'cors',signal:ctrl.signal});
  const data=await r.json();
  if(!r.ok||data.error)
   throw Object.assign(new Error('آپلود فایل انجام نشد.'),{code:data.error||'UPLOAD_FAILED',status:r.status});
  return data.data;
 }finally{clearTimeout(timer);}
}
