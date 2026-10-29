import {useEffect,useState} from 'react';
import {showConfirm} from '../lib/telegram';
import {originalNotificationPreferences} from '../lib/originalNotificationsBridge';

export default function OriginalNotifications({navigate}){
 const [busy,setBusy]=useState(false);
 const [state,setState]=useState(null);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 async function act(name){
  setBusy(true);setError('');setNotice('');
  try{
   if(name==='deactivate'&&!await showConfirm(
    'آیا می‌خواهید دریافت پیام‌های همگانی ربات را غیرفعال کنید؟'))return;
   const data=await originalNotificationPreferences(name);
   setState(data);
   if(name==='deactivate')setNotice(
    'شما از دریافت پیام‌های همگانی ربات خارج شدید. با /start دوباره فعال شوید.');
   if(name==='activate')setNotice('دریافت پیام‌های همگانی برای حساب شما فعال شد.');
  }catch(e){setError(e.message||'دریافت تنظیمات ناموفق بود.');}
  finally{setBusy(false);}
 }
 useEffect(()=>{act('read');},[]);
 return <main className="app-shell" style={{padding:'24px 18px 100px',direction:'rtl'}}>
   <button onClick={()=>navigate('menu')}>بازگشت</button>
   <h1>دریافت پیام‌های ربات صراف</h1>
   <p>این همان تنظیم /start و /stop ربات اصلی است. سفارش‌ها،
    حواله‌ها و معلومات شما حذف نمی‌شوند.</p>
   {busy&&<p role="status">در حال بررسی...</p>}
   {error&&<p role="alert" style={{color:'#b42318'}}>{error}</p>}
   {notice&&<p className="notice">{notice}</p>}
   {state&&<p className="notice">وضعیت فعلی:
    <b>{state.is_active?' فعال':' غیرفعال'}</b></p>}
   <div style={{display:'grid',gap:12,marginTop:22}}>
    <button disabled={busy} onClick={()=>act('activate')}>
     ✅ فعال‌سازی دریافت پیام (/start)
    </button>
    <button disabled={busy} onClick={()=>act('deactivate')}>
     🔕 لغو دریافت پیام (/stop)
    </button>
   </div>
 </main>;
}
