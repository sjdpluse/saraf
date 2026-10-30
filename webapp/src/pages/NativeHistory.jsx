// Financial history is served from the ORIGINAL Supabase records, authenticated
// with Telegram's HMAC-signed initData. This page cannot initiate a transaction.
import { useEffect,useState } from 'react';
import { CaretRight, ArrowClockwise } from '@phosphor-icons/react';
import { api } from '../lib/api';
import { isCanonicalBridgeEnabled } from '../lib/supabaseBridge';
const format=n=>Number(n||0).toLocaleString('en-US',{maximumFractionDigits:2});
const statuses={
  pending:'در انتظار',payment_pending:'در انتظار پرداخت',payment_submitted:'پرداخت ثبت‌شده',
  under_review:'در حال بررسی',confirmed:'تأییدشده',approved:'تأییدشده',
  processing:'در حال اجرا',completed:'تکمیل‌شده',cancelled:'لغوشده',
  rejected:'ردشده',expired:'منقضی',failed:'ناموفق',
  awaiting_transfer:'در انتظار انتقال',transfer_submitted:'انتقال ثبت‌شده',
};
export default function NativeHistory({navigate,initialTab='orders'}) {
  const [tab,setTab]=useState(initialTab);
  const [records,setRecords]=useState([]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    let current=true;
    setError('');setRecords([]);setLoading(true);
    const promise=tab==='orders'?api.getMyOrders():api.getMyRemittances();
    Promise.resolve(promise).then(data=>{
      if(current) {
        if(!Array.isArray(data))throw new Error('پاسخ پایگاه داده معتبر نیست.');
        setRecords(data);
      }
    }).catch(err=>{if(current)setError(err.message||'سوابق قابل دریافت نیست.');})
      .finally(()=>{if(current)setLoading(false);});
    return()=>{current=false;};
  },[tab,retry]);
  return <main className="app-shell" dir="rtl">
    <div className="header">
      <button className="back-btn" type="button" aria-label="بازگشت" onClick={()=>navigate('menu')}>
        <CaretRight size={20}/>
      </button>
      <h1>سوابق مالی من</h1><span className="header-spacer"/>
    </div>
    <div className="card" style={{padding:16,marginBottom:14}}>
      <p style={{fontSize:13,marginTop:0}}>
        سفارش‌ها و حواله‌های قبلی مستقیماً از دیتابیس اصلی صراف (Supabase) دریافت می‌شوند.
        در این صفحه امکان پرداخت یا ثبت حواله وجود ندارد.
      </p>
      <div className="choice-row" role="group" aria-label="نوع سوابق">
        <button type="button" className={'choice-btn '+(tab==='orders'?'selected':'')}
          onClick={()=>setTab('orders')}>📦 سفارش‌های من</button>
        <button type="button" className={'choice-btn '+(tab==='remittances'?'selected':'')}
          onClick={()=>setTab('remittances')}>💸 حواله‌های من</button>
      </div>
      <button type="button" className="btn btn-outline" style={{marginTop:12}}
        onClick={()=>setRetry(x=>x+1)} disabled={loading}>
        <ArrowClockwise size={16}/> بروزرسانی
      </button>
      {!isCanonicalBridgeEnabled()&&<p role="status" className="notice warn">
        اتصال سوابق اصلی هنوز منتشر نشده است؛ تا آن زمان سوابق آزمایشی نمایش داده نمی‌شوند.
      </p>}
      {loading&&<p role="status" className="notice">در حال دریافت سوابق...</p>}
      {error&&<p role="alert" className="notice warn">{error}</p>}
      {!loading&&!error&&records.length===0&&<p className="notice">
        برای حساب شما در این بخش سابقه‌ای ثبت نشده است.
      </p>}
    </div>
    {!loading&&!error&&records.map(item=><article key={item.id} className="card" style={{padding:16,marginBottom:12}}>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:12}}>
        <strong>{tab==='orders'
          ? ((item.order_type==='buy'?'خرید':'فروش')+' '+item.asset)
          : ('حواله '+item.asset)}</strong>
        <span className="status-badge">{statuses[item.status]||item.status}</span>
      </div>
      <p className="num" style={{fontWeight:700}}>
        {tab==='orders'?format(item.usdt_amount):format(item.crypto_amount)} {item.asset}
      </p>
      <p className="num">{format(tab==='orders'?item.total_afn:item.payout_afn)} افغانی</p>
      <small>شناسه: {item.id} · {item.created_at?new Date(item.created_at).toLocaleDateString('fa-AF'):'—'}</small>
      {tab==='remittances'&&item.verification_status&&
        <p className="notice">تأیید بلاکچین: {item.verification_status}</p>}
    </article>)}
  </main>;
}
