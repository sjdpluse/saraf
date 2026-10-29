// ORIGINAL @sarafiaf_bot canonical financial backend adapter.
// Deliberately OFF until separately reviewed Supabase migration, quote supplier,
// KYC policy, chain watcher, payout controls, and operator secrets are live.
// This adapter never falls back to Railway or a second SQLite ledger.
import { getInitData } from './telegram';
const ORIGIN='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-finance';
const ACTIONS=new Set(['capabilities','quote.issue','order.submit',
  'remittance.quote','remittance.submit','remittance.claimTx']);
export const isFinanceUiEnabled=() =>
  import.meta.env.VITE_SARAF_FINANCE_UI_ENABLED==='true';
export class FinancialActionError extends Error {
  constructor(code,status=503){
    super(code==='FINANCE_DISABLED'
      ? 'ثبت معاملات مالی هنوز فعال نشده است.'
      : 'اجرای عملیات مالی در حال حاضر امکان‌پذیر نیست.');
    this.code=code;
    this.status=status;
  }
}
export async function financeCall(action,input={}) {
  if(!ACTIONS.has(action))throw new FinancialActionError('ACTION_DISABLED',403);
  if(!isFinanceUiEnabled())throw new FinancialActionError('FINANCE_DISABLED');
  const initData=getInitData();
  if(!initData)throw new FinancialActionError('UNAUTHORIZED',401);
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),16000);
  try{
    const response=await fetch(ORIGIN,{
      method:'POST',cache:'no-store',credentials:'omit',mode:'cors',
      headers:{'Content-Type':'application/json','X-Telegram-Init-Data':initData},
      body:JSON.stringify({action,input}),
      signal:controller.signal,
    });
    let value;
    try{value=await response.json();}catch{
      throw new FinancialActionError('INVALID_RESPONSE');
    }
    if(!response.ok||value?.error)throw new FinancialActionError(
      value?.error||'FINANCE_UNAVAILABLE',response.status);
    if(!Object.hasOwn(value,'data'))throw new FinancialActionError('INVALID_RESPONSE');
    return value.data;
  }catch(error){
    if(error instanceof FinancialActionError)throw error;
    throw new FinancialActionError('NETWORK_ERROR');
  }finally{clearTimeout(timer);}
}
