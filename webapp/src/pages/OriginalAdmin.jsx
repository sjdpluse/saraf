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
 const [completionProof,setCompletionProof]=useState('');
 const [pickupCodes,setPickupCodes]=useState({});
 const [broadcastMessage,setBroadcastMessage]=useState('');
 const [broadcastKey,setBroadcastKey]=useState('');
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
  const requested=['stats','spreads','pending','setspread','confirm','broadcast','kyc','complete','remittances']
   .includes(command)?command:'stats';
  const next=requested==='remittances'?'remittances.pending':requested==='complete'?'orders.confirmed':requested==='kyc'?'kyc.pending':requested==='broadcast'?'broadcast':requested==='pending'?'orders.pending':
   requested==='confirm'?'orders.pending':requested==='setspread'?'spreads':requested;
  setSection(next);
  if(next==='stats'||next==='spreads'||next==='orders.pending'||
    next==='orders.confirmed'||next==='kyc.pending'||
    next==='remittances.pending')load(next);
  const prefillCode=params.get('currency');
  if(prefillCode&&CODES.includes(prefillCode))setCode(prefillCode);
  const amount=params.get('percent');
  if(amount&&/^\d{1,2}(?:\.\d{1,2})?$/.test(amount))setPct(amount);
  const prefill=params.get('broadcast');
  if(prefill&&prefill.length<=1024)setBroadcastMessage(prefill);
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
 async function rejectOrder(id){
  const n=Number(id);
  if(!Number.isSafeInteger(n)||n<1){setError('شماره سفارش معتبر نیست.');return;}
  if(!await showConfirm('این سفارش مطابق ربات اصلی رد و لغو شود؟'))return;
  await load('order.reject',{order_id:n});
 }
 async function completeOrder(id){
  const n=Number(id),details=completionProof.trim();
  if(!Number.isSafeInteger(n)||n<1){setError('شماره سفارش معتبر نیست.');return;}
  if(details.length<4||details.length>2000){
   setError('برای تکمیل سفارش، Tx Hash / Transaction Details واقعی (۴ تا ۲۰۰۰ حرف) لازم است.');return;
  }
  if(!await showConfirm('آیا مبلغ/رمزارز واقعاً به مشتری ارسال شده و مدرک تراکنش صحیح است؟ این عمل سفارش را تکمیل می‌کند.'))return;
  await load('order.complete',{order_id:n,completion_tx_details:details});
 }
 async function transitionRemittance(order,transition){
  const id=Number(order?.id);
  if(!Number.isSafeInteger(id)||id<=0){setError('شناسه حواله معتبر نیست.');return;}
  const code=String(pickupCodes[id]||'').trim();
  if(transition==='pay'&&!/^[0-9]{6}$/.test(code)){
   setError('برای تکمیل پرداخت واقعی، کد شش‌رقمی را پس از تطبیق مدرک هویت گیرنده وارد کنید.');return;
  }
  const prompts={
   ready:'دریافت کریپتو را در شبکه بررسی کرده‌اید؟ تنها پس از تأیید دریافت واقعی و تطبیق مبلغ، حواله آمادهٔ پرداخت شود.',
   hold:'حواله برای بررسی بیشتر متوقف شود؟',
   cancel:'حواله لغو شود؟ این اقدام ممکن است نیازمند بررسی بازپرداخت باشد.',
   pay:'آیا مدرک هویت گیرنده تطبیق شده، وجه نقد واقعاً پرداخت شده و کد شش‌رقمی از گیرنده دریافت شده است؟',
  };
  const warning=transition==='ready'&&order.verification_status!=='verified'
    ?'⚠️ وضعیت تأیید بلاکچین در سیستم «تأیید شده» نیست؛ انجام این عمل فقط با تأیید مستقل دریافت واقعی توسط مدیر مجاز است.\\n\\n':'';
  if(!await showConfirm(warning+prompts[transition]))return;
  await load('remittances.transition',{
   order_id:id,transition,...(transition==='pay'?{pickup_code:code}:{}),
  });
  setPickupCodes(prev=>({...prev,[id]:''}));
 }
 async function reviewKyc(id,decision){
  const chat_id=Number(id);
  if(!Number.isSafeInteger(chat_id)||chat_id<=0||
      !['verify','reject'].includes(decision)){
   setError('شناسهٔ کاربر یا تصمیم معتبر نیست.');return;
  }
  const msg=decision==='verify'
   ?'پس از بررسی تصویر تذکره و سلفی، احراز هویت این کاربر را تایید می‌کنید؟'
   :'با رد این اسناد، حساب کاربر مطابق سیستم اصلی محدود می‌شود. آیا مطمئن هستید؟';
  if(!await showConfirm(msg))return;
  await load('kyc.review',{chat_id,decision});
 }
 async function createBroadcast(event){
  event.preventDefault();
  const body=broadcastMessage.trim();
  if(!body||body.length>4096){
   setError('متن پیام باید بین ۱ تا ۴۰۹۶ حرف باشد.');return;
  }
  if(!await showConfirm('این پیام به تمام کاربران فعال ربات صراف فرستاده شود؟\\n\\n'+
    body.slice(0,200)))return;
  let id=broadcastKey;
  if(!id){id=globalThis.crypto?.randomUUID?.()||'';
   if(!id){setError('شناسهٔ امن برای جلوگیری از ارسال تکراری در دسترس نیست.');return;}
   setBroadcastKey(id);
  }
  await load('broadcast.create',{message:body,idempotency_key:id});
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
   <button disabled={busy} onClick={()=>{setSection('orders.confirmed');load('orders.confirmed');}}>📦 سفارش‌های تأییدشده</button>
   <button disabled={busy} onClick={()=>{setSection('remittances.pending');load('remittances.pending');}}>💸 حواله‌های در جریان</button>
   <button disabled={busy} onClick={()=>{setSection('kyc.pending');load('kyc.pending');}}>🪪 احراز هویت</button>
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
       <button type="button" disabled={busy} style={{marginRight:8}}
        onClick={()=>rejectOrder(order.id)}>❌ رد سفارش</button>
     </article>)}
  </section>}
  {result?.action==='remittances.pending'&&<section>
   <h2 style={{fontSize:17}}>حواله‌ها — بررسی کریپتو، مدرک هویت و پرداخت نقدی</h2>
   <p className="notice">کد دریافت تنها به مشتری ارسال می‌شود و در این پنل نمایش داده نمی‌شود. برای ثبت پرداخت باید کد شش‌رقمی را از گیرنده بگیرید و تذکره را تطبیق کنید.</p>
   {!result.orders?.length&&<p>حواله‌ای در انتظار بررسی نیست.</p>}
   {(result.orders||[]).map(order=>
    <article className="notice" key={order.id} style={{marginTop:12}}>
     <b>REM-{String(order.id).padStart(6,'0')}</b>
     <p>{order.crypto_amount} {order.asset} | شبکه: {order.network}
     {' | '}{cash(order.payout_afn)} افغانی</p>
     <p>گیرنده: {order.beneficiary_full_name} | {order.beneficiary_phone}</p>
     <p>موقعیت: {order.beneficiary_province} / {order.beneficiary_city}</p>
     <p>وضعیت: {order.status} | تأیید بلاکچین: {order.verification_status||'نامعلوم'}
     {' | '}تأیید شبکه: {order.chain_confirmations??0}</p>
     {order.tx_hash&&<p style={{overflowWrap:'anywhere'}}>Tx Hash: {order.tx_hash}</p>}
     {order.beneficiary_id_url?
      <a href={order.beneficiary_id_url} target="_blank"
       rel="noopener noreferrer" referrerPolicy="no-referrer">🪪 مشاهده خصوصی تذکره گیرنده (۹۰ ثانیه)</a>
      :<p>سند هویتی گیرنده در دسترس نیست؛ قبل از پرداخت بررسی شود.</p>}
     <div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:12}}>
      {['transfer_submitted','on_hold'].includes(order.status)&&
       <button type="button" disabled={busy}
        onClick={()=>transitionRemittance(order,'ready')}>✅ کریپتو دریافت شد — آماده پرداخت</button>}
      {['transfer_submitted','payout_ready'].includes(order.status)&&
       <button type="button" disabled={busy}
        onClick={()=>transitionRemittance(order,'hold')}>⏸ توقف بررسی</button>}
      {['transfer_submitted','on_hold'].includes(order.status)&&
       <button type="button" disabled={busy}
        onClick={()=>transitionRemittance(order,'cancel')}>❌ لغو حواله</button>}
     </div>
     {order.status==='payout_ready'&&<div style={{marginTop:14}}>
      <label>کد دریافت ۶ رقمی که از گیرنده پس از تطبیق هویت گرفته‌اید:</label>
      <input aria-label={'کد دریافت حواله '+order.id} className="input num"
       type="text" inputMode="numeric" maxLength={6}
       value={pickupCodes[order.id]||''}
       onChange={e=>setPickupCodes(prev=>({...prev,
        [order.id]:e.target.value.replace(/[^0-9]/g,'').slice(0,6)}))}
       placeholder="••••••" autoComplete="off" />
      <button type="button" disabled={busy||String(pickupCodes[order.id]||'').length!==6}
       onClick={()=>transitionRemittance(order,'pay')}>💵 پرداخت انجام شد — تکمیل با کد</button>
     </div>}
    </article>)}
   <button type="button" disabled={busy} style={{marginTop:12}}
    onClick={()=>load('remittances.pending')}>🔄 بازخوانی وضعیت و لینک‌های سند</button>
  </section>}
  {result?.action==='remittances.transition'&&<div className="notice">
   ✅ وضعیت حواله {result.result?.order_code} به {result.result?.status} تغییر کرد.
   {result.result?.customer_notified===false&&
    ' اطلاع‌رسانی به مشتری موفق نشد؛ به‌صورت دستی پیگیری کنید.'}
   <div><button type="button" disabled={busy} onClick={()=>{
     setSection('remittances.pending');load('remittances.pending');
   }}>بازگشت به حواله‌ها</button></div>
  </div>}
  {result?.action==='orders.confirmed'&&<section>
   <h2 style={{fontSize:17}}>سفارش‌های تأییدشده و در انتظار تکمیل واقعی</h2>
   <p className="notice">تا زمان ارسال واقعی وجه/رمزارز، سفارش را تکمیل نکنید. مطابق ربات اصلی درج Transaction Details یا Tx Hash الزامی است.</p>
   <textarea aria-label="Transaction Details / Tx Hash واقعی" rows={3}
    value={completionProof} maxLength={2000}
    onChange={e=>setCompletionProof(e.target.value)}
    placeholder="Tx Hash / Transaction Details واقعی پس از ارسال وجه به مشتری" />
   {!result.orders?.length&&<p>سفارش تأییدشده‌ای در انتظار تکمیل نیست.</p>}
   {(result.orders||[]).map(order=>
    <article className="notice" key={order.id} style={{marginTop:10}}>
     <b>{order.asset||'USDT'}-{String(order.id).padStart(5,'0')}</b>
     <p>{order.order_type==='buy'?'خرید':'فروش'} | {cash(order.usdt_amount)}
       {' '}{order.asset} | {cash(order.total_afn)} افغانی</p>
     <button type="button" disabled={busy||completionProof.trim().length<4}
      onClick={()=>completeOrder(order.id)}>📦 تکمیل با مدرک تراکنش</button>
    </article>)}
   <button type="button" disabled={busy} style={{marginTop:12}}
    onClick={()=>load('orders.confirmed')}>🔄 بازخوانی</button>
  </section>}
  {result?.action==='order.reject'&&<div className="notice">
   ❌ سفارش {cash(result.result?.order_id)} رد و لغو شد.
   {result.result?.customer_notified===false&&' اطلاع‌رسانی به مشتری موفق نشد.'}
   <div><button type="button" disabled={busy}
    onClick={()=>{setSection('orders.pending');load('orders.pending');}}>
    بازگشت به سفارش‌های در انتظار</button></div>
  </div>}
  {result?.action==='order.complete'&&<div className="notice">
   ✅ سفارش {cash(result.result?.order_id)} با مدرک تراکنش ثبت‌شده تکمیل شد.
   {result.result?.customer_notified===false&&' اطلاع‌رسانی به مشتری موفق نشد.'}
   <div><button type="button" disabled={busy}
     onClick={()=>{setSection('orders.confirmed');load('orders.confirmed');}}>
     بازگشت به سفارش‌های تأییدشده</button></div>
  </div>}
  {result?.action==='kyc.pending'&&<section>
   <h2 style={{fontSize:17}}>اسناد در انتظار بررسی هویت</h2>
   <p className="notice">فقط مدیر مجاز می‌تواند تصویر خصوصی تذکره و سلفی را با لینک موقت ۹۰ثانیه‌ای مشاهده کند. پیش از تأیید، هر دو سند را بررسی کنید.</p>
   {!result.customers?.length&&<p>درخواستی در انتظار بررسی نیست.</p>}
   {(result.customers||[]).map(customer=>
    <article className="notice" key={customer.chat_id} style={{marginBottom:12}}>
     <b>{customer.first_name} {customer.last_name}</b>
     <p>شناسهٔ مشتری: {customer.chat_id} | {customer.phone||'شماره ثبت نشده'}</p>
     <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>
      <div>
       <p>سند هویتی</p>
       {customer.id_url?<a href={customer.id_url} target="_blank" rel="noopener noreferrer"
        referrerPolicy="no-referrer">مشاهده تصویر تذکره</a>
        :<span>تصویر فعلاً در دسترس نیست</span>}
      </div>
      <div>
       <p>سلفی مشتری</p>
       {customer.selfie_url?<a href={customer.selfie_url} target="_blank"
        rel="noopener noreferrer" referrerPolicy="no-referrer">مشاهده تصویر سلفی</a>
        :<span>تصویر فعلاً در دسترس نیست</span>}
      </div>
     </div>
     <div style={{display:'flex',gap:10,marginTop:12}}>
      <button type="button" disabled={busy||!customer.id_url||!customer.selfie_url}
       onClick={()=>reviewKyc(customer.chat_id,'verify')}>✅ تأیید احراز هویت</button>
      <button type="button" disabled={busy}
       onClick={()=>reviewKyc(customer.chat_id,'reject')}>❌ رد اسناد</button>
     </div>
    </article>)}
   <button type="button" disabled={busy} onClick={()=>load('kyc.pending')}>
    🔄 بازخوانی درخواست‌ها و لینک‌های خصوصی
   </button>
  </section>}
  {result?.action==='kyc.review'&&<div className="notice">
   {result.result?.status==='verified'?'✅ هویت مشتری تأیید شد.':
    '❌ مدارک مشتری رد و وضعیت حساب محدود شد.'}
   {' '}شناسه: {result.result?.chat_id}
   {result.result?.duplicate?' (پیشتر بررسی شده است)':''}
   {result.result?.customer_notified===false&&
     ' اطلاع‌رسانی به مشتری موفق نشد؛ وضعیت را بررسی کنید.'}
   <div><button type="button" disabled={busy}
     onClick={()=>{setSection('kyc.pending');load('kyc.pending');}}>
     بازگشت به بررسی اسناد
   </button></div>
  </div>}
  {result?.action==='order.confirm'&&<p className="notice">
    ✅ سفارش {cash(result.result?.order_id)} تأیید شد.
    {result.result?.customer_notified===false&&
      ' پیام اطلاع‌رسانی به کاربر ارسال نشد؛ وضعیت سفارش را بررسی کنید.'}
  </p>}
  {result?.action==='spread.set'&&<p className="notice">
    ✅ اسپرد {result.result?.currency?.toUpperCase()} روی
    {' '}{cash(result.result?.spread_percent)}٪ ثبت شد.
  </p>}
  <section style={{margin:'24px 0',display:'grid',gap:10}}>
   <h2 style={{fontSize:17}}>ارسال پیام همگانی (/broadcast)</h2>
   <form style={{display:'grid',gap:10}} onSubmit={createBroadcast}>
    <textarea aria-label="متن پیام همگانی" rows={4}
     maxLength={4096} value={broadcastMessage}
     onChange={event=>{
      setBroadcastMessage(event.target.value);
      setBroadcastKey('');
     }} placeholder="متن پیام همگانی برای کاربران فعال" />
    <p>فقط پس از تأیید مدیر، پیام به صف ارسال خصوصی می‌رود.
     کاربرانی که /stop زده‌اند پیام دریافت نمی‌کنند.</p>
    <button disabled={busy||!broadcastMessage.trim()} type="submit">
     تأیید و ثبت پیام در صف
    </button>
   </form>
   {result?.action==='broadcast.create'&&<div className="notice">
     ✅ پیام در صف قرار گرفت. شناسه: {result.result?.broadcast_id}
     {' — '}تعداد گیرندگان: {cash(result.result?.audience_size)}
     {result.result?.duplicate?' (درخواست تکراری)':''}
     <div style={{marginTop:8}}>
      <button disabled={busy} onClick={()=>load('broadcast.status',{
       broadcast_id:result.result?.broadcast_id,
      })}>مشاهده وضعیت ارسال</button>
     </div>
   </div>}
   {result?.action==='broadcast.status'&&<div className="notice">
     وضعیت: {result.result?.status}
     {' | '}ارسال‌شده: {cash(result.result?.deliveries?.sent)}
     {' | '}ناموفق: {cash(result.result?.deliveries?.failed)}
     {' | '}نامعلوم: {cash(result.result?.deliveries?.uncertain)}
     {' | '}انصراف‌داده: {cash(result.result?.deliveries?.skipped)}
   </div>}
  </section>
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
   برای امنیت، ارسال همگانی بدون فعال‌سازی مجزای سرور و بررسی دستی انجام نمی‌شود.
  </p>
 </main>;
}
