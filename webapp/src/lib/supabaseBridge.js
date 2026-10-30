// Saraf legacy Supabase is the source of truth for customers, orders and reviews.
// This adapter NEVER ships a Supabase secret/anon key and never falls back to
// the independent Telegram-native SQLite tables for existing financial records.
import { getInitData } from './telegram';

const CANONICAL_REF='cvernmhpnsgdtegvblyc';
const EDGE_URL='https://'+CANONICAL_REF+'.supabase.co/functions/v1/saraf-telegram-bridge';
const ALLOWED_ACTIONS=new Set([
  'profile.get','profile.save','orders.me','orders.rate','remittances.me',
  'stats.get','reviews.list','reviews.create','reviews.vote','reviews.reply',
]);

export class CanonicalBridgeError extends Error {
  constructor(message,code='BRIDGE_UNAVAILABLE',status=503) {
    super(message);
    this.code=code;
    this.status=status;
  }
}
export const isCanonicalBridgeEnabled=() =>
  import.meta.env.VITE_SARAF_CANONICAL_BRIDGE_ENABLED==='true';

const ERRORS=Object.freeze({
  INVALID_TELEGRAM_AUTH:'مدت اعتبار ورود تلگرام پایان یافته است؛ Mini App را دوباره از ربات اصلی باز کنید.',
  SERVER_NOT_CONFIGURED:'اتصال امن Supabase هنوز پیکربندی نشده است.',
  DATABASE_UNAVAILABLE:'دیتابیس صراف در دسترس نیست؛ لطفاً بعداً دوباره امتحان کنید.',
  ACTION_DISABLED:'این خدمت هنوز برای کاربران فعال نیست.',
  ORIGIN_NOT_ALLOWED:'آدرس Mini App از طرف سرور تأیید نشده است.',
  RATE_LIMIT:'لطفاً پس از یک دقیقه دوباره امتحان کنید.',
  RATING_NOT_ALLOWED:'این سفارش قابل امتیازدهی نیست یا قبلاً امتیاز داده‌اید.',
  INVALID_INPUT:'معلومات واردشده معتبر نیست.',
});

export async function canonicalCall(action,input={}) {
  if(!ALLOWED_ACTIONS.has(action))
    throw new CanonicalBridgeError('این عملیات در Supabase فعال نیست.','ACTION_DISABLED',403);
  if(!isCanonicalBridgeEnabled())
    throw new CanonicalBridgeError(
      'اتصال سوابق واقعی صراف به Supabase هنوز فعال نشده است؛ هیچ معلومات آزمایشی نمایش داده نمی‌شود.',
      'BRIDGE_DISABLED',503);
  const initData=getInitData();
  if(!initData)throw new CanonicalBridgeError('برنامه را از ربات اصلی تلگرام باز کنید.','INVALID_TELEGRAM_AUTH',401);
  if(typeof window==='undefined'||typeof window.fetch!=='function')
    throw new CanonicalBridgeError('محیط برنامه معتبر نیست.');
  const ctrl=new AbortController();
  const timer=window.setTimeout(()=>ctrl.abort(),18000);
  try{
    const response=await window.fetch(EDGE_URL,{
      method:'POST',
      headers:{'Content-Type':'application/json','X-Telegram-Init-Data':initData},
      body:JSON.stringify({action,input}),
      mode:'cors',credentials:'omit',cache:'no-store',signal:ctrl.signal,
    });
    let result;
    try{result=await response.json();}catch {
      throw new CanonicalBridgeError('پاسخ نامعتبر از سرور Supabase.');
    }
    if(!response.ok||!result||Object.hasOwn(result,'error')){
      const code=typeof result?.error==='string'?result.error:'BRIDGE_UNAVAILABLE';
      throw new CanonicalBridgeError(ERRORS[code]||'درخواست Supabase انجام نشد.',code,response.status);
    }
    if(!Object.hasOwn(result,'data'))
      throw new CanonicalBridgeError('پاسخ Supabase ناقص است.');
    return result.data;
  }catch(error){
    if(error instanceof CanonicalBridgeError)throw error;
    if(error?.name==='AbortError')
      throw new CanonicalBridgeError('ارتباط با Supabase به پایان مهلت رسید.','TIMEOUT',504);
    throw new CanonicalBridgeError('ارتباط امن با Supabase برقرار نشد.','NETWORK',503);
  }finally{window.clearTimeout(timer);}
}
