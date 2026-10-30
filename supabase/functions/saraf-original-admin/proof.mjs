// Original admin_bot.py completion proof is a Telegram file_id, NOT a
// public URL or shadow database path. HMAC attestations bind a file uploaded
// using the original customer BOT to one original order and verified admin.
// This token is short lived, and never grants status updates on its own.
// HMAC input is strictly domain-separated from Telegram initData HMAC.
const encoder=new TextEncoder();
const decoder=new TextDecoder('utf-8',{fatal:true});
const error=()=>new Error('INVALID_COMPLETION_PROOF');
function enc(raw){
 let binary='';for(const byte of raw)binary+=String.fromCharCode(byte);
 return btoa(binary).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
function dec(text){
 if(typeof text!=='string'||!text||!/^[A-Za-z0-9_-]+$/.test(text))throw error();
 const base=text.replace(/-/g,'+').replace(/_/g,'/');
 const padding='='.repeat((4-base.length%4)%4);
 const bin=atob(base+padding);
 return Uint8Array.from(bin,c=>c.charCodeAt(0));
}
function checkFields(o){
 if(!o||typeof o!=='object'||Array.isArray(o))throw error();
 if(!Number.isSafeInteger(o.order_id)||o.order_id<=0||
    !Number.isSafeInteger(o.actor_id)||o.actor_id<=0||
    typeof o.file_id!=='string'||o.file_id.length<12||
    o.file_id.length>300||!/^[A-Za-z0-9_-]+$/.test(o.file_id)||
    !['photo','document'].includes(o.file_type)||
    typeof o.file_name!=='string'||o.file_name.length<1||
    o.file_name.length>100||!/^[a-zA-Z0-9._-]+$/.test(o.file_name)||
    !Number.isSafeInteger(o.exp)||!Number.isSafeInteger(o.iat))throw error();
}
async function hmac(key){
 if(typeof key!=='string'||key.length<32)throw error();
 const raw=encoder.encode('saraf-original-admin-completion-proof-v1:'+key);
 return crypto.subtle.importKey('raw',raw,{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);
}
export async function issueOriginalProof(key,fields,now=Date.now()){
 const issued=Math.floor(now/1000);
 const obj={order_id:fields.order_id,actor_id:fields.actor_id,
  file_id:fields.file_id,file_type:fields.file_type,
  file_name:fields.file_name,iat:issued,exp:issued+600};
 checkFields(obj);
 const message=enc(encoder.encode(JSON.stringify(obj)));
 const signature=await crypto.subtle.sign('HMAC',await hmac(key),encoder.encode(message));
 return message+'.'+enc(new Uint8Array(signature));
}
export async function verifyOriginalProof(key,token,owner,order,now=Date.now()){
 try{
  if(typeof token!=='string'||token.length>3000)throw error();
  const parts=token.split('.');
  if(parts.length!==2||parts[1].length!==43)throw error();
  const valid=await crypto.subtle.verify('HMAC',await hmac(key),
   dec(parts[1]),encoder.encode(parts[0]));
  if(!valid)throw error();
  const data=JSON.parse(decoder.decode(dec(parts[0])));
  checkFields(data);
  const t=Math.floor(now/1000);
  if(data.actor_id!==owner||data.order_id!==order||
     data.iat>t+30||data.exp<t||data.exp-data.iat!==600)throw error();
  return {file_id:data.file_id,file_type:data.file_type,
   file_name:data.file_name};
 }catch{throw error();}
}
