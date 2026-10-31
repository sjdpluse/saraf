// GitHub Actions -> ORIGINAL Saraf rate snapshot queue.
// Independent from customer Telegram WebApp initData and from the financial
// release challenge: this HMAC can perform ONLY bounded history inserts.
const ENCODER=new TextEncoder();
const DOMAIN='SARAF_ORIGINAL_MARKET_HISTORY_V1';
const CODES=new Set(['reference','local']);
export async function signOriginalMarketJob(token,action,stamp){
 if(!/^[0-9]{5,15}:[A-Za-z0-9_-]{30,}$/.test(String(token||''))||
    !CODES.has(action)||!/^[0-9]{10}$/.test(String(stamp)))
   throw Error('INVALID_MARKET_JOB_SIGNING_INPUT');
 const key=await crypto.subtle.importKey('raw',ENCODER.encode(token),
  {name:'HMAC',hash:'SHA-256'},false,['sign']);
 const signed=new Uint8Array(await crypto.subtle.sign('HMAC',key,
  ENCODER.encode(DOMAIN+'\n'+action+'\n'+stamp)));
 return [...signed].map(x=>x.toString(16).padStart(2,'0')).join('');
}
export async function verifyOriginalMarketJob(token,action,stamp,signature,now=Date.now()){
 if(!CODES.has(action)||!/^[0-9]{10}$/.test(String(stamp))||
    !/^[0-9a-f]{64}$/.test(String(signature||''))||
    Math.abs(Math.floor(now/1000)-Number(stamp))>45)return false;
 try{
  const key=await crypto.subtle.importKey('raw',ENCODER.encode(token),
   {name:'HMAC',hash:'SHA-256'},false,['verify']);
  const raw=Uint8Array.from(signature.match(/.{2}/g),x=>parseInt(x,16));
  return await crypto.subtle.verify('HMAC',key,raw,
   ENCODER.encode(DOMAIN+'\n'+action+'\n'+stamp));
 }catch{return false;}
}
