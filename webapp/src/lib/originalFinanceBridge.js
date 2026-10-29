// ORIGINAL Saraf Mini App quote / buy / sell API transport.
// Matches main:api.py + services/usdt_api_guard.py request/return contracts.
// The same canonical Supabase and ORIGINAL Telegram identity are used.
// OFF by default; no Railway fallback and no alternate financial ledger.
import {getInitData} from './telegram';
const ENDPOINT='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-transactions';
export class OriginalFinanceBridgeError extends Error {
 constructor(message,code='NOT_MIGRATED',status=503){
  super(message);this.code=code;this.status=status;
 }
}
const ALLOWED=new Set(['stablecoins.config','payment.info','quote','order.buy','order.sell',
 'remittances.config','remittances.quote','remittances.create','remittances.tx']);
export const originalFinanceBridgeEnabled=()=>
 import.meta.env.VITE_SARAF_ORIGINAL_TRANSACTIONS_ENABLED==='true';
export async function originalFinanceCall(action,input={}){
 if(!ALLOWED.has(action))throw new OriginalFinanceBridgeError(
  'این عملیات هنوز به سرور اصلی صراف منتقل نشده است.');
 if(!originalFinanceBridgeEnabled())throw new OriginalFinanceBridgeError(
  'خدمات مالی هنوز در سرور جدید صراف فعال نشده‌اند؛ سفارش جدید ثبت نشد.');
 const initData=getInitData();
 if(!initData)throw new OriginalFinanceBridgeError(
  'لطفاً Mini App را از ربات اصلی باز کنید.','INVALID_TELEGRAM_AUTH',401);
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),18000);
 try{
  const response=await fetch(ENDPOINT,{
   method:'POST',mode:'cors',credentials:'omit',cache:'no-store',
   headers:{'Content-Type':'application/json',
    'X-Telegram-Init-Data':initData},
   body:JSON.stringify({action,input}),signal:controller.signal,
  });
  const json=await response.json();
  if(!response.ok||json?.error)throw new OriginalFinanceBridgeError(
    'درخواست مالی تأیید نشد. لطفاً معلومات را بررسی کنید.',
    json?.error||'FINANCIAL_API_UNAVAILABLE',response.status);
  return json;
 }catch(error){
  if(error instanceof OriginalFinanceBridgeError)throw error;
  throw new OriginalFinanceBridgeError(
   'اتصال امن با سرور صراف برقرار نشد. سفارش جدید ثبت نشد.',
   error?.name==='AbortError'?'TIMEOUT':'NETWORK',503);
 }finally{clearTimeout(timeout);}
}
