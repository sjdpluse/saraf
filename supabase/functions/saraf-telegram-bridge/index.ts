// Saraf canonical Supabase bridge: signed Telegram Mini App identity -> existing
// historical Supabase tables. Never expose the service-role key to the Mini App.
// Financial order creation, settlements, KYC uploads and transfers are disabled.
import { createClient } from 'npm:@supabase/supabase-js@2.57.0';
import { verifyTelegramInitData } from './telegram-auth.mjs';

type DbRow=Record<string,any>; // Supabase legacy tables have dynamic historic columns.
type TelegramUser={id:number;first_name?:string;last_name?:string;username?:string};

const SUPABASE_URL = Deno.env.get('SUPABASE_URL') || '';
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || '';
const BOT_TOKEN = Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN') || Deno.env.get('TELEGRAM_BOT_TOKEN') || '';
const allowedOrigin = (origin:string):boolean => origin === 'https://app8533795882.tgcloud.ai';
const resultHeaders = (origin:string) => ({
  'content-type':'application/json;charset=utf-8',
  'cache-control':'no-store',
  'vary':'Origin',
  ...(allowedOrigin(origin) ? {'access-control-allow-origin': origin} : {}),
  'access-control-allow-headers':'content-type,x-telegram-init-data',
  'access-control-allow-methods':'POST,OPTIONS',
});
function answer(origin:string, status:number, body:unknown):Response {
  return new Response(JSON.stringify(body),{status,headers:resultHeaders(origin)});
}
function validString(value:unknown,min:number,max:number):string {
  const text=String(value ?? '').trim();
  if(text.length<min||text.length>max)throw new Error('INVALID_INPUT');
  return text;
}
function validId(raw:unknown):number {
  const id=Number(raw);
  if(!Number.isSafeInteger(id)||id<=0)throw new Error('INVALID_ID');
  return id;
}
function check(error:unknown):void {
  if(error)throw new Error('DATABASE_UNAVAILABLE');
}
function client() {
  return createClient(SUPABASE_URL,SUPABASE_SERVICE_ROLE_KEY,{
    auth:{autoRefreshToken:false,persistSession:false},
  });
}
function originalReviewsAdmin(userId:number):boolean {
  // Mirrors original Python ADMIN_CHAT_IDS server-only allowlist.
  return (Deno.env.get('SARAF_ADMIN_CHAT_IDS')||'').split(',')
    .some(value=>value.trim()===String(userId));
}
function safeProfile(row:DbRow|null) {
  return {
    has_basic_profile:Boolean(row?.first_name && row?.last_name && row?.phone),
    has_identity_verification:Boolean(row?.id_document_path && row?.selfie_path &&
      ['verified','trusted'].includes(row.kyc_status)),
    identity_verification_threshold_usd:250,
    kyc_status:row?.kyc_status||'pending',
    identity_uploads_enabled:false,
    profile:row ? { first_name:row.first_name,last_name:row.last_name,
      phone:row.phone,kyc_status:row.kyc_status }:null,
    uploaded:{kyc_id:Boolean(row?.id_document_path),
      selfie:Boolean(row?.selfie_path),receipt:false,beneficiary_id:false},
  };
}
function publicOrder(row:DbRow) {
  return {id:row.id,asset:row.asset||'USDT',order_type:row.order_type,
    usdt_amount:row.usdt_amount,total_afn:row.total_afn,usd_rate:row.usd_rate,
    network:row.network,status:row.status,rating:row.rating,
    created_at:row.created_at,completed_at:row.completed_at};
}
// Match services/remittance_service.py:remittance_code and
// services/remittance_api_router.py:_client_order. Never expose pickup codes
// before payout_ready/completed or the internal administrative fields.
function publicRemittance(row:DbRow) {
  return {id:row.id,order_code:'REM-'+String(row.id).padStart(6,'0'),
    asset:row.asset,network:row.network,
    crypto_amount:row.crypto_amount,payout_afn:row.payout_afn,
    usd_rate:row.usd_rate,status:row.status,verification_status:row.verification_status,
    beneficiary_full_name:row.beneficiary_full_name,
    beneficiary_province:row.beneficiary_province,
    beneficiary_city:row.beneficiary_city,tx_hash:row.tx_hash||null,
    created_at:row.created_at,
    ...(['payout_ready','completed'].includes(row.status)&&row.pickup_code
      ? {pickup_code:row.pickup_code}:{}),
  };
}
async function handler(db:ReturnType<typeof client>,user:TelegramUser,action:string,input:DbRow) {
  if(action==='profile.get'){
    const {data,error}=await db.from('user_profiles')
      .select('first_name,last_name,phone,kyc_status,id_document_path,selfie_path')
      .eq('chat_id',user.id).maybeSingle();
    check(error);
    return safeProfile(data);
  }
  if(action==='profile.save'){
    const first_name=validString(input?.first_name,2,80);
    const last_name=validString(input?.last_name,2,80);
    const phone=validString(input?.phone,7,24);
    if(!/^\+?[0-9۰-۹٠-٩ ()-]+$/.test(phone))throw new Error('INVALID_PHONE');
    const {error}=await db.from('user_profiles').upsert({
      chat_id:user.id,first_name,last_name,phone,
    },{onConflict:'chat_id'});
    check(error);
    return {ok:true};
  }
  if(action==='orders.me'){
    const {data,error}=await db.from('usdt_orders')
      .select('id,asset,order_type,usdt_amount,total_afn,usd_rate,network,status,rating,created_at,completed_at')
      .eq('chat_id',user.id).order('created_at',{ascending:false}).limit(50);
    check(error);
    return (data||[]).map(publicOrder);
  }
  if(action==='orders.rate'){
    const id=validId(input?.order_id);
    const rating=Number(input?.rating);
    if(!Number.isSafeInteger(rating)||rating<1||rating>5)throw new Error('INVALID_RATING');
    const comment=input?.comment==null?null:validString(input.comment,1,800);
    const {data,error}=await db.from('usdt_orders').update({
      rating,rating_comment:comment,rated_at:new Date().toISOString(),
    }).eq('id',id).eq('chat_id',user.id).eq('status','completed')
      .is('rating',null).select('id');
    check(error);
    if(!data?.length)throw new Error('RATING_NOT_ALLOWED');
    return {ok:true};
  }
  if(action==='remittances.me'){
    const {data,error}=await db.from('remittance_orders')
      .select('id,asset,network,crypto_amount,payout_afn,usd_rate,status,verification_status,beneficiary_full_name,beneficiary_province,beneficiary_city,tx_hash,pickup_code,created_at')
      .eq('chat_id',user.id).order('created_at',{ascending:false}).limit(50);
    check(error);
    return (data||[]).map(publicRemittance);
  }
  if(action==='stats.get'){
    const {data,error,count}=await db.from('usdt_orders')
      .select('rating',{count:'exact'}).eq('status','completed').limit(1000);
    check(error);
    const ratings=(data||[]).map((row:DbRow)=>Number(row.rating))
      .filter((value:number)=>Number.isSafeInteger(value)&&value>=1&&value<=5);
    return {completed_orders:count||0,
      average_rating:ratings.length
        ?Math.round(100*ratings.reduce((a:number,b:number)=>a+b,0)/ratings.length)/100:null};
  }
  if(action==='reviews.list'){
    const limit=Math.min(50,Math.max(1,Number(input?.limit)||20));
    const offset=Math.max(0,Number(input?.offset)||0);
    if(!Number.isSafeInteger(limit)||!Number.isSafeInteger(offset)||offset>2000)
      throw new Error('INVALID_PAGINATION');
    const {data,error,count}=await db.from('miniapp_reviews')
      .select('id,display_name,body,admin_reply,admin_replied_at,created_at',{count:'exact'})
      .eq('is_visible',true).order('created_at',{ascending:false})
      .range(offset,offset+limit-1);
    check(error);
    const ids=(data||[]).map((row:DbRow)=>row.id);
    let votes:DbRow[]=[];
    if(ids.length){
      const result=await db.from('miniapp_review_votes')
        .select('review_id,chat_id,vote').in('review_id',ids);
      check(result.error);
      votes=result.data||[];
    }
    const items=(data||[]).map((row:DbRow)=>{
      const myVotes=votes.filter((v:DbRow)=>v.review_id===row.id);
      return {...row,likes:myVotes.filter((v:DbRow)=>v.vote===1).length,
        dislikes:myVotes.filter((v:DbRow)=>v.vote===-1).length,
        user_vote:myVotes.find((v:DbRow)=>String(v.chat_id)===String(user.id))?.vote||0};
    });
    return {items,total:count||0,is_admin:originalReviewsAdmin(user.id)};
  }
  if(action==='reviews.create'){
    const body=validString(input?.body,3,800).replace(/\s+/g,' ');
    const previous=await db.from('miniapp_reviews').select('created_at')
      .eq('chat_id',user.id).order('created_at',{ascending:false}).limit(1);
    check(previous.error);
    if(previous.data?.length &&
       Date.now()-Date.parse(previous.data[0].created_at)<30_000)
      throw new Error('RATE_LIMIT');
    const display_name=([user.first_name,user.last_name].filter(Boolean).join(' ')||'کاربر صراف').slice(0,100);
    const {data,error}=await db.from('miniapp_reviews').insert({
      chat_id:user.id,display_name,username:String(user.username||'').slice(0,80)||null,
      body,is_visible:true,
    }).select('id,display_name,body,admin_reply,admin_replied_at,created_at').single();
    check(error);
    return {...data,likes:0,dislikes:0,user_vote:0};
  }
  if(action==='reviews.reply'){
    if(!originalReviewsAdmin(user.id))throw new Error('ADMIN_NOT_ALLOWED');
    const id=validId(input?.review_id);
    const body=validString(input?.body,3,1200).replace(/\s+/g,' ');
    const now=new Date().toISOString();
    const updated=await db.from('miniapp_reviews').update({
      admin_reply:body,admin_replied_at:now,updated_at:now,
    }).eq('id',id).eq('is_visible',true)
      .select('id,display_name,body,admin_reply,admin_replied_at,created_at')
      .maybeSingle();
    check(updated.error);
    if(!updated.data)throw new Error('NOT_FOUND');
    const votes=await db.from('miniapp_review_votes')
      .select('chat_id,vote').eq('review_id',id);
    check(votes.error);
    const data=votes.data||[];
    return {...updated.data,
      likes:data.filter((v:DbRow)=>v.vote===1).length,
      dislikes:data.filter((v:DbRow)=>v.vote===-1).length,
      user_vote:data.find((v:DbRow)=>String(v.chat_id)===String(user.id))?.vote||0,
    };
  }
  if(action==='reviews.vote'){
    const id=validId(input?.review_id), vote=Number(input?.vote);
    if(!Number.isSafeInteger(vote)||![-1,0,1].includes(vote))throw new Error('INVALID_VOTE');
    const current=await db.from('miniapp_reviews').select('id')
      .eq('id',id).eq('is_visible',true).maybeSingle();
    check(current.error);
    if(!current.data)throw new Error('NOT_FOUND');
    const votes=db.from('miniapp_review_votes');
    if(vote===0){
      const {error}=await votes.delete().eq('review_id',id).eq('chat_id',user.id);
      check(error);
    }else{
      const {error}=await votes.upsert({
        review_id:id,chat_id:user.id,vote,updated_at:new Date().toISOString(),
      },{onConflict:'review_id,chat_id'});
      check(error);
    }
    const {data,error}=await db.from('miniapp_review_votes')
      .select('chat_id,vote').eq('review_id',id);
    check(error);
    return {review_id:id,likes:(data||[]).filter((v:DbRow)=>v.vote===1).length,
      dislikes:(data||[]).filter((v:DbRow)=>v.vote===-1).length,
      user_vote:(data||[]).find((v:DbRow)=>String(v.chat_id)===String(user.id))?.vote||0};
  }
  throw new Error('ACTION_DISABLED');
}
Deno.serve(async(req)=>{
  const origin=req.headers.get('origin')||'';
  if(req.method==='OPTIONS'){
    if(!allowedOrigin(origin))return answer(origin,403,{error:'ORIGIN_NOT_ALLOWED'});
    return new Response(null,{status:204,headers:resultHeaders(origin)});
  }
  if(req.method!=='POST')return answer(origin,405,{error:'METHOD_NOT_ALLOWED'});
  // CORS does not replace HMAC verification; also reject unknown browser origins.
  if(origin && !allowedOrigin(origin))return answer(origin,403,{error:'ORIGIN_NOT_ALLOWED'});
  if(!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY || !BOT_TOKEN)
    return answer(origin,503,{error:'SERVER_NOT_CONFIGURED'});
  const initData=req.headers.get('x-telegram-init-data')||'';
  const user=await verifyTelegramInitData(initData,BOT_TOKEN);
  if(!user)return answer(origin,401,{error:'INVALID_TELEGRAM_AUTH'});
  let request;
  try{
    const raw=await req.text();
    if(raw.length>12000)throw new Error('TOO_LARGE');
    request=JSON.parse(raw);
    if(!request||typeof request!=='object'||Array.isArray(request))throw new Error('INVALID_REQUEST');
  }catch{return answer(origin,400,{error:'INVALID_REQUEST'});}
  try{
    const data=await handler(client(),user,request.action,request.input||{});
    return answer(origin,200,{data});
  }catch(error){
    const safe=new Set([
      'INVALID_INPUT','INVALID_PHONE','INVALID_ID','INVALID_RATING',
      'RATING_NOT_ALLOWED','INVALID_PAGINATION','RATE_LIMIT',
      'INVALID_VOTE','NOT_FOUND','ACTION_DISABLED','DATABASE_UNAVAILABLE',
    ]);
    const message=error instanceof Error ? error.message : 'INTERNAL_ERROR';
    const code=safe.has(message)?message:'INTERNAL_ERROR';
    return answer(origin,code==='DATABASE_UNAVAILABLE'?503:
      code==='ACTION_DISABLED'?403:
      code==='RATE_LIMIT'?429:code==='INTERNAL_ERROR'?500:400,{error:code});
  }
});
