/**
 * Real ORIGINAL @sarafiaf_bot production read-only release verification.
 * Sends a fresh, 45-second, domain-separated HMAC signed with the ORIGINAL
 * bot API token from GitHub secret to the canonical original Supabase Edge.
 * NOT a fabricated Telegram WebApp session. No payments/updates performed.
 * Safe after the old initData secrets expire in 1h.
 */
import {originalReleaseSignature} from
 '../supabase/functions/saraf-original-transactions/preflight.mjs';
const key=process.env.SARAF_ORIGINAL_BOT_TOKEN||'';
const timestamp=String(Math.floor(Date.now()/1000));
if(!key)throw Error('MISSING_ORIGINAL_BOT_API_TOKEN_SECRET');
const signature=await originalReleaseSignature(key,timestamp);
const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),20000);
try{
 const url='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-transactions';
 const response=await fetch(url,{
  method:'POST',headers:{
   'Origin':'https://app8533795882.tgcloud.ai',
   'Content-Type':'application/json',
   'X-Saraf-Release-Time':timestamp,
   'X-Saraf-Release-Signature':signature,
  },
  body:JSON.stringify({action:'release.preflight'}),
  cache:'no-store',credentials:'omit',signal:ctrl.signal,
 });
 const reply=await response.json().catch(()=>({}));
 if(!response.ok)throw Error('SIGNED_RELEASE_PREFLIGHT_HTTP_'+response.status+
   (typeof reply?.error==='string'&&/^[A-Z0-9_]+$/.test(reply.error)
    ?'_'+reply.error:''));
 if(reply?.mode!=='original_Saraf_production_readiness_READ_ONLY')
  throw Error('UNEXPECTED_ORIGINAL_PRODUCTION_READINESS_PAYLOAD');
 const booleans=reply?.enabled||{};
 for(const [k,v] of Object.entries(booleans))
  console.log('Original Saraf feature '+k+': '+(v?'ON':'OFF'));
 console.log('Canonical bank setup: '+(reply.bank_ready?'READY':'MISSING'));
 console.log('Original admin notifications: '+(reply.admin_notifications_ready?'READY':'MISSING'));
 console.log('Original USDT/USDC sell network counts: '+
  JSON.stringify(reply.configured_sell_network_counts||{}));
 console.log('Original remittance asset count: '+Number(reply.remittance_asset_count||0));
 if(reply.ready_for_cutover!==true)
  throw Error('ORIGINAL_FINANCIAL_CUTOVER_FLAGS_INCOMPLETE');
 console.log('PASS: all signed original Saraf production prerequisite flags and bank/wallet configurations are enabled.');
}catch(e){
 const safe=String(e?.message||'PREFLIGHT_ERROR').replace(/[^A-Za-z0-9_]/g,'_').slice(0,100);
 console.error('RELEASE BLOCKED: '+safe);
 process.exitCode=1;
}finally{clearTimeout(timer);}
