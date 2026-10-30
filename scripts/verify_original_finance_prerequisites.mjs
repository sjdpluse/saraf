/**
 * Original Saraf canonical private finance config audit, safe while money
 * APIs are DISABLED. Uses signed real ORIGINAL admin Telegram initData,
 * produces ONLY missing env names and counts, never recipient addresses
 * or bank details, and never submits orders/calls paid endpoints.
 */
const TOKEN=process.env.SARAF_E2E_ADMIN_INIT_DATA||'';
if(TOKEN.length<70){
 console.error('FAILED: original signed admin Telegram initData missing/expired.');
 process.exit(2);
}
const url='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-transactions';
const controller=new AbortController();
const timer=setTimeout(()=>controller.abort(),20000);
try{
 const r=await fetch(url,{
  method:'POST',headers:{
   'Origin':'https://app8533795882.tgcloud.ai',
   'Content-Type':'application/json','X-Telegram-Init-Data':TOKEN,
  },
  body:JSON.stringify({action:'release.readiness',input:{}}),
  cache:'no-store',credentials:'omit',signal:controller.signal,
 });
 const data=await r.json().catch(()=>null);
 if(!r.ok){
  const code=String(data?.error||'UNEXPECTED_ERROR');
  console.error('FAILED original signed admin finance prerequisites: HTTP '+r.status+
    ' '+(/^[A-Z0-9_]{3,80}$/.test(code)?code:'REDACTED'));
  process.exitCode=1;
 }else{
  const missing=Array.isArray(data?.missing_secret_names)
   ?data.missing_secret_names.filter(x=>/^[A-Z0-9_]{3,90}$/.test(x)):[];
  console.log('Original bank configured: '+Boolean(data.bank_configured));
  console.log('Original sell networks configured: '+JSON.stringify(data.configured_sell_network_counts||{}));
  console.log('Original remittance asset count: '+Number(data.remittance_asset_count||0));
  console.log('Original administrator alerts configured: '+Boolean(data.admin_notifications_configured));
  console.log('Original financial operations currently enabled: '+Boolean(data.financial_api_enabled));
  if(!data.ready_for_cutover||missing.length){
   console.error('RELEASE BLOCKED — missing original private configuration names: '+missing.join(', '));
   process.exitCode=1;
  }else{
   console.log('PASS original bank/wallet/admin settings: ready for controlled finance activation.');
  }
 }
}catch{
 console.error('FAILED: cannot verify original Saraf private finance prereqs; no funds touched.');
 process.exitCode=1;
}finally{clearTimeout(timer);}
