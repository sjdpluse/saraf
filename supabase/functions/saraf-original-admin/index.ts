// Migration of ORIGINAL main:handlers/admin.py commands to the existing
// Supabase backend. Admin identity is SERVER-verified against the original
// bot's Telegram Mini App initData AND a server-only ID allowlist.
// No Railway, no browser-supplied actor ID, no public finance RPCs.
// Default OFF: read and write must be enabled separately after E2E.
import { createClient } from 'npm:@supabase/supabase-js@2.57.0';
import { verifyTelegramInitData } from './telegram-auth.mjs';

const ORIGIN='https://app8533795882.tgcloud.ai';
const BOT=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const URL=Deno.env.get('SUPABASE_URL')||'';
const KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const READ=Deno.env.get('SARAF_ORIGINAL_ADMIN_READ_ENABLED')==='true';
const WRITE=Deno.env.get('SARAF_ORIGINAL_ADMIN_WRITES_ENABLED')==='true';
const BROADCAST=Deno.env.get('SARAF_ORIGINAL_BROADCAST_ENABLED')==='true';
const ADMINS=(Deno.env.get('SARAF_ADMIN_CHAT_IDS')||'')
 .split(',').map(x=>x.trim()).filter(x=>/^[1-9][0-9]{0,15}$/.test(x));
const CODES=new Set([
 'usd','eur','gbp','pkr','irr','aed','inr','sar','try','cny',
 'aud','cad','chf','sek',
]);
const DEFAULT_SPREADS:Record<string,number>={
 usd:0.6,eur:0.8,gbp:1,aed:0.8,sar:0.8,pkr:1.5,irr:2,
 inr:1.5,try:1.5,cny:1.5,aud:1.2,cad:1.2,chf:1.2,sek:1.8,
};
function answer(origin:string,status:number,body:unknown){
 return new Response(JSON.stringify(body),{status,headers:{
  'Content-Type':'application/json; charset=utf-8',
  'Cache-Control':'no-store','Vary':'Origin',
  ...(origin===ORIGIN?{'Access-Control-Allow-Origin':ORIGIN}:{}),
  'Access-Control-Allow-Headers':'Content-Type,X-Telegram-Init-Data',
  'Access-Control-Allow-Methods':'POST,OPTIONS',
 }});
}
function isOwner(userId:number){
 return ADMINS.length>0&&ADMINS.includes(String(userId));
}
function isWrite(action:string){
 return action==='spread.set'||action==='order.confirm'||
   action==='broadcast.create'||action==='kyc.review'||
   action==='order.reject'||action==='order.complete'||
   action==='remittances.transition';
}
async function notifyOriginalCustomer(orderId:number,chatId:number,asset:string){
 if(!BOT||!Number.isSafeInteger(chatId)||chatId<=0)return false;
 try{
  const r=await fetch('https://api.telegram.org/bot'+BOT+'/sendMessage',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({
    chat_id:chatId,
    text:'✅ سفارش شما ('+(asset==='USDC'?'USDC':'USDT')+'-'+String(orderId).padStart(5,'0')+
       ') تأیید و در حال پردازش نهایی است.',
   }),
   signal:AbortSignal.timeout(6500),
  });
  return r.ok;
 }catch{return false;}
}
async function notifyOriginalKycCustomer(chatId:number,status:string){
 if(!BOT||!Number.isSafeInteger(chatId)||chatId<=0)return false;
 const message=status==='verified'
  ?'✅ هویت شما تایید شد. از این پس سفارش‌های شما سریع‌تر پردازش می‌شوند.'
  :'⚠️ متاسفانه مدارک ارسالی شما تایید نشد.\n'+
    'لطفاً برای پیگیری با پشتیبانی تماس بگیرید: '+
    (Deno.env.get('SUPPORT_TELEGRAM_USERNAME')||'@sarafiaf_bot');
 try{
  const r=await fetch('https://api.telegram.org/bot'+BOT+'/sendMessage',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({chat_id:chatId,text:message}),
   signal:AbortSignal.timeout(6500),
  });
  return r.ok;
 }catch{return false;}
}
async function notifyOriginalFinalized(chatId:number,orderId:number,
 asset:string,status:string,details:string){
 if(!BOT||!Number.isSafeInteger(chatId)||chatId<=0)return false;
 const code=(asset==='USDC'?'USDC':'USDT')+'-'+String(orderId).padStart(5,'0');
 const text=status==='completed'
  ?'📦 سفارش '+code+' با موفقیت تکمیل شد.\\n'+
   '🔎 Transaction Details / Tx Hash:\\n'+details+
   '\\nلطفاً از بخش «سفارش‌های من» در اپلیکیشن اصلی به سفارش امتیاز بدهید.'
  :'⚠️ سفارش '+code+' قابل تایید نبود.\\n'+
   'لطفاً برای پیگیری با پشتیبانی تماس بگیرید: '+
    (Deno.env.get('SUPPORT_TELEGRAM_USERNAME')||'@sarafiaf_bot');
 try{
  const r=await fetch('https://api.telegram.org/bot'+BOT+'/sendMessage',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({chat_id:chatId,text}),
   signal:AbortSignal.timeout(6500),
  });
  return r.ok;
 }catch{return false;}
}
async function notifyOriginalRemittanceCustomer(row:{
 chat_id:number;order_code:string;status:string;
 beneficiary_full_name?:string;payout_afn?:number;pickup_code?:string,
}){
 if(!BOT||!Number.isSafeInteger(row.chat_id)||row.chat_id<=0)return false;
 const code=row.order_code;
 const support=Deno.env.get('SUPPORT_TELEGRAM_USERNAME')||'@sarafiaf_bot';
 let message='';
 if(row.status==='payout_ready'){
  if(!/^\d{6}$/.test(String(row.pickup_code||'')))return false;
  message='✅ حوالهٔ شما ('+code+') آمادهٔ پرداخت در افغانستان است.\n\n'+
   'گیرنده: '+String(row.beneficiary_full_name||'')+'\n'+
   'مبلغ قابل دریافت: '+Number(row.payout_afn||0).toLocaleString('en-US')+
   ' افغانی\nکد دریافت: '+row.pickup_code+'\n\n'+
   'کد دریافت را فقط با گیرنده شریک کنید. گیرنده هنگام دریافت باید تذکره همراه داشته باشد.';
 }else if(row.status==='completed'){
  message='✅ حوالهٔ شما ('+code+') با موفقیت به گیرنده پرداخت و تکمیل شد.';
 }else if(row.status==='on_hold'){
  message='⏸ حوالهٔ شما ('+code+') برای بررسی بیشتر موقتاً متوقف شده است. برای پیگیری: '+support;
 }else if(row.status==='cancelled'){
  message='❌ حوالهٔ شما ('+code+') لغو شد. برای جزئیات با پشتیبانی تماس بگیرید: '+support;
 }else return false;
 try{
  const response=await fetch('https://api.telegram.org/bot'+BOT+'/sendMessage',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({chat_id:row.chat_id,text:message}),
   signal:AbortSignal.timeout(6500),
  });
  return response.ok;
 }catch{return false;}
}
Deno.serve(async(req:Request)=>{
 const origin=req.headers.get('origin')||'';
 if(req.method==='OPTIONS')return origin===ORIGIN
  ?new Response(null,{status:204,headers:{
    'Access-Control-Allow-Origin':ORIGIN,
    'Access-Control-Allow-Methods':'POST,OPTIONS',
    'Access-Control-Allow-Headers':'Content-Type,X-Telegram-Init-Data',
    'Vary':'Origin',
  }})
  :answer('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(req.method!=='POST')return answer(origin,405,{error:'METHOD_NOT_ALLOWED'});
 if(origin!==ORIGIN)return answer('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(!BOT||!URL||!KEY||!ADMINS.length)
  return answer(origin,503,{error:'ORIGINAL_ADMIN_NOT_CONFIGURED'});
 const actor=await verifyTelegramInitData(
  req.headers.get('x-telegram-init-data')||'',BOT);
 if(!actor)return answer(origin,401,{error:'INVALID_TELEGRAM_AUTH'});
 if(!isOwner(actor.id))return answer(origin,403,{error:'ADMIN_NOT_ALLOWED'});
 if(!READ)return answer(origin,503,{error:'ORIGINAL_ADMIN_NOT_ENABLED'});

 let body:Record<string,unknown>;
 try{
  const raw=await req.text();
  if(raw.length>3000)return answer(origin,413,{error:'REQUEST_TOO_LARGE'});
  const parsed=JSON.parse(raw);
  if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))
   return answer(origin,400,{error:'INVALID_REQUEST'});
  body=parsed;
 }catch{return answer(origin,400,{error:'INVALID_REQUEST'});}
 const action=String(body.action||'');
 const input=(body.input||{}) as Record<string,unknown>;
 if(!input||typeof input!=='object'||Array.isArray(input))
  return answer(origin,400,{error:'INVALID_INPUT'});
 if(isWrite(action)&&!WRITE)
  return answer(origin,503,{error:'ORIGINAL_ADMIN_WRITES_DISABLED'});
 const db=createClient(URL,KEY,{auth:{persistSession:false,autoRefreshToken:false}});

 try{
  if(action==='stats'){
   const r=await db.from('users').select('chat_id',{count:'exact',head:true})
     .eq('is_active',true);
   if(r.error)throw r.error;
   return answer(origin,200,{active_users:r.count||0});
  }
  if(action==='spreads'){
   const r=await db.from('spread_settings').select('currency,spread_percent')
     .limit(100);
   if(r.error)throw r.error;
   const settings={...DEFAULT_SPREADS};
   for(const row of r.data||[]){
    if(CODES.has(row.currency)&&Number.isFinite(Number(row.spread_percent)))
     settings[row.currency]=Number(row.spread_percent);
   }
   return answer(origin,200,{spreads:settings});
  }
  if(action==='orders.pending'){
   const r=await db.from('usdt_orders')
     .select('id,order_type,asset,usdt_amount,total_afn,status,created_at')
     .eq('status','pending').order('created_at',{ascending:true}).limit(20);
   if(r.error)throw r.error;
   return answer(origin,200,{orders:r.data||[]});
  }
  if(action==='kyc.pending'){
   // Same ORIGINAL admin_bot.py KYC review, with short-lived private
   // document preview links. A browser cannot request another customer's
   // identity without BOTH verified Telegram HMAC and private admin ID.
   const r=await db.from('user_profiles').select(
    'chat_id,first_name,last_name,phone,kyc_status,id_document_path,selfie_path'
   ).eq('kyc_status','pending')
    .not('id_document_path','is',null).not('selfie_path','is',null)
    .order('chat_id',{ascending:false}).limit(20);
   if(r.error)throw r.error;
   const bucket=db.storage.from(Deno.env.get('USDT_KYC_DOCS_BUCKET')||'usdt-kyc-docs');
   const customers=await Promise.all((r.data||[]).map(async row=>{
     const [id,selfie]=await Promise.all([
       bucket.createSignedUrl(row.id_document_path,90),
       bucket.createSignedUrl(row.selfie_path,90),
     ]);
     // No persistent storage path or raw ID image is sent in the response.
     return {chat_id:row.chat_id,
       first_name:row.first_name,last_name:row.last_name,phone:row.phone,
       id_url:id.error?null:id.data?.signedUrl||null,
       selfie_url:selfie.error?null:selfie.data?.signedUrl||null};
   }));
   return answer(origin,200,{customers});
  }
  if(action==='kyc.review'){
   const chatId=Number(input.chat_id);
   const decision=String(input.decision||'');
   if(!Number.isSafeInteger(chatId)||chatId<=0||
      !['verify','reject'].includes(decision))
      return answer(origin,400,{error:'INVALID_KYC_REVIEW'});
   const status=decision==='verify'?'verified':'restricted';
   const rpc=await db.rpc('saraf_original_admin_review_kyc',{
     p_admin:actor.id,p_chat_id:chatId,p_status:status,
   });
   if(rpc.error){
     const known=new Set(['INVALID_KYC_REVIEW','KYC_PROFILE_NOT_FOUND',
      'KYC_NOT_PENDING','KYC_DOCUMENTS_MISSING']);
     const code=known.has(rpc.error.message)?rpc.error.message:'KYC_REVIEW_UNAVAILABLE';
     return answer(origin,code==='KYC_PROFILE_NOT_FOUND'?404:409,{error:code});
   }
   const result=rpc.data as {chat_id:number;status:string;duplicate:boolean};
   const notified=result?.duplicate?true:
     await notifyOriginalKycCustomer(result.chat_id,result.status);
   return answer(origin,200,{result:{
     chat_id:result.chat_id,status:result.status,
     duplicate:!!result.duplicate,customer_notified:notified,
   }});
  }
  if(action==='orders.confirmed'){
   const r=await db.from('usdt_orders').select(
     'id,order_type,asset,usdt_amount,total_afn,status,created_at'
    ).eq('status','confirmed').order('created_at',{ascending:true}).limit(20);
   if(r.error)throw r.error;
   return answer(origin,200,{orders:r.data||[]});
  }
  if(action==='order.reject'||action==='order.complete'){
   const orderId=Number(input.order_id);
   const complete=action==='order.complete';
   const details=complete?String(input.completion_tx_details||'').trim():'';
   if(!Number.isSafeInteger(orderId)||orderId<=0)
    return answer(origin,400,{error:'INVALID_ORDER_ID'});
   if(complete && (details.length<4||details.length>2000))
    return answer(origin,400,{error:'COMPLETION_PROOF_REQUIRED'});
   const r=await db.rpc('saraf_original_admin_finalize_order',{
     p_admin:actor.id,p_order_id:orderId,
     p_action:complete?'complete':'reject',
     p_details:complete?details:null,
   });
   if(r.error){
    const known=new Set(['INVALID_ADMIN_FINALIZE','ORDER_NOT_FOUND',
     'INVALID_ORDER_TRANSITION','COMPLETION_PROOF_REQUIRED',
     'BASIC_PROFILE_REQUIRED']);
    const code=known.has(r.error.message)?r.error.message:'ORDER_FINALIZE_UNAVAILABLE';
    return answer(origin,code==='ORDER_NOT_FOUND'?404:409,{error:code});
   }
   const row=r.data as {order_id:number;chat_id:number;asset:string;
     status:string;duplicate:boolean};
   const notified=row?.duplicate?true:await notifyOriginalFinalized(
     row.chat_id,row.order_id,row.asset,row.status,details);
   return answer(origin,200,{result:{
     order_id:row.order_id,status:row.status,duplicate:!!row.duplicate,
     customer_notified:notified,
   }});
  }
  if(action==='remittances.pending'){
   // Original remittance_admin.py private inbox: only actionable statuses.
   const r=await db.from('remittance_orders').select(
    'id,chat_id,status,asset,network,crypto_amount,payout_afn,beneficiary_full_name,beneficiary_phone,beneficiary_province,beneficiary_city,beneficiary_id_document_path,tx_hash,verification_status,chain_confirmations,created_at'
    ).in('status',['transfer_submitted','on_hold','payout_ready'])
     .order('created_at',{ascending:true}).limit(30);
   if(r.error)throw r.error;
   const bucket=db.storage.from(Deno.env.get('USDT_KYC_DOCS_BUCKET')||'usdt-kyc-docs');
   const orders=await Promise.all((r.data||[]).map(async row=>{
     const path=String(row.beneficiary_id_document_path||'');
     const own=path.startsWith('remittances/'+row.chat_id+'/')&&!path.includes('..');
     const signed=own?await bucket.createSignedUrl(path,90):null;
     // A pickup code stays in private DB and is sent only to the customer
     // when payout_ready; it never appears in the admin inbox response.
     const {beneficiary_id_document_path:discard,...safe}=row;
     return {...safe,beneficiary_id_url:signed&&!signed.error?
       signed.data?.signedUrl||null:null};
   }));
   return answer(origin,200,{orders});
  }
  if(action==='remittances.transition'){
   const id=Number(input.order_id);
   const transition=String(input.transition||'');
   const pickup=String(input.pickup_code||'').trim();
   if(!Number.isSafeInteger(id)||id<=0||
      !['ready','hold','cancel','pay'].includes(transition))
     return answer(origin,400,{error:'INVALID_REMITTANCE_ADMIN_INPUT'});
   if(transition==='pay'&&!/^[0-9]{6}$/.test(pickup))
     return answer(origin,400,{error:'INVALID_PICKUP_CODE'});
   const saved=await db.rpc('saraf_original_admin_remittance',{
     p_admin:actor.id,p_order_id:id,p_action:transition,
     p_pickup_code:transition==='pay'?pickup:null,
   });
   if(saved.error){
     const known=new Set(['INVALID_REMITTANCE_ADMIN_INPUT',
      'REMITTANCE_NOT_FOUND','INVALID_REMITTANCE_TRANSITION','INVALID_PICKUP_CODE']);
     const code=known.has(saved.error.message)?saved.error.message:'REMITTANCE_ADMIN_UNAVAILABLE';
     return answer(origin,code==='REMITTANCE_NOT_FOUND'?404:409,{error:code});
   }
   // NEVER return pickup_code to the admin web client or audit logs.
   // The original service sends it to the authenticated customer only.
   const result=saved.data as {
     order_id:number;chat_id:number;order_code:string;status:string;
     duplicate:boolean;beneficiary_full_name?:string;
     payout_afn?:number;pickup_code?:string;
   };
   const notified=result.duplicate?true:await notifyOriginalRemittanceCustomer(result);
   return answer(origin,200,{result:{
     order_id:result.order_id,order_code:result.order_code,
     status:result.status,duplicate:!!result.duplicate,
     customer_notified:notified,
   }});
  }
  if(action==='broadcast.create'){
   if(!BROADCAST)return answer(origin,503,{error:'ORIGINAL_BROADCAST_DISABLED'});
   const message=String(input.message||'').trim();
   const key=String(input.idempotency_key||'').trim();
   if(message.length<1||message.length>4096||
      !/^[A-Za-z0-9._:-]{16,120}$/.test(key))
    return answer(origin,400,{error:'INVALID_BROADCAST'});
   const r=await db.rpc('saraf_original_broadcast_create',{
    p_admin:actor.id,p_message:message,p_key:key,
   });
   if(r.error){
    return answer(origin,r.error.code==='P0001'?409:503,{
     error:r.error.code==='P0001'?r.error.message:'BROADCAST_QUEUE_UNAVAILABLE',
    });
   }
   return answer(origin,200,{result:r.data});
  }
  if(action==='broadcast.status'){
   if(!BROADCAST)return answer(origin,503,{error:'ORIGINAL_BROADCAST_DISABLED'});
   const id=Number(input.broadcast_id);
   if(!Number.isSafeInteger(id)||id<1)
    return answer(origin,400,{error:'INVALID_BROADCAST_ID'});
   const r=await db.from('saraf_original_broadcasts')
    .select('id,admin_chat_id,status,audience_size')
    .eq('id',id).eq('admin_chat_id',actor.id).maybeSingle();
   if(r.error||!r.data)return answer(origin,404,{error:'BROADCAST_NOT_FOUND'});
   const rows=await db.from('saraf_original_broadcast_deliveries')
    .select('state').eq('broadcast_id',id).limit(10000);
   if(rows.error)return answer(origin,503,{error:'BROADCAST_STATUS_UNAVAILABLE'});
   const counts:Record<string,number>={};
   for(const row of rows.data||[])
    counts[row.state]=(counts[row.state]||0)+1;
   return answer(origin,200,{result:{
    broadcast_id:r.data.id,status:r.data.status,audience_size:r.data.audience_size,
    deliveries:counts,
   }});
  }
  if(action==='spread.set'){
   const currency=String(input.currency||'').toLowerCase().trim();
   const amount=input.spread_percent;
   const pct=Number(amount);
   if(!CODES.has(currency)||typeof amount==='boolean'||amount==null||
    !Number.isFinite(pct)||pct<0||pct>20){
    return answer(origin,400,{error:'INVALID_SPREAD_INPUT'});
   }
   const r=await db.rpc('saraf_original_admin_set_spread',{
    p_admin:actor.id,p_currency:currency,p_percent:pct,
   });
   if(r.error)throw r.error;
   return answer(origin,200,{result:r.data});
  }
  if(action==='order.confirm'){
   const orderId=Number(input.order_id);
   if(!Number.isSafeInteger(orderId)||orderId<=0)
    return answer(origin,400,{error:'INVALID_ORDER_ID'});
   const r=await db.rpc('saraf_original_admin_confirm',{
    p_admin:actor.id,p_order_id:orderId,
   });
   if(r.error){
    const known=new Set(['INVALID_ADMIN_INPUT','ORDER_NOT_FOUND',
      'INVALID_ORDER_TRANSITION']);
    const code=known.has(r.error.message)?r.error.message:'CONFIRMATION_FAILED';
    return answer(origin,code==='ORDER_NOT_FOUND'?404:409,{error:code});
   }
   const row=r.data as {order_id:number;chat_id:number;asset:string;duplicate:boolean};
   const notified=row?.duplicate?true:
     await notifyOriginalCustomer(row.order_id,row.chat_id,row.asset);
   return answer(origin,200,{result:{
    order_id:row.order_id,status:'confirmed',
    duplicate:!!row.duplicate,customer_notified:notified,
   }});
  }
  return answer(origin,404,{error:'ADMIN_COMMAND_NOT_PORTED'});
 }catch(error){
  console.warn('Saraf existing admin command failed',
   String((error as {code?:string})?.code||'DATABASE_UNAVAILABLE'));
  return answer(origin,503,{error:'ADMIN_DATABASE_UNAVAILABLE'});
 }
});
