/**
 * Strict read-only original Saraf cutover preflight. Zero real finance writes.
 * Feed *fresh genuine* Telegram Mini App initData from ORIGINAL bot through
 * GitHub Actions SECRETS, never command-line arguments or stdout.
 *
 * Unlike a synthetic CI test this verifies owner signed auth and original
 * canonical Supabase Edge functions, required private feature gates, admin
 * allowlist and original configured network recipient wallets LIVE.
 *
 * Nothing in this script sends money, uploads identity documents, accepts
 * an order, confirms a payment or touches Telegram webhook.
 */
const ROOT='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1';
const ORIGIN='https://app8533795882.tgcloud.ai';
const user=process.env.SARAF_E2E_USER_INIT_DATA||'';
const admin=process.env.SARAF_E2E_ADMIN_INIT_DATA||'';
if(user.length<70||admin.length<70){
 console.error('FAILED: fresh original Telegram user/admin signed initData secrets missing.');
 process.exit(20);
}
const tests=[
 ['Canonical owner profile','saraf-telegram-bridge',user,{action:'profile.get',input:{}},200],
 ['Canonical owned orders','saraf-telegram-bridge',user,{action:'orders.me',input:{limit:1,offset:0}},200],
 ['Original stablecoin configured networks','saraf-original-transactions',user,{action:'stablecoins.config',input:{}},200],
 ['Original remittance configured wallets','saraf-original-transactions',user,{action:'remittances.config',input:{}},200],
 ['Original verified admin account','saraf-original-admin',admin,{action:'stats',input:{}},200],
 ['Original verified admin KYC read','saraf-original-admin',admin,{action:'kyc.pending',input:{}},200],
 ['Original admin write switch without writing money','saraf-original-admin',admin,{action:'order.complete',input:{order_id:-1}},400],
 ['Original KYC review gate without changing an account','saraf-original-admin',admin,{action:'kyc.review',input:{chat_id:-1,decision:'verify'}},400],
 ['Original /broadcast capability, no sends','saraf-original-admin',admin,{action:'broadcast.status',input:{broadcast_id:-1}},400],
 ['Original /start /stop preference read','saraf-original-notifications',user,{action:'read'},200],
];
async function probe([title,fn,token,body,expected]){
 const ctrl=new AbortController();
 const timer=setTimeout(()=>ctrl.abort(),20000);
 try{
  const response=await fetch(ROOT+'/'+fn,{
   method:'POST',headers:{'Content-Type':'application/json','Origin':ORIGIN,
    'X-Telegram-Init-Data':token},body:JSON.stringify(body),
   credentials:'omit',cache:'no-store',signal:ctrl.signal,
  });
  const parsed=await response.json().catch(()=>null);
  if(response.status!==expected){
   // Only print a standardized backend status code; never expose customer
   // records, signed Telegram initData or user supplied error messages.
   const code=String(parsed?.error||'');
   const safe=/^[A-Z][A-Z0-9_]{2,70}$/.test(code)?code:'UNKNOWN_ERROR';
   throw Error('HTTP '+response.status+' '+safe+' (expected '+expected+')');
  }
  if(expected===200&&parsed?.error)throw Error('Backend returned '+String(parsed.error).slice(0,70));
  if(expected===400&&typeof parsed?.error!=='string')
   throw Error('Expected signed input rejection payload');
  if(fn==='saraf-original-transactions'&&body.action==='remittances.config'){
   if(!Array.isArray(parsed?.assets)||!parsed.assets.some(a=>
      Array.isArray(a.networks)&&a.networks.length>0))
     throw Error('original deposit wallets are not configured');
  }
  console.log('PASS '+title+' ('+response.status+')');
  return true;
 }catch(error){
  // Never print raw response, signed initData, wallet address, or customer rows.
  console.error('FAIL '+title+': '+String(error.message).replace(/https?:\/\/\S+/g,'[redacted]'));
  return false;
 }finally{clearTimeout(timer);}
}
let ok=true;
for(const check of tests)if(!await probe(check))ok=false;
if(!ok){
 console.error('RELEASE BLOCKED: original signed production capability preflight failed.');
 process.exit(1);
}
console.log('Original bot financial/admin read-only preflight passed; no money or customer data was changed.');
