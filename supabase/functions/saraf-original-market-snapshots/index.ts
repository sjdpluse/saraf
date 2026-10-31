/**
 * Exact ORIGINAL Saraf public reference market-history writer, without Railway.
 * main:jobs.py {fetch_and_store_snapshot,fetch_and_store_local_market}.
 * Reuses the same currency, XAU/XAG and sarafi.af parser port as the original
 * financial quote API; stores only to existing four history tables.
 *
 * Never handles customer sessions, payments, messages, order changes, Meta
 * posts or administrative transitions. No public cron/write endpoint:
 * requires a fresh ORIGINAL bot-token HMAC bound to the exact action.
 */
import {createClient} from 'npm:@supabase/supabase-js@2.57.0';
import {verifyOriginalMarketJob} from './market-auth.mjs';
import {CODES,fetchOriginalCurrencyRates,fetchOriginalMetal,goldSnapshot,
 silverSnapshot,fetchOriginalLocalMarkets} from './markets.mjs';
const URL=Deno.env.get('SUPABASE_URL')||'';
const KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const BOT=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const json=(status:number,body:unknown)=>new Response(JSON.stringify(body),{
 status,headers:{'Content-Type':'application/json','Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff'},
});
type Db=ReturnType<typeof createClient>;
const now=()=>new Date().toISOString();
// Fail closed if state is unknown: never create duplicate historical prices
// on spurious retries, and never replace existing prices with fallback zeros.
async function recent(db:Db,table:string,ageMinutes:number){
 const result=await db.from(table).select('recorded_at')
  .order('recorded_at',{ascending:false}).limit(1);
 if(result.error)throw Error('HISTORY_READ_UNAVAILABLE');
 const last=result.data?.[0]?.recorded_at;
 return !!last && Date.now()-Date.parse(last)<ageMinutes*60000;
}
const positive=(v:unknown)=>Number.isFinite(Number(v))&&Number(v)>0;
async function reference(db:Db){
 if(await recent(db,'currency_history',20))
  return {status:'ALREADY_RECENT',currency_rows:0,gold_rows:0,silver_rows:0};
 const rates=await fetchOriginalCurrencyRates();
 if(!positive(rates.usd)||Number(rates.usd)<10||Number(rates.usd)>1000)
  throw Error('INVALID_ORIGINAL_REFERENCE_USD');
 const rows=CODES.filter(c=>positive(rates[c]))
  .map(c=>({currency:c,afn_rate:rates[c],recorded_at:now()}));
 if(rows.length<4)throw Error('INSUFFICIENT_FX_RATES');
 // Original jobs.py writes FX first. If a metal endpoint fails we preserve
 // successful currency history and explicitly report the missing metal.
 const currency=await db.from('currency_history').insert(rows);
 if(currency.error)throw Error('CURRENCY_SNAPSHOT_UNAVAILABLE');
 const metalResults=await Promise.allSettled(
  (['XAU','XAG'] as const).map(symbol=>fetchOriginalMetal(symbol)));
 const result:{status:string;currency_rows:number;gold_rows:number;silver_rows:number;
  unavailable_metals:string[]}={
  status:'RECORDED',currency_rows:rows.length,gold_rows:0,silver_rows:0,
  unavailable_metals:[],
 };
 for(let i=0;i<metalResults.length;i++){
  const symbol=i===0?'XAU':'XAG';
  const metal=metalResults[i];
  if(metal.status!=='fulfilled'){
   result.unavailable_metals.push(symbol);continue;
  }
  const price=Number(metal.value);
  if(!positive(price)){result.unavailable_metals.push(symbol);continue;}
  const row=symbol==='XAU'
   ?goldSnapshot(price,rates.usd):silverSnapshot(price,rates.usd);
  const table=symbol==='XAU'?'gold_history':'silver_history';
  if(await recent(db,table,20))continue;
  const stored=await db.from(table).insert({...row,recorded_at:now()});
  if(stored.error){result.unavailable_metals.push(symbol);continue;}
  if(symbol==='XAU')result.gold_rows=1;else result.silver_rows=1;
 }
 return result;
}
async function local(db:Db){
 if(await recent(db,'local_market_history',10))
  return {status:'ALREADY_RECENT',local_rows:0};
 const markets=await fetchOriginalLocalMarkets();
 let rows:{market:string;currency:string;buy:number;sell:number;recorded_at:string}[]=[];
 for(const market of ['sarai_shahzada','khorasan_market','da_afg_bank']){
  const entries=markets[market]||{};
  for(const currency of CODES){
   const value=entries[currency];
   if(!positive(value?.buy)||!positive(value?.sell))continue;
   const buy=Number(value.buy),sell=Number(value.sell);
   // Public market source must never poison numeric historical comparisons.
   if(buy>1000000||sell>1000000)continue;
   rows.push({market,currency,buy,sell,recorded_at:now()});
  }
 }
 if(!rows.length)throw Error('NO_VERIFIED_ORIGINAL_LOCAL_MARKETS');
 const stored=await db.from('local_market_history').insert(rows);
 if(stored.error)throw Error('LOCAL_MARKET_SNAPSHOT_UNAVAILABLE');
 return {status:'RECORDED',local_rows:rows.length};
}
Deno.serve(async req=>{
 if(req.method!=='POST')return json(405,{error:'METHOD_NOT_ALLOWED'});
 // No browser use; this is a private server-to-server GitHub scheduled job.
 if(req.headers.get('origin'))return json(403,{error:'BROWSER_DENIED'});
 if(!BOT||!KEY||!URL)return json(503,{error:'ORIGINAL_MARKET_WORKER_NOT_CONFIGURED'});
 let body:{action:string};
 try{
  if(Number(req.headers.get('content-length')||0)>256)
   return json(413,{error:'PAYLOAD_TOO_LARGE'});
  const raw=await req.text();
  if(raw.length>256) return json(413,{error:'PAYLOAD_TOO_LARGE'});
  body=JSON.parse(raw);
  if(!body||typeof body!=='object'||Array.isArray(body)||
    !['reference','local'].includes(body.action))
   return json(400,{error:'INVALID_MARKET_ACTION'});
 }catch{return json(400,{error:'INVALID_JSON'});}
 const valid=await verifyOriginalMarketJob(
  BOT,body.action,
  req.headers.get('x-saraf-market-time')||'',
  req.headers.get('x-saraf-market-signature')||'');
 if(!valid)return json(401,{error:'INVALID_MARKET_JOB_SIGNATURE'});
 const db=createClient(URL,KEY,{auth:{
  persistSession:false,autoRefreshToken:false}});
 try{
  const outcome=body.action==='reference'?await reference(db):await local(db);
  return json(200,{mode:'ORIGINAL_SARAF_HISTORICAL_MARKET_ONLY',action:body.action,...outcome});
 }catch(error){
  const safe=new Set(['HISTORY_READ_UNAVAILABLE','INVALID_ORIGINAL_REFERENCE_USD',
    'INSUFFICIENT_FX_RATES','CURRENCY_SNAPSHOT_UNAVAILABLE',
    'NO_VERIFIED_ORIGINAL_LOCAL_MARKETS','LOCAL_MARKET_SNAPSHOT_UNAVAILABLE']);
  const name=String((error as Error)?.message||'MARKET_SNAPSHOT_UNAVAILABLE');
  console.error('Original public market history update unavailable:',safe.has(name)?name:'SOURCE_UNAVAILABLE');
  return json(503,{error:safe.has(name)?name:'MARKET_SNAPSHOT_UNAVAILABLE'});
 }
});
