// Original Saraf order-card delivery, Railway-free and separate from financial RPCs.
// Client PNG is visual-only. Telegram captions are generated EXCLUSIVELY
// from the authenticated persisted order. Never approve a transfer from an image.
import {createClient} from 'npm:@supabase/supabase-js@2.57.0';
import {verifyTelegramInitData} from './telegram-auth.mjs';

const ORIGIN='https://app8533795882.tgcloud.ai';
const URL=Deno.env.get('SUPABASE_URL')||'';
const KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const TOKEN=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const ADMIN_TOKEN=Deno.env.get('SARAF_ADMIN_BOT_TOKEN')||'';
const ADMINS=(Deno.env.get('SARAF_ADMIN_CHAT_IDS')||'').split(',')
 .map(v=>v.trim()).filter(v=>/^[1-9][0-9]{0,15}$/.test(v));
const ENABLED=Deno.env.get('SARAF_ORIGINAL_TRANSACTIONS_ENABLED')==='true';
const MAX_BYTES=5*1024*1024;
const json=(origin:string,status:number,body:unknown)=>new Response(JSON.stringify(body),{
 status,headers:{'Content-Type':'application/json','Cache-Control':'no-store',
  'Vary':'Origin',...(origin===ORIGIN?{'Access-Control-Allow-Origin':ORIGIN}:{}),
  'Access-Control-Allow-Headers':'X-Telegram-Init-Data,Content-Type',
  'Access-Control-Allow-Methods':'POST,OPTIONS'},
});
function isPng(bytes:Uint8Array){
 if(bytes.byteLength<256||bytes.byteLength>MAX_BYTES)return false;
 const magic=[137,80,78,71,13,10,26,10];
 if(!magic.every((v,i)=>bytes[i]===v))return false;
 if(String.fromCharCode(...bytes.slice(12,16))!=='IHDR')return false;
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 return view.getUint32(16)===1320&&view.getUint32(20)===900&&
   bytes[bytes.length-12]===0&&bytes[bytes.length-11]===0&&
   bytes[bytes.length-10]===0&&bytes[bytes.length-9]===0&&
   bytes[bytes.length-8]===73&&bytes[bytes.length-7]===69&&
   bytes[bytes.length-6]===78&&bytes[bytes.length-5]===68;
}
const cash=(value:unknown,places=2)=>Number(value||0).toLocaleString('en-US',{
 minimumFractionDigits:places,maximumFractionDigits:places,
});
function captions(order:Record<string,unknown>,profile:Record<string,unknown>|null){
 const asset=order.asset==='USDC'?'USDC':'USDT';
 const code=asset+'-'+String(order.id).padStart(5,'0');
 const kind=order.order_type==='buy'?'خرید':'فروش';
 const base=['🪪 کارت دیجیتال سفارش صراف','کد: '+code,
   'نوع: '+kind+' '+asset,
   'مقدار: '+cash(order.usdt_amount)+' '+asset,
   'مبلغ: '+cash(order.total_afn)+' افغانی',
   'نرخ: '+cash(order.usd_rate)+' افغانی',
   'شبکه: '+String(order.network||'-').slice(0,70),
   'صرافی: '+String(order.exchange_name||'-').slice(0,80),
   'وضعیت: '+String(order.status||'pending'),
 ];
 const customer=[...base,'⏳ سفارش در انتظار بررسی تیم صراف است؛ این کارت تأیید پرداخت نیست.',
  '🆘 پشتیبانی: @SJDPLUS'].join('\n').slice(0,1000);
 const admin=[...base,'مشتری: '+[profile?.first_name,profile?.last_name]
   .filter(Boolean).join(' ').slice(0,95),
  'تماس: '+String(profile?.phone||order.phone||'-').slice(0,50),
  'روش پرداخت/دریافت: '+String(order.payment_method||order.receive_method||'-'),
  'ریسک: '+String(order.risk_level||'نامشخص').slice(0,25),
  '⚠️ اطلاعات معتبر فقط همین کپشن و پایگاه دادهٔ اصلی است؛ تصویر توسط Mini App تولید شده و به‌تنهایی سند تأیید پرداخت نیست.'
 ].join('\n').slice(0,1000);
 return {code,customer,admin};
}
type DeliverState='sent'|'failed'|'uncertain'|'sending';
async function deliver(db:ReturnType<typeof createClient>,orderId:number,
 chatId:number,recipient:'customer'|'admin',botToken:string,
 image:Blob,caption:string){
 const key={order_id:orderId,chat_id:chatId,recipient};
 const inserted=await db.from('saraf_original_order_card_deliveries')
  .insert({...key,state:'sending'}).select('state,attempt_count').single();
 let claimed=!inserted.error;
 if(inserted.error){
  if(inserted.error.code!=='23505')
   return {recipient,state:'uncertain' as DeliverState,error:'DELIVERY_OUTBOX_UNAVAILABLE'};
  const previous=await db.from('saraf_original_order_card_deliveries')
   .select('state,attempt_count').match(key).single();
  if(previous.error||!previous.data)
   return {recipient,state:'uncertain' as DeliverState,error:'DELIVERY_STATE_UNAVAILABLE'};
  if(previous.data.state==='sent')
   return {recipient,state:'sent' as DeliverState,duplicate:true};
  if(previous.data.state==='failed'&&previous.data.attempt_count<5){
   const retry=await db.from('saraf_original_order_card_deliveries')
    .update({state:'sending',updated_at:new Date().toISOString(),
     attempt_count:previous.data.attempt_count+1})
    .match({...key,state:'failed',attempt_count:previous.data.attempt_count})
    .select('state').maybeSingle();
   claimed=!!retry.data&&!retry.error;
  }
  if(!claimed)
   return {recipient,state:previous.data.state as DeliverState,
    manual_review:previous.data.state==='uncertain'||previous.data.state==='sending'};
 }
 // Claim is durable before network call. Unknown network outcomes are never
 // retried automatically; otherwise a customer/admin could receive duplicates.
 let state:DeliverState='uncertain',messageId:number|null=null;
 try{
  const form=new FormData();
  form.append('chat_id',String(chatId));
  form.append('caption',caption);
  form.append('photo',image,'Saraf-'+orderId+'.png');
  const response=await fetch('https://api.telegram.org/bot'+botToken+'/sendPhoto',{
   method:'POST',body:form,signal:AbortSignal.timeout(10000),
  });
  const answer=await response.json().catch(()=>null);
  if(response.ok&&answer?.ok&&Number.isSafeInteger(answer.result?.message_id)){
   state='sent';messageId=answer.result.message_id;
  }else if(response.status>=400&&response.status<500&&
    response.status!==408&&response.status!==429){
   state='failed';
  }
 }catch{/* Unknown delivery outcome: never blindly repeat. */}
 const saved=await db.from('saraf_original_order_card_deliveries')
  .update({state,telegram_message_id:messageId,
   sent_at:state==='sent'?new Date().toISOString():null,
   updated_at:new Date().toISOString()}).match({...key,state:'sending'});
 if(saved.error)return {recipient,state:'uncertain' as DeliverState,
  error:'DELIVERY_STATUS_UNAVAILABLE'};
 return {recipient,state};
}

Deno.serve(async req=>{
 const origin=req.headers.get('origin')||'';
 if(req.method==='OPTIONS')return origin===ORIGIN?
   new Response(null,{status:204,headers:{
    'Access-Control-Allow-Origin':ORIGIN,
    'Access-Control-Allow-Headers':'X-Telegram-Init-Data,Content-Type',
    'Access-Control-Allow-Methods':'POST,OPTIONS','Vary':'Origin',
   }}):json('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(req.method!=='POST')return json(origin,405,{error:'METHOD_NOT_ALLOWED'});
 if(origin!==ORIGIN)return json('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(!URL||!KEY||!TOKEN||!ADMIN_TOKEN||!ADMINS.length||!ENABLED)
  return json(origin,503,{error:'ORIGINAL_CARD_DELIVERY_NOT_CONFIGURED'});
 const user=await verifyTelegramInitData(
  req.headers.get('x-telegram-init-data')||'',TOKEN);
 if(!user)return json(origin,401,{error:'INVALID_TELEGRAM_AUTH'});
 const type=req.headers.get('content-type')||'';
 if(!type.toLowerCase().startsWith('multipart/form-data')||
   Number(req.headers.get('content-length')||0)>MAX_BYTES+50000)
  return json(origin,400,{error:'INVALID_CARD_REQUEST'});
 try{
  const form=await req.formData();
  const id=Number(form.get('order_id'));
  if(!Number.isSafeInteger(id)||id<=0)
   return json(origin,400,{error:'INVALID_ORDER_ID'});
  const file=form.get('card');
  if(!(file instanceof File)||file.type!=='image/png'||file.size>MAX_BYTES)
   return json(origin,400,{error:'INVALID_CARD_FILE'});
  const data=new Uint8Array(await file.arrayBuffer());
  if(!isPng(data))return json(origin,400,{error:'INVALID_CARD_PNG'});
  const db=createClient(URL,KEY,{auth:{persistSession:false,autoRefreshToken:false}});
  // Never use browser-supplied chat ID/amount/status. Query the canonical
  // financial order and require its Telegram HMAC identity owner.
  const order=await db.from('usdt_orders').select(
   'id,chat_id,asset,order_type,status,created_at,usdt_amount,total_afn,usd_rate,network,exchange_name,phone,payment_method,receive_method,risk_level,card_image_path'
  ).eq('id',id).eq('chat_id',user.id).maybeSingle();
  if(order.error)return json(origin,503,{error:'ORDER_LOOKUP_FAILED'});
  if(!order.data)return json(origin,404,{error:'ORDER_NOT_FOUND'});
  const row=order.data;
  if(!['pending','confirmed','completed'].includes(row.status)||
     Date.now()-Date.parse(row.created_at)>48*3600*1000)
   return json(origin,409,{error:'ORDER_CARD_WINDOW_CLOSED'});
  const path='orders/'+id+'.png',bucket=db.storage.from('usdt-cards');
  if(!row.card_image_path){
   const uploaded=await bucket.upload(path,data,{
    contentType:'image/png',upsert:false,cacheControl:'0',
   });
   // If a previous request already uploaded, continue only with exact
   // deterministic order path; never replace a stored card.
   if(uploaded.error){
    const existing=await bucket.download(path);
    if(existing.error)return json(origin,503,{error:'CARD_STORAGE_UNAVAILABLE'});
   }
   const updated=await db.from('usdt_orders')
    .update({card_image_path:path}).eq('id',id).eq('chat_id',user.id)
    .is('card_image_path',null).select('id').maybeSingle();
   if(updated.error)return json(origin,503,{error:'CARD_LINK_UNAVAILABLE'});
  }else if(row.card_image_path!==path){
   // Legacy Railway card: do not overwrite an earlier persisted image.
   return json(origin,409,{error:'ORIGINAL_CARD_ALREADY_EXISTS'});
  }
  // Always resend the STORED original image, not an uncommitted browser file.
  const stored=await bucket.download(path);
  if(stored.error||!stored.data)
   return json(origin,503,{error:'CARD_DOWNLOAD_UNAVAILABLE'});
  const png=stored.data;
  const profile=await db.from('user_profiles')
   .select('first_name,last_name,phone').eq('chat_id',user.id).maybeSingle();
  if(profile.error)return json(origin,503,{error:'PROFILE_UNAVAILABLE'});
  const caption=captions(row,profile.data);
  const customer=await deliver(db,id,user.id,'customer',TOKEN,png,caption.customer);
  const admins=await Promise.all(ADMINS.map(chat=>deliver(
   db,id,Number(chat),'admin',ADMIN_TOKEN,png,caption.admin)));
  return json(origin,200,{
   order_code:caption.code,card_path_stored:true,
   customer:customer.state,
   admins:admins.map((a,i)=>({recipient_index:i+1,state:a.state})),
   requires_manual_review:[customer,...admins].some(x=>
    x.state==='uncertain'||x.state==='sending'),
  });
 }catch{
  return json(origin,503,{error:'ORIGINAL_CARD_DELIVERY_UNAVAILABLE'});
 }
});
