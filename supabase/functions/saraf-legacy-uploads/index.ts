// Exact existing Saraf multipart upload contracts, NOT a new product:
// POST /api/usdt/upload-receipt => {url: signed private 24h URL}
// POST /api/remittances/upload-beneficiary-id => {file_id: owner-only path}
// Original source: main:api.py and services/remittance_api_router.py.
// Staged OFF until Supabase original-bot integration tests pass.
import { createClient } from 'npm:@supabase/supabase-js@2.57.0';
import { verifyTelegramInitData } from '../saraf-telegram-bridge/telegram-auth.mjs';
const BOT=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const ENABLED=Deno.env.get('SARAF_ORIGINAL_UPLOADS_ENABLED')==='true';
const DB=Deno.env.get('SUPABASE_URL')||'https://cvernmhpnsgdtegvblyc.supabase.co';
const ORIGIN='https://app8533795882.tgcloud.ai';
const allowed={receipt:{bucket:'usdt-receipts',limit:8*1024*1024},
  beneficiary:{bucket:'usdt-kyc-docs',limit:10*1024*1024}};
function headers(origin:string){
 return {'Content-Type':'application/json','Cache-Control':'no-store','Vary':'Origin',
  ...(origin===ORIGIN?{'Access-Control-Allow-Origin':ORIGIN}:{}),
  'Access-Control-Allow-Methods':'POST,OPTIONS',
  'Access-Control-Allow-Headers':'Content-Type,X-Telegram-Init-Data'};
}
const result=(origin:string,status:number,body:unknown)=>
 new Response(JSON.stringify(body),{status,headers:headers(origin)});
function imageExtension(file:File,data:Uint8Array){
 const jpeg=data[0]===255&&data[1]===216&&data[2]===255;
 const png=data.length>=8&&[137,80,78,71,13,10,26,10].every((n,i)=>data[i]===n);
 const webp=data.length>=12&&[82,73,70,70].every((n,i)=>data[i]===n)
   &&[87,69,66,80].every((n,i)=>data[i+8]===n);
 if(jpeg&&file.type==='image/jpeg')return 'jpg';
 if(png&&file.type==='image/png')return 'png';
 if(webp&&file.type==='image/webp')return 'webp';
 return null;
}
Deno.serve(async(req:Request)=>{
 const origin=req.headers.get('origin')||'';
 if(req.method==='OPTIONS')return origin===ORIGIN
   ?new Response(null,{status:204,headers:headers(origin)})
   :result('',403,{error:'ORIGIN_DENIED'});
 if(req.method!=='POST')return result(origin,405,{error:'METHOD_NOT_ALLOWED'});
 if(origin&&origin!==ORIGIN)return result('',403,{error:'ORIGIN_DENIED'});
 if(!KEY||!BOT)return result(origin,503,{error:'SERVICE_NOT_CONFIGURED'});
 const user=await verifyTelegramInitData(req.headers.get('x-telegram-init-data')||'',BOT);
 if(!user)return result(origin,401,{error:'INVALID_TELEGRAM_AUTH'});
 if(!ENABLED)return result(origin,503,{error:'UPLOAD_NOT_MIGRATED'});
 const length=Number(req.headers.get('content-length')||0);
 if(length>11*1024*1024)return result(origin,413,{error:'FILE_TOO_LARGE'});
 try{
  const form=await req.formData();
  const kind=String(form.get('kind')||'');
  const cfg=allowed[kind as keyof typeof allowed];
  if(!cfg)return result(origin,400,{error:'INVALID_UPLOAD_KIND'});
  const file=form.get('file');
  if(!(file instanceof File)||file.size<12||file.size>cfg.limit)
    return result(origin,400,{error:'INVALID_UPLOAD_FILE'});
  const content=new Uint8Array(await file.arrayBuffer());
  const ext=imageExtension(file,content);
  if(!ext)return result(origin,400,{error:'INVALID_IMAGE_TYPE'});
  const suffix=crypto.randomUUID().replaceAll('-','')+'.'+ext;
  const name=kind==='receipt'?user.id+'_'+suffix:
    'remittances/'+user.id+'/'+suffix;
  const db=createClient(DB,KEY,{auth:{autoRefreshToken:false,persistSession:false}});
  const stored=await db.storage.from(cfg.bucket).upload(name,content,{
    contentType:file.type,upsert:false,cacheControl:'0',
  });
  if(stored.error)return result(origin,503,{error:'UPLOAD_UNAVAILABLE'});
  if(kind==='beneficiary')return result(origin,200,{data:{file_id:name}});
  const signed=await db.storage.from(cfg.bucket).createSignedUrl(name,86400);
  if(signed.error||!signed.data?.signedUrl){
   await db.storage.from(cfg.bucket).remove([name]);
   return result(origin,503,{error:'RECEIPT_SIGNING_FAILED'});
  }
  return result(origin,200,{data:{url:signed.data.signedUrl}});
 }catch{
  return result(origin,503,{error:'UPLOAD_UNAVAILABLE'});
 }
});
