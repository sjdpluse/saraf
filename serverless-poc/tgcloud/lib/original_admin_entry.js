// Original /stats, /spreads, /setspread, /usdtpending, /usdtconfirm.
// Telegram Serverless has no documented server-side secrets store; do NOT
// forward an unsigned from.id to a privileged Supabase finance endpoint.
// Instead require Telegram's independently signed Mini App initData + server
// admin allowlist before any protected read or write.
import {api} from 'sdk';
const BASE='https://app8533795882.tgcloud.ai/';
const FLAGS=new Set(['stats','spreads','usdtpending','setspread','usdtconfirm','broadcast']);
const VALID_CODES=new Set(['usd','eur','gbp','pkr','irr','aed','inr','sar',
 'try','cny','aud','cad','chf','sek']);
export function parseOriginalAdminCommand(input){
 const raw=String(input||'').trim();
 const m=/^\/([a-z]+)(?:@[A-Za-z0-9_]+)?(?:\s+(.*))?$/i.exec(raw);
 if(!m)return null;
 const name=m[1].toLowerCase(),args=(m[2]||'').trim();
 if(!FLAGS.has(name))return null;
 const out={name,query:new URLSearchParams({action:'admin'})};
 if(name==='stats')out.query.set('admin','stats');
 if(name==='spreads')out.query.set('admin','spreads');
 if(name==='usdtpending')out.query.set('admin','pending');
 if(name==='setspread'){
  out.query.set('admin','setspread');
  const parts=args.split(/\s+/);
  if(parts.length===2&&VALID_CODES.has(parts[0].toLowerCase())&&
    /^\d{1,2}(?:\.\d{1,2})?$/.test(parts[1])&&Number(parts[1])<=20){
   out.query.set('currency',parts[0].toLowerCase());
   out.query.set('percent',parts[1]);
  }else out.usage='استفاده: /setspread usd 0.8';
 }
 if(name==='usdtconfirm'){
  out.query.set('admin','confirm');
  const id=args.replace(/^USDT-/i,'').trim();
  if(/^[1-9]\d{0,12}$/.test(id))out.query.set('order_id',id);
  else out.usage='استفاده: /usdtconfirm 12';
 }
 if(name==='broadcast'){
  out.usage='ارسال همگانی /broadcast تا تکمیل سیستم صف امن، غیرفعال است.';
 }
 return out;
}
export async function handleOriginalAdminCommand(message){
 const cmd=parseOriginalAdminCommand(message?.text);
 if(!cmd)return false;
 const chat=message.chat?.id;
 if(!Number.isSafeInteger(chat)||chat!==message.from?.id||
    message.chat?.type!=='private')return false;
 if(cmd.name==='broadcast'){
  await api.sendMessage({chat_id:chat,text:cmd.usage});
  return true;
 }
 // A URL alone gives no privilege. Original Supabase Edge checks HMAC
 // over initData and compares user ID against private SARAF_ADMIN_CHAT_IDS.
 const url=BASE+'?'+cmd.query.toString();
 await api.sendMessage({
  chat_id:chat,
  text:cmd.usage?cmd.usage+'\n\nمعلومات را در پنل مدیریت تکمیل کنید.':
    '🔐 برای اجرای دستور، هویت مدیر باید در Mini App اصلی تأیید شود.',
  reply_markup:{inline_keyboard:[[
   {text:'🔐 پنل مدیریت صراف',web_app:{url}},
  ]]},
 });
 return true;
}
