// Faithful port of existing main:api.py POST /api/usdt/kyc and
// main:services/kyc_service.py -> private storage and existing user_profiles.
// NOT a new KYC scheme. Never deploy until original admin review notification
// path has been confirmed. No cloud-Telegram SQLite or Railway.
import { createClient } from 'npm:@supabase/supabase-js@2.57.0';
import { verifyTelegramInitData } from './telegram-auth.mjs';

const PROJECT='cvernmhpnsgdtegvblyc';
const TRUSTED_ORIGIN='https://app8533795882.tgcloud.ai';
const PRIVATE_BUCKET='usdt-kyc-docs';
const FILE_LIMIT=8*1024*1024;
const REQUEST_LIMIT=18*1024*1024;
const TELEGRAM_TOKEN=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const SERVICE_KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const ENABLED=Deno.env.get('SARAF_ORIGINAL_KYC_ENABLED')==='true';
const ADMIN_IDS=(Deno.env.get('SARAF_KYC_ADMIN_IDS')||
  Deno.env.get('SARAF_ADMIN_CHAT_IDS')||'').split(',')
  .map(s=>s.trim()).filter(s=>/^[1-9][0-9]{0,15}$/.test(s));
const edgeURL=Deno.env.get('SUPABASE_URL')||'https://'+PROJECT+'.supabase.co';
const headers=(origin:string)=>({
  'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',
  'Vary':'Origin',
  ...(origin===TRUSTED_ORIGIN?{'Access-Control-Allow-Origin':TRUSTED_ORIGIN}:{}),
  'Access-Control-Allow-Headers':'Content-Type,X-Telegram-Init-Data',
  'Access-Control-Allow-Methods':'POST,OPTIONS',
});
function answer(origin:string,status:number,body:unknown){
 return new Response(JSON.stringify(body),{status,headers:headers(origin)});
}
const bad=(name:string,status=400):never=>{
 throw Object.assign(new Error(name),{status});
};
function imageKind(file:File,bytes:Uint8Array){
  if(file.size<12||file.size>FILE_LIMIT)bad('INVALID_IMAGE_SIZE');
  const jpg=bytes.length>=3&&bytes[0]===255&&bytes[1]===216&&bytes[2]===255;
  const png=bytes.length>=8&&bytes[0]===137&&bytes[1]===80&&
    bytes[2]===78&&bytes[3]===71&&bytes[4]===13&&bytes[5]===10&&
    bytes[6]===26&&bytes[7]===10;
  const webp=bytes.length>=12&&[82,73,70,70].every((b,i)=>bytes[i]===b)&&
    [87,69,66,80].every((b,i)=>bytes[8+i]===b);
  if(jpg&&file.type==='image/jpeg')return {extension:'jpg',mime:file.type};
  if(png&&file.type==='image/png')return {extension:'png',mime:file.type};
  if(webp&&file.type==='image/webp')return {extension:'webp',mime:file.type};
  return bad('INVALID_IMAGE_TYPE');
}
async function adminNotification(userId:number,profile:Record<string,unknown>){
  // The old Python service sends a separate review request to admin IDs.
  // The original bot token is used only server-side and never exposed.
  if(!ADMIN_IDS.length)return;
  const name=[profile.first_name,profile.last_name].filter(Boolean).join(' ');
  const message='🪪 درخواست بررسی KYC جدید در صراف\n'+
   'کاربر: '+String(userId)+'\n'+
   'نام: '+String(name).slice(0,140)+'\n'+
   'مدارک در باکت خصوصی Supabase ذخیره شدند؛ در پنل مدیریت بررسی کنید.';
  await Promise.allSettled(ADMIN_IDS.map(async id=>{
    // Never send private image bytes or temporary public URLs in a plain text message.
    const rsp=await fetch('https://api.telegram.org/bot'+TELEGRAM_TOKEN+'/sendMessage',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({chat_id:Number(id),text:message}),
      signal:AbortSignal.timeout(5000),
    });
    if(!rsp.ok)console.error('Saraf KYC review notification failed',{status:rsp.status});
  }));
}
Deno.serve(async(request:Request)=>{
  const origin=request.headers.get('origin')||'';
  if(request.method==='OPTIONS')return origin===TRUSTED_ORIGIN
    ?new Response(null,{status:204,headers:headers(origin)})
    :answer('',403,{error:'ORIGIN_NOT_ALLOWED'});
  if(request.method!=='POST')return answer(origin,405,{error:'METHOD_NOT_ALLOWED'});
  if(origin&&origin!==TRUSTED_ORIGIN)return answer('',403,{error:'ORIGIN_NOT_ALLOWED'});
  if(!TELEGRAM_TOKEN||!SERVICE_KEY)return answer(origin,503,{error:'SERVICE_NOT_CONFIGURED'});
  const user=await verifyTelegramInitData(
    request.headers.get('x-telegram-init-data')||'',TELEGRAM_TOKEN);
  if(!user)return answer(origin,401,{error:'INVALID_TELEGRAM_AUTH'});
  if(!ENABLED)return answer(origin,503,{error:'KYC_NOT_MIGRATED'});
  // Do not accept irreversible identity documents when no original admin
  // can review them; this is the migration's required human approval step.
  if(!ADMIN_IDS.length)
    return answer(origin,503,{error:'KYC_ADMIN_REVIEW_NOT_CONFIGURED'});
  if(Number(request.headers.get('content-length')||0)>REQUEST_LIMIT)
    return answer(origin,413,{error:'PAYLOAD_TOO_LARGE'});
  try {
    const form=await request.formData();
    const document=form.get('id_document');
    const selfie=form.get('selfie');
    if(!(document instanceof File)||!(selfie instanceof File))
      throw new Error('BOTH_FILES_REQUIRED');
    if(document.size+selfie.size>2*FILE_LIMIT)bad('PAYLOAD_TOO_LARGE',413);
    const payment=String(form.get('payment_info')||'').trim();
    if(payment.length>2000||(payment.length>0&&payment.length<4))
      bad('INVALID_PAYMENT_INFO');
    const idBytes=new Uint8Array(await document.arrayBuffer());
    const selfBytes=new Uint8Array(await selfie.arrayBuffer());
    const idType=imageKind(document,idBytes);
    const selfType=imageKind(selfie,selfBytes);
    const db=createClient(edgeURL,SERVICE_KEY,{
      auth:{autoRefreshToken:false,persistSession:false},
    });
    const profileRes=await db.from('user_profiles').select(
      'first_name,last_name,phone,kyc_status'
    ).eq('chat_id',user.id).maybeSingle();
    if(profileRes.error)bad('DATABASE_UNAVAILABLE',503);
    const p=profileRes.data;
    if(!p||!p.first_name||!p.last_name||!p.phone)
      throw Object.assign(new Error('BASIC_PROFILE_REQUIRED'),{status:403});
    if(p.kyc_status==='restricted')
      bad('ACCOUNT_RESTRICTED',403);
    const random=crypto.randomUUID().replaceAll('-','');
    // Unique paths avoid overwriting previous verified ID documents.
    const idPath=user.id+'_id_document_'+random+'.'+idType.extension;
    const selfiePath=user.id+'_selfie_'+random+'.'+selfType.extension;
    const storage=db.storage.from(PRIVATE_BUCKET);
    const first=await storage.upload(idPath,idBytes,{
      contentType:idType.mime,upsert:false,
    });
    if(first.error)bad('PRIVATE_UPLOAD_FAILED',503);
    const second=await storage.upload(selfiePath,selfBytes,{
      contentType:selfType.mime,upsert:false,
    });
    if(second.error){
      await storage.remove([idPath]);
      bad('PRIVATE_UPLOAD_FAILED',503);
    }
    // The original service updates the existing profile, never creates a
    // partial identity. The existing admin approval workflow remains required.
    const profileUpdate=await db.from('user_profiles').update({
      id_document_path:idPath,selfie_path:selfiePath,kyc_status:'pending',
      ...(payment?{payment_info:payment}:{}),
    }).eq('chat_id',user.id).eq('kyc_status',p.kyc_status).select('chat_id');
    if(profileUpdate.error||profileUpdate.data?.length!==1){
      await storage.remove([idPath,selfiePath]);
      bad('PROFILE_UPDATE_FAILED',503);
    }
    await adminNotification(user.id,p as Record<string,unknown>);
    return answer(origin,200,{data:{ok:true}});
  }catch(error){
    const e=error as {message?:string;status?:number};
    const allowed=new Set(['INVALID_IMAGE_TYPE','INVALID_IMAGE_SIZE',
      'BOTH_FILES_REQUIRED','PAYLOAD_TOO_LARGE','INVALID_PAYMENT_INFO',
      'BASIC_PROFILE_REQUIRED','ACCOUNT_RESTRICTED','PRIVATE_UPLOAD_FAILED',
      'DATABASE_UNAVAILABLE','PROFILE_UPDATE_FAILED']);
    const code=allowed.has(e?.message||'')?e.message:'INVALID_UPLOAD';
    return answer(origin,e?.status||500,{error:code});
  }
});
