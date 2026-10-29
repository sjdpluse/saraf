// Original main:handlers/start.py /start and /stop, with unchanged canonical
// Supabase "users" table. The Telegram native runtime cannot safely prove
// its message.from ID to a separate Edge API: signed Mini App initData does.
// No shadow users and no ability to deactivate someone else's account.
import {createClient} from 'npm:@supabase/supabase-js@2.57.0';
import {verifyTelegramInitData} from './telegram-auth.mjs';
const ORIGIN='https://app8533795882.tgcloud.ai';
const TOKEN=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const URL=Deno.env.get('SUPABASE_URL')||'';
const ENABLED=Deno.env.get('SARAF_ORIGINAL_USER_PREFERENCES_ENABLED')==='true';
const response=(origin:string,status:number,body:unknown)=>new Response(
 JSON.stringify(body),{status,headers:{
  'Content-Type':'application/json','Cache-Control':'no-store',
  'Vary':'Origin',...(origin===ORIGIN?{
   'Access-Control-Allow-Origin':ORIGIN}:{}),
  'Access-Control-Allow-Headers':'Content-Type,X-Telegram-Init-Data',
  'Access-Control-Allow-Methods':'POST,OPTIONS',
 }});
Deno.serve(async req=>{
 const origin=req.headers.get('origin')||'';
 if(req.method==='OPTIONS')return origin===ORIGIN
  ?new Response(null,{status:204,headers:{
    'Access-Control-Allow-Origin':ORIGIN,'Access-Control-Allow-Headers':
      'Content-Type,X-Telegram-Init-Data','Access-Control-Allow-Methods':'POST,OPTIONS',
   }})
  :response('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(req.method!=='POST')return response(origin,405,{error:'METHOD_NOT_ALLOWED'});
 if(origin!==ORIGIN)return response('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(!TOKEN||!KEY||!URL)return response(origin,503,{error:'NOT_CONFIGURED'});
 const user=await verifyTelegramInitData(
  req.headers.get('x-telegram-init-data')||'',TOKEN);
 if(!user)return response(origin,401,{error:'INVALID_TELEGRAM_AUTH'});
 if(!ENABLED)return response(origin,503,{error:'PREFERENCES_NOT_MIGRATED'});
 let data:Record<string,unknown>;
 try{
  const raw=await req.text();
  if(raw.length>2000)return response(origin,413,{error:'TOO_LARGE'});
  const json=JSON.parse(raw);
  if(!json||typeof json!=='object'||Array.isArray(json))
    return response(origin,400,{error:'INVALID_REQUEST'});
  data=json;
 }catch{return response(origin,400,{error:'INVALID_REQUEST'});}
 const action=String(data.action||'');
 if(!['read','activate','deactivate'].includes(action))
  return response(origin,400,{error:'UNKNOWN_ACTION'});
 const db=createClient(URL,KEY,{auth:{autoRefreshToken:false,persistSession:false}});
 try{
  if(action==='read'){
   const r=await db.from('users').select('is_active')
    .eq('chat_id',user.id).maybeSingle();
   if(r.error)throw r.error;
   return response(origin,200,{is_active:r.data?.is_active===true,
    registered:!!r.data});
  }
  if(action==='activate'){
   const username=typeof user.username==='string'?
    user.username.slice(0,80):null;
   const name=[user.first_name,user.last_name]
    .filter((part:unknown)=>typeof part==='string'&&part.length)
    .join(' ').slice(0,160);
   // Original upsert_user intentionally refreshes last_seen_at.
   const r=await db.from('users').upsert({
    chat_id:user.id,username,full_name:name||null,
    is_active:true,last_seen_at:new Date().toISOString(),
   },{onConflict:'chat_id'}).select('chat_id').single();
   if(r.error)throw r.error;
   return response(origin,200,{is_active:true,registered:true});
  }
  // Original /stop does not delete order or KYC history. It only opts out.
  const r=await db.from('users').update({is_active:false})
    .eq('chat_id',user.id).select('chat_id').maybeSingle();
  if(r.error)throw r.error;
  return response(origin,200,{is_active:false,registered:!!r.data});
 }catch{
  return response(origin,503,{error:'DATABASE_UNAVAILABLE'});
 }
});
