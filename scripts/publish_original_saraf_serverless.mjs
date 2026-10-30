/**
 * ORIGINAL @sarafiaf_bot migration cutover. NEVER runs on a push/PR.
 * Called only by manual dispatch after *real* signed original-bot preflight.
 * Deploys the already-tested full original React + allowlisted tgcloud code,
 * without creating any Telegram SQLite financial tables.
 *
 * Requires BotFather Serverless CLI ACCESS token, different from BOT_TOKEN.
 * Fails closed if CLI token belongs to any project except app8533795882.
 * Attempts to restore the previous webhook on a failed push/smoke.
 */
import {spawn} from 'node:child_process';
const TOKEN=process.env.TGCLOUD_TOKEN||'';
const BOT=process.env.SARAF_ORIGINAL_BOT_TOKEN||'';
const PREVIOUS_SECRET=process.env.SARAF_ORIGINAL_PREVIOUS_WEBHOOK_SECRET||'';
const APP='https://app8533795882.tgcloud.ai/';
const target='sarafiaf_bot';
if(!/^app8533795882:[A-Za-z0-9_-]{16,}$/.test(TOKEN))
 throw Error('TGCLOUD_TOKEN_NOT_MATCHING_ORIGINAL_APP_ID');
if(!/^[0-9]{5,15}:[A-Za-z0-9_-]{30,}$/.test(BOT))
 throw Error('ORIGINAL_BOT_API_TOKEN_MISSING');
const base='https://api.telegram.org/bot'+BOT+'/';
async function botApi(method,body){
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),15000);
 try{
  const r=await fetch(base+method,{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify(body||{}),signal:ctrl.signal,cache:'no-store',
  });
  const j=await r.json();
  if(!r.ok||!j.ok)throw Error('TELEGRAM_BOT_API_'+method+'_ERROR');
  return j.result;
 }finally{clearTimeout(timer);}
}
async function push(){
 const dir=new URL('../serverless-poc/.release-original/',import.meta.url);
 return new Promise((resolve,reject)=>{
  const cmd=spawn('npx',['--no-install','tgcloud','push'],{
   cwd:dir,env:process.env,stdio:'inherit',shell:false,
  });
  cmd.once('error',reject);
  cmd.once('close',c=>c===0?resolve():reject(Error('TGCLOUD_PUSH_FAILED')));
 });
}
let previous;
let started=false;
let success=false;
try{
 const who=await botApi('getMe');
 if(!who?.is_bot||who.username?.toLowerCase()!==target)
  throw Error('BOT_TOKEN_NOT_ORIGINAL_SARAF');
 previous=await botApi('getWebhookInfo');
 // Neither this address nor the Telegram tokens are ever printed.
 if(previous?.url&&
    (!previous.url.startsWith('https://')||previous.url.length>1024))
  throw Error('PREVIOUS_WEBHOOK_NOT_RESTORABLE');
 console.log('Verified original @sarafiaf_bot and pinned app8533795882.');
 console.log('Uploading full original Saraf React and TG JS modules atomically...');
 started=true;
 await push();
 const info=await botApi('getWebhookInfo');
 if(!info?.url?.startsWith('https://'))
  throw Error('NEW_TGCLOUD_WEBHOOK_NOT_ACTIVE');
 // A successful CLI exit alone is not a migration: the ORIGINAL Railway
 // webhook must actually change before we announce that traffic moved.
 if(previous?.url&&info.url===previous.url&&
    !/(?:tgcloud|telegram\.org)/i.test(previous.url))
  throw Error('ORIGINAL_RAILWAY_WEBHOOK_UNCHANGED');
 const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),20000);
 try{
  const r=await fetch(APP,{cache:'no-store',signal:ctl.signal});
  const html=await r.text();
  if(!r.ok||!/<html[\s>]/i.test(html))
   throw Error('ORIGINAL_MINI_APP_HOST_FAILED');
 }finally{clearTimeout(timer);}
 console.log('Verified original Telegram webhook and live Mini App homepage.');
 success=true;
}catch(error){
 console.error('CUTOVER_FAILED: '+String(error?.message||'unknown'));
 if(started&&previous){
  try{
   if(previous.url){
    const args={url:previous.url,drop_pending_updates:false};
    if(Array.isArray(previous.allowed_updates))
     args.allowed_updates=previous.allowed_updates;
    if(PREVIOUS_SECRET)args.secret_token=PREVIOUS_SECRET;
    await botApi('setWebhook',args);
   }else{
    await botApi('deleteWebhook',{drop_pending_updates:false});
   }
   console.error('RESTORED_PREVIOUS_TELEGRAM_WEBHOOK (Railway deployment not touched).');
  }catch{
   console.error('CRITICAL: automatic webhook rollback failed; immediately restore original webhook in @BotFather/Telegram.');
  }
 }
 process.exitCode=1;
}
if(success)console.log('ORIGINAL_SARAF_CUTOVER_PUSH_SUCCEEDED; review money transactions and disable old Railway manually.');
