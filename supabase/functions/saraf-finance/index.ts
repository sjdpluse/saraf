// Staged canonical Saraf financial API. Do NOT deploy before applying and
// verifying supabase/sql/saraf_atomic_finance_staged.sql and operator secrets.
// Original @sarafiaf_bot only. All real writes OFF by default.
// This function never sends coins, confirms bank payments, or executes payouts.
import { createClient } from 'npm:@supabase/supabase-js@2.57.0';
import { verifyTelegramInitData } from '../saraf-telegram-bridge/telegram-auth.mjs';

const PROJECT='cvernmhpnsgdtegvblyc';
const ORIGIN='https://app8533795882.tgcloud.ai';
const API_URL='https://'+PROJECT+'.supabase.co';
const BOT_TOKEN=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN') || '';
const SERVICE_KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || '';
const ENABLED=Deno.env.get('SARAF_FINANCIAL_WRITES_ENABLED')==='true';
const ADMIN_IDS=new Set((Deno.env.get('SARAF_OPERATOR_IDS')||'')
  .split(',').filter(v=>/^\d{1,16}$/.test(v.trim())).map(v=>Number(v.trim())));
const MAX_BODY=3500;

const headers=(origin:string)=>({
  'Content-Type':'application/json; charset=utf-8',
  'Cache-Control':'no-store',
  'Vary':'Origin',
  ...(origin===ORIGIN ? {'Access-Control-Allow-Origin':ORIGIN} : {}),
  'Access-Control-Allow-Methods':'POST, OPTIONS',
  'Access-Control-Allow-Headers':'Content-Type, X-Telegram-Init-Data',
});
function response(origin:string,status:number,payload:unknown) {
  return new Response(JSON.stringify(payload),{status,headers:headers(origin)});
}
function bad(code:string, status=400):never {
  throw Object.assign(new Error(code),{status});
}
type Body={action:string;input?:Record<string,unknown>};
function parseInput(input:unknown) {
  if (!input || typeof input!=='object' || Array.isArray(input))bad('INVALID_INPUT');
  return input as Record<string,unknown>;
}
function string(input:unknown,minimum:number,maximum:number) {
  if(typeof input!=='string' || input.trim().length<minimum ||
     input.trim().length>maximum)bad('INVALID_INPUT');
  return (input as string).trim();
}
function amount(input:unknown) {
  const a=String(input);
  // Stablecoins limited to TWO decimal places for original Saraf's economics.
  if(!/^(?:0|[1-9][0-9]{0,3})(?:\.[0-9]{1,2})?$/.test(a))bad('INVALID_AMOUNT');
  const cents=Number(a)*100;
  if(!Number.isSafeInteger(Math.round(cents)) || cents<1000 || cents>100000)
    bad('AMOUNT_OUT_OF_RANGE');
  return a;
}
function asset(input:unknown) {
  if(input!=='USDT' && input!=='USDC')bad('INVALID_ASSET');
  return input;
}
function action(input:unknown) {
  if(input!=='buy' && input!=='sell')bad('INVALID_ACTION');
  return input;
}
function id(input:unknown) {
  const n=Number(input);
  if(!Number.isSafeInteger(n)||n<=0)bad('INVALID_ID');
  return n;
}
function idem(input:unknown):string {
  const value=string(input,16,128);
  if(!/^[A-Za-z0-9_.:-]{16,128}$/.test(value))bad('IDEMPOTENCY_KEY_INVALID');
  return value;
}
function client() {
  return createClient(API_URL,SERVICE_KEY,{
    auth:{autoRefreshToken:false,persistSession:false}
  });
}
function rpcFailure(error: {message?:string;code?:string}|null) {
  if(!error)return;
  // Never leak SQL internals, historic finance PII, or PostgREST metadata.
  const allow=new Set([
    'INVALID_QUOTE_INPUT','FRESH_VERIFIED_RATE_REQUIRED',
    'INVALID_ORDER_INPUT','INVALID_ORDER_DETAILS','UNVERIFIED_DEPOSIT_WALLET',
    'IDEMPOTENCY_CONFLICT','QUOTE_INVALID_OR_CONSUMED',
    'PROFILE_REQUIRED_OR_RESTRICTED','VERIFIED_IDENTITY_REQUIRED',
    'DAILY_LIMIT_EXCEEDED','QUOTE_CONCURRENTLY_CONSUMED',
  ]);
  if(error.code==='P0001' && allow.has(error.message||''))
    bad(error.message||'FINANCE_REJECTED',409);
  console.error('Finance database request rejected',error.code || 'unknown');
  bad('FINANCE_DATABASE_UNAVAILABLE',503);
}
function safeError(error:unknown) {
  const o=(error && typeof error==='object') ? error as {message?:string;status?:number} : {};
  const errors=new Set([
    'INVALID_INPUT','INVALID_AMOUNT','AMOUNT_OUT_OF_RANGE','INVALID_ASSET',
    'INVALID_ACTION','INVALID_ID','IDEMPOTENCY_KEY_INVALID',
    'FINANCE_DISABLED','FINANCE_DATABASE_UNAVAILABLE','UNAUTHORIZED','FORBIDDEN',
    'INVALID_QUOTE_INPUT','FRESH_VERIFIED_RATE_REQUIRED','INVALID_ORDER_INPUT',
    'INVALID_ORDER_DETAILS','UNVERIFIED_DEPOSIT_WALLET','IDEMPOTENCY_CONFLICT',
    'QUOTE_INVALID_OR_CONSUMED','PROFILE_REQUIRED_OR_RESTRICTED',
    'VERIFIED_IDENTITY_REQUIRED','DAILY_LIMIT_EXCEEDED','QUOTE_CONCURRENTLY_CONSUMED',
  ]);
  return {code:errors.has(o.message||'')?o.message:'INTERNAL_ERROR',
    status:Number.isSafeInteger(o.status)?Number(o.status):500};
}
Deno.serve(async (request:Request)=>{
  const origin=request.headers.get('origin')||'';
  if(request.method==='OPTIONS'){
    if(origin!==ORIGIN)return response('',403,{error:'FORBIDDEN'});
    return new Response(null,{status:204,headers:headers(origin)});
  }
  if(request.method!=='POST')return response(origin,405,{error:'METHOD_NOT_ALLOWED'});
  if(origin && origin!==ORIGIN)return response(origin,403,{error:'FORBIDDEN'});
  if(!BOT_TOKEN || !SERVICE_KEY)return response(origin,503,{error:'FINANCE_NOT_CONFIGURED'});
  const user=await verifyTelegramInitData(
    request.headers.get('x-telegram-init-data') || '',BOT_TOKEN);
  if(!user)return response(origin,401,{error:'UNAUTHORIZED'});
  let body:Body;
  try{
    const raw=await request.text();
    if(raw.length>MAX_BODY)throw new Error('BODY_TOO_LARGE');
    const parsed=JSON.parse(raw);
    if(!parsed || typeof parsed.action!=='string')throw new Error('BAD_BODY');
    body=parsed;
  }catch {return response(origin,400,{error:'BAD_REQUEST'});}
  const input=body.input||{};
  try {
    // Safe capability endpoint supports monitoring even before launch.
    if(body.action==='capabilities')return response(origin,200,{data:{
      trading_enabled:ENABLED,
      bank_settlement_enabled:false,blockchain_settlement_enabled:false,
      remittance_payout_enabled:false,identity_uploads_enabled:false,
      original_bot:'sarafiaf_bot',
    }});
    if(!ENABLED)bad('FINANCE_DISABLED',503);
    const db=client();
    if(body.action==='quote.issue'){
      const params=parseInput(input);
      const {data,error}=await db.rpc('saraf_issue_quote_atomic',{
        p_chat_id:user.id,p_action:action(params.action),
        p_asset:asset(params.asset),p_amount:amount(params.amount),
      });
      rpcFailure(error);
      return response(origin,200,{data});
    }
    if(body.action==='order.submit'){
      const p=parseInput(input);
      const quoteId=id(p.quote_id);
      const key=idem(p.idempotency_key);
      // Never accept browser-provided price, financial amount or actor ID.
      const actionValue=action(p.action),assetValue=asset(p.asset);
      const method=string(p.payment_method,9,9);
      if(method!=='in_person')bad('INVALID_INPUT');
      const network=string(p.network,3,12).toUpperCase();
      const exchange=string(p.exchange_name,2,120);
      const wallet=actionValue==='buy'?string(p.wallet_address,30,150):'';
      const {data,error}=await db.rpc('saraf_submit_order_atomic',{
        p_chat_id:user.id,p_quote_id:quoteId,p_idempotency_key:key,
        p_payload:{
          asset:assetValue,action:actionValue,network,
          payment_method:method,exchange_name:exchange,wallet_address:wallet,
        },
      });
      rpcFailure(error);
      return response(origin,200,{data});
    }
    // All monetary release, settlement, payment receipt and admin status
    // transitions are forbidden until separately verified service integrations.
    return response(origin,403,{error:'FINANCIAL_ACTION_NOT_AVAILABLE'});
  }catch(error){
    const result=safeError(error);
    return response(origin,result.status,{error:result.code});
  }
});
