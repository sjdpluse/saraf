// Portable Telegram Mini App initData HMAC verification (Deno and Node.js).
// Does NOT trust initDataUnsafe, localStorage, user-provided Telegram IDs or
// client-side Supabase sessions. Keep bot token only in Edge Function secrets.
const textEncoder=new TextEncoder();
async function sign(key,message){
  const cryptoKey=await crypto.subtle.importKey(
    'raw',key,{name:'HMAC',hash:'SHA-256'},false,['sign']);
  return new Uint8Array(await crypto.subtle.sign(
    'HMAC',cryptoKey,textEncoder.encode(message)));
}
function sameLengthHex(a,b){
  if(a.length!==b.length)return false;
  let difference=0;
  for(let i=0;i<a.length;i++)difference|=a.charCodeAt(i)^b.charCodeAt(i);
  return difference===0;
}
export async function verifyTelegramInitData(raw,botToken,nowSeconds=Math.floor(Date.now()/1000)) {
  if(typeof botToken!=='string' || !botToken.includes(':') ||
      typeof raw!=='string' || raw.length<20 || raw.length>4096)
    return null;
  const entries=[...new URLSearchParams(raw).entries()];
  const keys=entries.map(([key])=>key);
  if(new Set(keys).size!==keys.length)return null;
  const hash=entries.find(([key])=>key==='hash')?.[1]||'';
  if(!/^[0-9a-f]{64}$/i.test(hash))return null;
  const authDate=Number(entries.find(([key])=>key==='auth_date')?.[1]);
  if(!Number.isSafeInteger(authDate) ||
      nowSeconds-authDate>3600 || nowSeconds-authDate< -60)return null;
  const dataCheck=entries.filter(([key])=>key!=='hash')
    .sort(([a],[b])=>a<b?-1:a>b?1:0)
    .map(([key,value])=>key+'='+value).join('\n');
  const secret=await sign(textEncoder.encode('WebAppData'),botToken);
  const computed=Array.from(await sign(secret,dataCheck),
    n=>n.toString(16).padStart(2,'0')).join('');
  if(!sameLengthHex(computed,hash.toLowerCase()))return null;
  let user;
  try {user=JSON.parse(entries.find(([key])=>key==='user')?.[1]||'{}');}
  catch {return null;}
  if(!Number.isSafeInteger(user?.id)||user.id<=0)return null;
  return user;
}
