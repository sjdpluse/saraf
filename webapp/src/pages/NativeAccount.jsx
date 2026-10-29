import { useEffect,useState } from 'react';
import { CaretRight,ShieldCheck,ArrowClockwise } from '@phosphor-icons/react';
import { nativeCall } from '../lib/nativeApi';

// Native KYC uses the VERIFIED private Telegram bot chat for images, not the
// unsupported multipart upload routes. No image bytes are sent to an API.
export default function NativeAccount({navigate}) {
  const [profile,setProfile]=useState(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');
  const [form,setForm]=useState({first_name:'',last_name:'',phone:''});

  async function reload() {
    setLoading(true);setError('');
    try {
      const result=await nativeCall('getNativeProfile');
      setProfile(result);
      setForm(old=>({
        first_name:old.first_name||result.profile?.first_name||'',
        last_name:old.last_name||result.profile?.last_name||'',
        phone:old.phone||result.profile?.phone||'',
      }));
    } catch (e) {setError(e.message);}
    finally {setLoading(false);}
  }
  useEffect(()=>{reload();},[]);
  async function submitBasic(e) {
    e.preventDefault();
    setBusy(true);setError('');setMessage('');
    try {
      await nativeCall('saveBasicProfile',form);
      setMessage('✅ پروفایل ثبت شد.');
      await reload();
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function submitIdentity() {
    setBusy(true);setError('');setMessage('');
    try {
      await nativeCall('submitNativeIdentity');
      setMessage('✅ مدارک برای بررسی مدیر ثبت شد. تأیید هویت تا بررسی دستی در انتظار است.');
      await reload();
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  return <main className="app-shell">
    <div className="header"><button className="back-btn" onClick={()=>navigate('home')} aria-label="بازگشت"><CaretRight size={20}/></button>
      <h1>پروفایل و احراز هویت</h1><span className="header-spacer"/></div>
    <section className="card" style={{padding:18,marginBottom:16}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <h2 style={{fontSize:17}}>👤 اطلاعات پایه</h2>
        <button className="btn btn-outline" onClick={reload} type="button" aria-label="بروزرسانی"><ArrowClockwise size={17}/></button>
      </div>
      {loading && <p>در حال دریافت معلومات...</p>}
      <form onSubmit={submitBasic} style={{display:'grid',gap:12}}>
        <label>نام<input className="input" maxLength={80} minLength={2} required value={form.first_name} onChange={e=>setForm(f=>({...f,first_name:e.target.value}))}/></label>
        <label>تخلص<input className="input" maxLength={80} minLength={2} required value={form.last_name} onChange={e=>setForm(f=>({...f,last_name:e.target.value}))}/></label>
        <label>شماره تماس<input className="input" maxLength={24} minLength={7} required value={form.phone} onChange={e=>setForm(f=>({...f,phone:e.target.value}))}/></label>
        <button className="btn btn-primary" type="submit" disabled={busy}>{busy?'در حال ثبت...':'ثبت معلومات پایه'}</button>
      </form>
    </section>
    <section className="card" style={{padding:18}}>
      <h2 style={{fontSize:17}}>🛡 تأیید هویت</h2>
      {profile?.identity_uploads_enabled===false && <p role="alert" className="notice warn">در حال حاضر دریافت سند هویتی غیرفعال است. لطفاً عکس تذکره یا سلفی را ارسال نکنید.</p>}
      <p>وضعیت: <strong>{profile?.kyc_status==='verified'?'✅ تأییدشده':profile?.kyc_status==='rejected'?'❌ ردشده':'⏳ در انتظار بررسی'}</strong></p>
      <p>برای ثبت مدارک، به چت خصوصی <strong>همین ربات صراف</strong> بروید و دو عکس جداگانه بفرستید:</p>
      <p><strong>۱.</strong> تصویر مدرک شناسایی با متن توضیح (Caption) دقیق <code>KYC_ID</code></p>
      <p><strong>۲.</strong> تصویر سلفی با متن توضیح (Caption) دقیق <code>KYC_SELFIE</code></p>
      <p>سپس به این صفحه بازگردید و دکمهٔ بروزرسانی را بزنید.</p>
      <button className="btn btn-outline" type="button" onClick={reload}>↻ بررسی دریافت تصاویر</button>
      <p>مدرک: {profile?.uploaded?.kyc_id?'✅':'❌'} | سلفی: {profile?.uploaded?.selfie?'✅':'❌'}</p>
      <button type="button" className="btn btn-primary"
        disabled={busy || !profile?.identity_uploads_enabled || !profile?.has_basic_profile || !profile?.uploaded?.kyc_id || !profile?.uploaded?.selfie}
        onClick={submitIdentity}>ارسال مدارک برای تأیید مدیر</button>
      <p className="notice">در این مرحله عکس‌ها فقط به چت خصوصی ربات ارسال می‌شوند. برای حفظ حریم خصوصی، مدارک را در گروه‌ها یا کانال‌ها نفرستید.</p>
    </section>
    {error && <p role="alert" className="notice warn">{error}</p>}
    {message && <p role="status" className="notice">{message}</p>}
  </main>;
}
