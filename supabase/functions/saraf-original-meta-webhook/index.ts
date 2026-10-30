// Railway-free transport for the ORIGINAL Instagram + Facebook webhooks.
// This does NOT invent or replace their existing AI/Meta business logic.
// Original Python handlers are run by the queue worker in GitHub Actions.
// OFF unless SARAF_ORIGINAL_META_WEBHOOKS_ENABLED=true.
import {createClient} from 'npm:@supabase/supabase-js@2.57.0';

const ENABLED=Deno.env.get('SARAF_ORIGINAL_META_WEBHOOKS_ENABLED')==='true';
const DB_URL=Deno.env.get('SUPABASE_URL')||'';
const DB_KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
import {constantTimeEqual,metaSignatureValid,contentHash} from './signature.mjs';
const json=(status:number,value:unknown)=>new Response(JSON.stringify(value),{
 status,headers:{'Content-Type':'application/json; charset=utf-8',
   'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'},
});
const platformConfig=(platform:string)=>{
 if(platform==='instagram')return {
  secret:Deno.env.get('INSTAGRAM_APP_SECRET')||'',
  verify:Deno.env.get('INSTAGRAM_WEBHOOK_VERIFY_TOKEN')||'',
  object:'instagram',
 };
 if(platform==='facebook')return {
  secret:Deno.env.get('FACEBOOK_APP_SECRET')||'',
  verify:Deno.env.get('FACEBOOK_WEBHOOK_VERIFY_TOKEN')||'',
  object:'page',
 };
 return null;
};
Deno.serve(async(request:Request)=>{
 const url=new URL(request.url);
 const platform=String(url.searchParams.get('platform')||'').toLowerCase();
 const config=platformConfig(platform);
 if(!config)return json(404,{error:'UNKNOWN_META_WEBHOOK'});
 if(request.method==='GET'){
   const mode=url.searchParams.get('hub.mode');
   const token=url.searchParams.get('hub.verify_token')||'';
   const challenge=url.searchParams.get('hub.challenge')||'';
   if(!ENABLED||!config.verify||mode!=='subscribe'||
     !constantTimeEqual(token,config.verify))return json(403,{error:'VERIFICATION_REJECTED'});
   if(challenge.length>512)return json(400,{error:'INVALID_CHALLENGE'});
   return new Response(challenge,{status:200,
    headers:{'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store'}});
 }
 if(request.method!=='POST')return json(405,{error:'METHOD_NOT_ALLOWED'});
 if(!ENABLED)return json(503,{error:'WEBHOOK_NOT_ENABLED'});
 const len=Number(request.headers.get('content-length')||'0');
 if(len>131072)return json(413,{error:'PAYLOAD_TOO_LARGE'});
 let raw:Uint8Array;
 try{
  raw=new Uint8Array(await request.arrayBuffer());
  if(raw.byteLength>131072)return json(413,{error:'PAYLOAD_TOO_LARGE'});
 }catch{return json(400,{error:'MALFORMED_BODY'});}
 if(!await metaSignatureValid(config.secret,raw,request.headers.get('x-hub-signature-256')))
   return json(403,{error:'INVALID_META_SIGNATURE'});
 let payload:Record<string,unknown>;
 try{
  payload=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
  if(!payload||typeof payload!=='object'||Array.isArray(payload)||
     payload.object!==config.object||!Array.isArray(payload.entry)){
   return json(400,{error:'INVALID_META_PAYLOAD'});
  }
 }catch{return json(400,{error:'INVALID_META_JSON'});}
 if(!DB_URL||!DB_KEY)return json(503,{error:'META_QUEUE_NOT_CONFIGURED'});
 const db=createClient(DB_URL,DB_KEY,{auth:{
   persistSession:false,autoRefreshToken:false,
 }});
 const fingerprint=await contentHash(raw);
 const result=await db.from('saraf_meta_delivery_queue')
  .upsert({platform,sha256_hex:fingerprint,payload},
    {onConflict:'platform,sha256_hex',ignoreDuplicates:true});
 if(result.error){
  console.warn('Saraf signed Meta webhook queue failed',result.error.code||'unknown');
  return json(503,{error:'META_QUEUE_UNAVAILABLE'});
 }
 // Enqueue is durable only. The separate original-Python worker
 // processes received comments/DMs with original duplicate detection.
 return json(200,{status:'received'});
});
