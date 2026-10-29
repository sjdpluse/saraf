// Original Saraf operator-only review API.
// This is a review/queue workflow, NOT a bank transfer, wallet withdrawal,
// cash payout, or transaction settlement. OFF unless separately authorized.
import { createClient } from 'npm:@supabase/supabase-js@2.57.0';
import { verifyTelegramInitData } from '../saraf-telegram-bridge/telegram-auth.mjs';

const TRUSTED_ORIGIN='https://app8533795882.tgcloud.ai';
const BOT_TOKEN=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const DB_URL=Deno.env.get('SUPABASE_URL')||'';
const DB_KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const ENABLED=Deno.env.get('SARAF_OPERATOR_REVIEW_ENABLED')==='true';
const rawOperators=(Deno.env.get('SARAF_OPERATOR_IDS')||'').split(',');
const operatorIds=new Set(rawOperators.map(s=>s.trim())
 .filter(s=>/^[1-9][0-9]{0,15}$/.test(s))
 .map(Number).filter(Number.isSafeInteger));
const outputHeaders=(origin:string)=>({
 'content-type':'application/json; charset=utf-8','cache-control':'no-store',
 'vary':'Origin',
 ...(origin===TRUSTED_ORIGIN?{'access-control-allow-origin':TRUSTED_ORIGIN}:{}),
 'access-control-allow-headers':'content-type,x-telegram-init-data',
 'access-control-allow-methods':'POST,OPTIONS',
});
const respond=(origin:string,status:number,data:unknown)=>
 new Response(JSON.stringify(data),{status,headers:outputHeaders(origin)});
Deno.serve(async(req:Request)=>{
 const origin=req.headers.get('origin')||'';
 if(req.method==='OPTIONS'){
   if(origin!==TRUSTED_ORIGIN)return respond('',403,{error:'ORIGIN_NOT_ALLOWED'});
   return new Response(null,{status:204,headers:outputHeaders(origin)});
 }
 if(req.method!=='POST')return respond(origin,405,{error:'METHOD_NOT_ALLOWED'});
 if(origin && origin!==TRUSTED_ORIGIN)return respond('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(!BOT_TOKEN||!DB_URL||!DB_KEY)return respond(origin,503,{error:'NOT_CONFIGURED'});
 const identity=await verifyTelegramInitData(
   req.headers.get('x-telegram-init-data')||'',BOT_TOKEN);
 if(!identity)return respond(origin,401,{error:'INVALID_TELEGRAM_AUTH'});
 // Two distinct authorized operators are required before any queue workflow
 // can operate. The DB independently checks enabled operator enrollments.
 if(operatorIds.size<2||!operatorIds.has(identity.id))
   return respond(origin,403,{error:'OPERATOR_NOT_AUTHORIZED'});
 if(!ENABLED)return respond(origin,503,{error:'OPERATOR_REVIEW_DISABLED'});
 let body:Record<string,unknown>;
 try{
   const text=await req.text();
   if(text.length>1500)throw Error('INVALID_BODY');
   body=JSON.parse(text);
   if(!body||typeof body!=='object'||Array.isArray(body))throw Error('INVALID_BODY');
 }catch{return respond(origin,400,{error:'INVALID_REQUEST'});}
 const action=body.action;
 const input=body.input as Record<string,unknown>|undefined;
 const id=Number(input?.remittance_id);
 if(!Number.isSafeInteger(id)||id<=0)
   return respond(origin,400,{error:'INVALID_REMITTANCE_ID'});
 const rpc=action==='payout.approve'?'saraf_approve_verified_payout':
   action==='payout.queue'?'saraf_prepare_payout_after_dual_approval':null;
 if(!rpc)return respond(origin,403,{error:'ACTION_NOT_AVAILABLE'});
 const db=createClient(DB_URL,DB_KEY,{
   auth:{persistSession:false,autoRefreshToken:false},
 });
 try{
   const limit=await db.rpc('saraf_limit_finance_api',{
     p_chat_id:identity.id,p_action:String(action),
   });
   if(limit.error){
     if(limit.error.code==='P0001' &&
        limit.error.message==='FINANCIAL_RATE_LIMIT_EXCEEDED')
       return respond(origin,429,{error:'FINANCIAL_RATE_LIMIT_EXCEEDED'});
     return respond(origin,503,{error:'DATABASE_UNAVAILABLE'});
   }
   const {data,error}=await db.rpc(rpc,{
     p_remittance_id:id,p_operator_id:identity.id,
   });
   if(error){
     const allowed=new Set([
       'INVALID_APPROVAL_INPUT','REMITTANCE_NOT_FOUND','REMITTANCE_NOT_READY',
       'INDEPENDENT_CHAIN_PROOF_REQUIRED','OPERATOR_NOT_AUTHORIZED',
       'SELF_APPROVAL_FORBIDDEN','TWO_INDEPENDENT_APPROVALS_REQUIRED',
       'PAYOUT_COMPLETION_INTEGRATION_REQUIRED',
     ]);
     if(error.code==='P0001' && allowed.has(error.message))
       return respond(origin,409,{error:error.message});
     console.warn('Saraf operator RPC denied',error.code||'db_error');
     return respond(origin,503,{error:'DATABASE_UNAVAILABLE'});
   }
   return respond(origin,200,{data});
 }catch{
   return respond(origin,503,{error:'DATABASE_UNAVAILABLE'});
 }
});
