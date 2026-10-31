/**
 * Restore ONLY the four ORIGINAL public market history tables that previously
 * depended on the Railway process, using the ORIGINAL BotFather token as a
 * time-limited server-to-server job proof. No financial operation is submitted.
 */
import {signOriginalMarketJob} from '../supabase/functions/saraf-original-market-snapshots/market-auth.mjs';
const token=process.env.SARAF_ORIGINAL_BOT_TOKEN||'';
const action=process.argv[2];
if(!['reference','local'].includes(action)){
 console.error('Usage: node scripts/run_original_saraf_market_snapshots.mjs reference|local');
 process.exit(2);
}
if(!token)throw Error('MISSING_ORIGINAL_SARAF_BOT_GITHUB_SECRET');
const stamp=String(Math.floor(Date.now()/1000));
const signature=await signOriginalMarketJob(token,action,stamp);
const signal=AbortSignal.timeout(action==='reference'?60000:30000);
const endpoint='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-market-snapshots';
try{
 const response=await fetch(endpoint,{
  method:'POST',headers:{
   'Content-Type':'application/json',
   'X-Saraf-Market-Time':stamp,
   'X-Saraf-Market-Signature':signature,
  },
  body:JSON.stringify({action}),cache:'no-store',signal,
 });
 const parsed=await response.json().catch(()=>null);
 if(response.status!==200||
   parsed?.mode!=='ORIGINAL_SARAF_HISTORICAL_MARKET_ONLY'||
   parsed?.action!==action){
  const safe=typeof parsed?.error==='string'&&/^[A-Z0-9_]{3,80}$/.test(parsed.error)
   ?parsed.error:'INVALID_RESPONSE';
  throw Error('ORIGINAL_HISTORY_HTTP_'+response.status+'_'+safe);
 }
 if(!['RECORDED','ALREADY_RECENT'].includes(parsed?.status))
  throw Error('ORIGINAL_HISTORY_RESULT_INVALID');
 if(action==='reference'){
  console.log('Original Saraf reference FX rows recorded:',Number(parsed.currency_rows||0));
  console.log('Original Saraf XAU rows recorded:',Number(parsed.gold_rows||0));
  console.log('Original Saraf XAG rows recorded:',Number(parsed.silver_rows||0));
  if(Array.isArray(parsed.unavailable_metals)&&parsed.unavailable_metals.length)
   console.warn('Metal source temporarily unavailable:',parsed.unavailable_metals.filter(x=>/^(XAU|XAG)$/.test(x)).join(','));
 }else{
  console.log('Original Saraf Kabul/Herat/Da Afghanistan Bank local rows recorded:',
   Number(parsed.local_rows||0));
 }
 console.log('PASS original Saraf '+action+' history: '+parsed.status+' — no funds or client records touched.');
}catch(e){
 const safe=String(e?.message||'UNAVAILABLE').replace(/[^A-Za-z0-9_]/g,'_').slice(0,90);
 console.error('ORIGINAL_HISTORY_JOB_FAILED '+safe);
 process.exitCode=1;
}
