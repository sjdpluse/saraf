// Pure original admin command parsing with no SDK/runtime secrets.
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
  // The original command is now a signed admin Mini App composer. It never
  // sends a broadcast by chat-text alone; server-side ACL, separate OFF flag
  // and a second explicit confirmation gate remain mandatory.
  out.query.set('admin','broadcast');
  if(args.length>0 && args.length<=512)out.query.set('broadcast',args);
  out.usage='ارسال همگانی تنها پس از تایید هویت مدیر و تایید مجدد در پنل مدیریت امکان‌پذیر است.';
 }
 return out;
}
