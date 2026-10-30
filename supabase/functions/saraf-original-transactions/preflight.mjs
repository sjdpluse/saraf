// PRIVATE MACHINE-TO-MACHINE ORIGINAL Saraf deploy-readiness challenge.
// This never grants customer/admin data or writes and is NOT Telegram initData.
// Caller must possess the original bot API token via GitHub secret.
// Fresh HMAC prevents replay. Domain separation avoids accidental reuse.
const encoder=new TextEncoder();
const DOMAIN='SARAF_ORIGINAL_RELEASE_PREFLIGHT_V1';
const HEX=/^[0-9a-f]{64}$/;
export async function originalReleaseSignature(botToken,timestamp){
 if(typeof botToken!=='string'||botToken.length<30||
    !/^[0-9]{5,15}:[A-Za-z0-9_-]{30,}$/.test(botToken)||
    !/^[0-9]{10}$/.test(String(timestamp)))throw Error('INVALID_RELEASE_AUTH');
 const k=await crypto.subtle.importKey('raw',encoder.encode(botToken),
  {name:'HMAC',hash:'SHA-256'},false,['sign','verify']);
 const bytes=new Uint8Array(await crypto.subtle.sign('HMAC',k,
  encoder.encode(DOMAIN+'\\n'+timestamp)));
 return [...bytes].map(x=>x.toString(16).padStart(2,'0')).join('');
}
export async function verifyOriginalReleaseProof(botToken,stamp,signature,
 now=Date.now()){
 if(typeof stamp!=='string'||!/^[0-9]{10}$/.test(stamp)||
    typeof signature!=='string'||!HEX.test(signature))return false;
 const diff=Math.abs(Math.floor(now/1000)-Number(stamp));
 if(!Number.isSafeInteger(Number(stamp))||diff>45)return false;
 try{
  const expected=await originalReleaseSignature(botToken,stamp);
  // Constant-time WebCrypto.verify avoids string-comparison timing leaks.
  const k=await crypto.subtle.importKey('raw',encoder.encode(botToken),
   {name:'HMAC',hash:'SHA-256'},false,['verify']);
  return await crypto.subtle.verify('HMAC',k,
   Uint8Array.from(signature.match(/.{2}/g),b=>parseInt(b,16)),
   encoder.encode(DOMAIN+'\\n'+stamp));
 }catch{return false;}
}
