// Shared Node 22 / Deno pure webhook HMAC checker for original Meta API.
// No network, no repository credentials, no user data storage.
const utf8=new TextEncoder();
export function constantTimeEqual(a,b){
 if(typeof a!=='string'||typeof b!=='string'||!a||!b||a.length!==b.length)return false;
 let mismatch=0;
 for(let i=0;i<a.length;i++)mismatch|=a.charCodeAt(i)^b.charCodeAt(i);
 return mismatch===0;
}
export async function metaSignatureValid(secret,raw,header){
 if(typeof secret!=='string'||secret.length<16||
   !(raw instanceof Uint8Array)||typeof header!=='string'||
   !/^sha256=[0-9a-f]{64}$/i.test(header))return false;
 const sig=new Uint8Array(32),hex=header.slice(7).toLowerCase();
 for(let i=0;i<32;i++)sig[i]=parseInt(hex.slice(i*2,i*2+2),16);
 const key=await crypto.subtle.importKey('raw',utf8.encode(secret),
   {name:'HMAC',hash:'SHA-256'},false,['verify']);
 return crypto.subtle.verify('HMAC',key,sig,raw);
}
export async function contentHash(raw){
 const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',raw));
 return [...bytes].map(x=>x.toString(16).padStart(2,'0')).join('');
}
