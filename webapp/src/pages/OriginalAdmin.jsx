import {useEffect,useState} from 'react';
import {originalAdminCommand} from '../lib/originalAdminBridge';
import {showConfirm} from '../lib/telegram';

const CODES=['usd','eur','gbp','pkr','irr','aed','inr','sar',
 'try','cny','aud','cad','chf','sek'];
const cash=n=>Number(n||0).toLocaleString('en-US',{
 maximumFractionDigits:2,
});
export default function OriginalAdmin({navigate}){
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [result,setResult]=useState(null);
 const [section,setSection]=useState('stats');
 const [code,setCode]=useState('usd');
 const [pct,setPct]=useState('0.6');
 const [orderId,setOrderId]=useState('');
 async function load(action,input={}){
  setBusy(true);setError('');
  try{
   const response=await originalAdminCommand(action,input);
   setResult({action,...response});
  }catch(e){
   setResult(null);setError(e?.message||'ارتباط با مدیریت ناموفق بود.');
  }finally{setBusy(false);}
 }
 useEffect(()=>{
  const params=new URLSearchParams(location.search);
  const command=params.get('admin')||'';
  const requested=['stats','spreads','pending','setspread','confirm']
   .includes(command)?command:'stats';
  const next=requested==='pending'?'orders.pending':
   requested==='confirm'?'orders.pending':requested==='setspread'?'spreads':requested;
  setSection(next);
  if(next==='stats'||next==='spreads'||next==='orders.pending')load(next);
  const prefillCode=params.get('currency');
  if(prefillCode&&CODES.includes(prefillCode))setCode(prefillCode);
  const amount=params.get('percent');
  if(amount&&/^\d{1,2}(?:\.\d{1,2})?$/.test(amount))setPct(amount);
  const id=params.get('order_id');
  if(id&&/^[1-9]\d{0,12}$/.test(id))setOrderId(id);
 },[]);
 async function confirmOrder(id){
  const n=Number(id);
  if(!Number.isSafeInteger(n)||n<1){setError('شماره سفارش معتبر نیست.');return;}
  if(!await showConfirm('سفارش USDT-'+String(n).padStart(5,'0')+
    ' را مطابق دستور اصلی /usdtconfirm تأیید می‌کنید؟'))return;
  await load('order.confirm',{order_id:n});
 }
 async function saveSpread(event){
  event.preventDefault();
  const num=Number(pct);
  if(!CODES.includes(code)||!Number.isFinite(num)||num<0||num>20){
   setError('درصد اسپرد باید بین ۰ تا ۲۰ باشد.');return;
  }
  if(!await showConfirm('اسپرد '+code.toUpperCase()+' روی '+num+'٪ ذخیره شود؟'))return;
  await load('spread.set',{currency:code,spread_percent:num});
 }
 return <main className="app-shell" style={{padding:'20px 18px 100px',direction:'rtl'}}>
  <header style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}>
   <h1 style={{fontSize:21}}>مدیریت صراف</h1>
   <button type="button" onClick={()=>navigate('menu')}>بازگشت</button>
  </header>
  <p className="notice">همان دستورات مدیریت ربات اصلی؛ دسترسی تنها با احراز هویت امضاشدهٔ تلگرام و تأیید مدیر در سرور امکان‌پذیر است.</p>
  <div style={{display:'flex',gap:8,flexWrap:'wrap',margin:'18px 0'}}>
   <button disabled={busy} onClick={()=>{setSection('stats');load('stats');}}>📈 آمار</button>
   <button disabled={busy} onClick={()=>{setSection('spreads');load('spreads');}}>📐 اسپردها</button>
   <button disabled={busy} onClick={()=>{setSection('orders.pending');load('orders.pending');}}>📋 سفارش‌های در انتظار</button>
  </div>
  {busy&&<p role="status">در حال بررسی ...</p>}
  {error&&<p role="alert" style={{color:'#b42318'}}>{error}</p>}
  {result?.action==='stats'&&<section className="notice">
   📈 تعداد کاربران فعال ربات: <b>{cash(result.active_users)}</b>
  </section>}
  {result?.action==='spreads'&&<section>
   <h2 style={{fontSize:17}}>اسپرد فعلی ارزها</h2>
   <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8}}>
    {Object.entries(result.spreads||{}).map(([currency,value])=>
     <div className="notice" key={currency}>
      <b>{currency.toUpperCase()}</b> — {cash(value)}٪
     </div>)}
   </div>
  </section>}
  {result?.action==='orders.pending'&&<section>
    <h2 style={{fontSize:17}}>سفارش‌های در انتظار</h2>
    {!result.orders?.length&&<p>سفارش در انتظاری وجود ندارد.</p>}
    {(result.orders||[]).map(order=>
     <article className="notice" key={order.id} style={{marginBottom:10}}>
       <b>{order.asset||'USDT'}-{String(order.id).padStart(5,'0')}</b>
       <p>{order.order_type==='buy'?'خرید':'فروش'} | {cash(order.usdt_amount)} {order.asset}
       {' | '}{cash(order.total_afn)} افغانی</p>
       <button type="button" disabled={busy}
        onClick={()=>confirmOrder(order.id)}>تأیید سفارش</button>
     </article>)}
  </section>}
  {result?.action==='order.confirm'&&<p className="notice">
    ✅ سفارش {cash(result.result?.order_id)} تأیید شد.
    {result.result?.customer_notified===false&&
      ' پیام اطلاع‌رسانی به کاربر ارسال نشد؛ وضعیت سفارش را بررسی کنید.'}
  </p>}
  {result?.action==='spread.set'&&<p className="notice">
    ✅ اسپرد {result.result?.currency?.toUpperCase()} روی
    {' '}{cash(result.result?.spread_percent)}٪ ثبت شد.
  </p>}
  <form onSubmit={saveSpread} style={{display:'grid',gap:10,marginTop:22}}>
   <h2 style={{fontSize:17}}>تنظیم اسپرد (/setspread)</h2>
   <select value={code} onChange={event=>setCode(event.target.value)}>
     {CODES.map(c=><option key={c} value={c}>{c.toUpperCase()}</option>)}
   </select>
   <input aria-label="درصد اسپرد" type="number" min="0" max="20"
    step="0.1" value={pct} onChange={event=>setPct(event.target.value)}/>
   <button disabled={busy} type="submit">ثبت اسپرد</button>
  </form>
  <section style={{marginTop:20}}>
   <h2 style={{fontSize:17}}>تأیید سفارش (/usdtconfirm)</h2>
   <input aria-label="شماره سفارش" type="number" min="1"
     value={orderId} onChange={e=>setOrderId(e.target.value)}/>
   <button type="button" disabled={busy} onClick={()=>confirmOrder(orderId)}>
    تأیید شماره سفارش
   </button>
  </section>
  <p className="notice" style={{marginTop:24}}>
   ارسال همگانی (/broadcast) تا انتقال کامل صف پیام‌رسانی غیرفعال است.
  </p>
 </main>;
}
