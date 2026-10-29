// Public read-only historical rate bridge for ORIGINAL Saraf compare.py.
// Only preexisting price-history and spread tables; never personal/financial
// orders, wallets, KYC or users. Not deployed until reviewed.
import { createClient } from 'npm:@supabase/supabase-js@2.57.0';
const CODES=new Set(['usd','eur','gbp','pkr','irr','aed','inr','sar',
 'try','cny','aud','cad','chf','sek']);
const DAYS=new Set([1,7,30,90]);
const ORIGIN='https://app8533795882.tgcloud.ai';
function respond(status:number,data:unknown){
 return new Response(JSON.stringify(data),{
  status,headers:{'Content-Type':'application/json','Cache-Control':'no-store',
   'Access-Control-Allow-Origin':ORIGIN,'Vary':'Origin'}
 });
}
Deno.serve(async request=>{
 if(request.method!=='GET')return respond(405,{error:'METHOD_NOT_ALLOWED'});
 const url=new URL(request.url);
 const target=String(url.searchParams.get('target')||'').toLowerCase();
 const days=Number(url.searchParams.get('days'));
 if(url.searchParams.get('mode')!=='spreads'&&
    (!(target==='gold'||CODES.has(target))||!DAYS.has(days)))
  return respond(400,{error:'INVALID_COMPARE_SELECTION'});
 const service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
 const endpoint=Deno.env.get('SUPABASE_URL');
 if(!service||!endpoint)return respond(503,{error:'DATABASE_UNAVAILABLE'});
 const db=createClient(endpoint,service,{
  auth:{autoRefreshToken:false,persistSession:false},
 });
 if(url.searchParams.get('mode')==='spreads'){
  const r=await db.from('spread_settings').select('currency,spread_percent')
   .limit(100);
  if(r.error)return respond(503,{error:'SPREADS_UNAVAILABLE'});
  const spreads:Record<string,number>={};
  for(const row of r.data||[]){
    if(CODES.has(row.currency) && Number.isFinite(Number(row.spread_percent)))
      spreads[row.currency]=Number(row.spread_percent);
  }
  return respond(200,{spreads});
 }
 const when=new Date(Date.now()-days*86400000).toISOString();
 const before=<T,>(v:{data:T|null;error:unknown})=>{
  if(v.error)throw Error('DATABASE_UNAVAILABLE');
  return v.data;
 };
 try{
  if(target==='gold'){
   const q=await db.from('gold_history').select('afn_per_gram_24k')
    .lte('recorded_at',when).order('recorded_at',{ascending:false})
    .limit(1).maybeSingle();
   const row=before(q);
   return respond(200,{target,days,reference_old:row?.afn_per_gram_24k??null,
    old_local:null,spread_percent:null});
  }
  const [local,reference,spread]=await Promise.all([
   db.from('local_market_history').select('buy,sell')
    .eq('market','sarai_shahzada').eq('currency',target)
    .lte('recorded_at',when).order('recorded_at',{ascending:false})
    .limit(1).maybeSingle(),
   db.from('currency_history').select('afn_rate')
    .eq('currency',target).lte('recorded_at',when)
    .order('recorded_at',{ascending:false}).limit(1).maybeSingle(),
   db.from('spread_settings').select('spread_percent')
    .eq('currency',target).maybeSingle(),
  ]);
  const oldLocal=before(local),oldReference=before(reference),setting=before(spread);
  return respond(200,{
   target,days,
   reference_old:oldReference?.afn_rate??null,
   old_local:oldLocal?{buy:oldLocal.buy,sell:oldLocal.sell}:null,
   spread_percent:setting?.spread_percent??null,
  });
 }catch{
  return respond(503,{error:'HISTORY_UNAVAILABLE'});
 }
});
