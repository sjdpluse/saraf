import {useEffect,useState} from 'react';
import {originalAdminCommand} from '../lib/originalAdminBridge';
import {showConfirm} from '../lib/telegram';
import {ArrowRight, CaretDown, SlidersHorizontal, Vault} from '@phosphor-icons/react';
import AdminOrderDesk from './AdminOrderDesk';
import {orderNumber} from '../lib/adminOrders';
import './OriginalAdmin.css';

const CODES=['usd','eur','gbp','pkr','irr','aed','inr','sar',
 'try','cny','aud','cad','chf','sek'];
const cash=n=>Number(n||0).toLocaleString('en-US',{
 maximumFractionDigits:2,
});
const sections = {
 orders:'سفارش‌های مشتریان', 'remittances.pending':'حواله‌های در جریان',
 'kyc.pending':'احراز هویت', stats:'کاربران', spreads:'اسپرد ارزها',
 broadcast:'پیام همگانی', post:'نشر در شبکه‌های اجتماعی',
};
const links = {remittances:'remittances.pending', kyc:'kyc.pending', setspread:'spreads'};
function initialAdminPage(){
 const params=new URLSearchParams(location.search);
 const cmd=params.get('admin');
 const section=Object.hasOwn(links,cmd) ? links[cmd] : Object.hasOwn(sections,cmd) ? cmd : 'orders';
 return {section, queue:cmd==='complete'?'confirmed':'pending',
  id:section==='orders'?orderNumber(params.get('order_id')||''):null};
}
export default function OriginalAdmin({navigate}){
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [result,setResult]=useState(null);
 const [initial]=useState(initialAdminPage);
 const [section,setSection]=useState(initial.section);
 const [working,setWorking]=useState(false);
 const [code,setCode]=useState('usd');
 const [pct,setPct]=useState('0.6');
 const [orderId,setOrderId]=useState(initial.id);
 const [pickupCodes,setPickupCodes]=useState({});
 const [broadcastMessage,setBroadcastMessage]=useState('');
 const [broadcastKey,setBroadcastKey]=useState('');
 const [socialRequestId,setSocialRequestId]=useState(null);
 const [socialKey,setSocialKey]=useState('');
 async function load(action,input={}){
  setBusy(true);setError('');
  try{
   const response=await originalAdminCommand(action,input);
   setResult({action,...response});
   return response;
  }catch(e){
   setResult(null);setError(e?.message||'ارتباط با مدیریت ناموفق بود.');
   return null;
  }finally{setBusy(false);}
 }
 useEffect(()=>{
  const params=new URLSearchParams(location.search);
  if (['stats','spreads','kyc.pending','remittances.pending'].includes(initial.section))
   load(initial.section);
  const prefillCode=params.get('currency');
  if(prefillCode&&CODES.includes(prefillCode))setCode(prefillCode);
  const amount=params.get('percent');
  if(amount&&/^\d{1,2}(?:\.\d{1,2})?$/.test(amount))setPct(amount);
  const prefill=params.get('broadcast');
  if(prefill&&prefill.length<=1024)setBroadcastMessage(prefill);
 },[]);
 function selectSection(next){
  setError('');setResult(null);setOrderId(null);setSection(next);
  if (['stats','spreads','kyc.pending','remittances.pending'].includes(next)) load(next);
 }
 function back(){
  if(orderId) setOrderId(null);
  else if(section!=='orders') selectSection('orders');
  else navigate('menu');
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
 async function manualSocialPost(){
  // Original handlers/admin.py manual_post(force=True) requires deliberate
  // admin confirmation; queue the same two posts without direct browser Graph
  // API calls. Preserve idempotency if Telegram UI/network retries.
  if(!await showConfirm('آیا پست نرخ لحظه‌یی اسعار، طلا و نقره در هر دو صفحهٔ اصلی فیسبوک و اینستاگرام صراف منتشر شود؟'))return;
  let key=socialKey;
  if(!key){key=globalThis.crypto?.randomUUID?.()||'';
   if(!key){setError('شناسهٔ امن نشر پست در دسترس نیست.');return;}
   setSocialKey(key);
  }
  const created=await load('social.post.create',{idempotency_key:key});
  const id=Number(created?.result?.request_id);
  if(Number.isSafeInteger(id)&&id>0)setSocialRequestId(id);
 }
 async function checkManualSocialPost(){
  if(!Number.isSafeInteger(Number(socialRequestId))||Number(socialRequestId)<=0)return;
  await load('social.post.status',{request_id:Number(socialRequestId)});
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
 return <main className="app-shell saraf-desk" dir="rtl">
  <header className="desk-header">
   <div className="desk-brand"><span className="desk-emblem"><Vault size={26}/></span><h1>مدیریت صراف</h1></div>
   <div className="desk-header-tools">
    <label className="desk-tool-picker"><SlidersHorizontal size={18}/><span>بخش‌ها</span><CaretDown size={12}/>
     <select aria-label="بخش‌های مدیریت" disabled={busy||working} value={section} onChange={e=>selectSection(e.target.value)}>
      {Object.entries(sections).map(([key,title])=><option key={key} value={key}>{title}</option>)}
     </select>
    </label>
    <button type="button" className="desk-exit back-btn" disabled={busy||working} onClick={back} aria-label="بازگشت از مدیریت"><ArrowRight size={20}/></button>
   </div>
  </header>
  {section==='orders'&&<AdminOrderDesk initialQueue={initial.queue} orderId={orderId} setWorking={setWorking}
    openOrder={id=>{setOrderId(id);window.scrollTo(0,0);}}/>}
  {section!=='orders'&&<div className="desk-aux">
   <h2>{sections[section]}</h2>
  {section==='post'&&<section className="notice">
   <h2>📢 نشر پست اصلی صراف در فیسبوک و اینستاگرام</h2>
   <p>همان تصویر و کپشن نرخ لحظه‌یی نسخهٔ اصلی. نشر تنها پس از تأیید مدیر و آماده‌بودن اتصال Meta انجام می‌شود؛ تغییر در پرداخت مشتریان ندارد.</p>
   <button type="button" disabled={busy||Boolean(socialRequestId)}
     onClick={manualSocialPost}>✅ تأیید و درخواست نشر در هر دو صفحه</button>
   {socialRequestId&&<div style={{marginTop:12}}>
    <p>شناسهٔ درخواست: {socialRequestId}</p>
    <button type="button" disabled={busy} onClick={checkManualSocialPost}>🔄 بررسی نتیجه نشر</button>
   </div>}
   {['social.post.create','social.post.status'].includes(result?.action)&&
    <p role="status">وضعیت نشر: {result?.result?.status||'نامعلوم'}
    {result?.result?.facebook&&' | Facebook: '+result.result.facebook}
    {result?.result?.instagram&&' | Instagram: '+result.result.instagram}
    </p>}
   {socialRequestId&&['done','partial','failed','needs_review'].includes(result?.result?.status)&&
    <button type="button" onClick={()=>{setSocialKey('');setSocialRequestId(null);setResult(null);}}>درخواست جدید</button>}
  </section>}
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
  {result?.action==='spread.set'&&<p className="notice">
    ✅ اسپرد {result.result?.currency?.toUpperCase()} روی
    {' '}{cash(result.result?.spread_percent)}٪ ثبت شد.
  </p>}
  {section==='broadcast'&&<section>
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
  </section>}
  {section==='spreads'&&<form onSubmit={saveSpread} style={{display:'grid',gap:10,marginTop:22}}>
   <h2 style={{fontSize:17}}>تنظیم اسپرد (/setspread)</h2>
   <select value={code} onChange={event=>setCode(event.target.value)}>
     {CODES.map(c=><option key={c} value={c}>{c.toUpperCase()}</option>)}
   </select>
   <input aria-label="درصد اسپرد" type="number" min="0" max="20"
    step="0.1" value={pct} onChange={event=>setPct(event.target.value)}/>
   <button disabled={busy} type="submit">ثبت اسپرد</button>
  </form>}
  {error&&!busy&&['stats','spreads','kyc.pending','remittances.pending'].includes(section)&&
    <button type="button" onClick={()=>load(section)}>بازخوانی بخش</button>}
  </div>}
 </main>;
}
