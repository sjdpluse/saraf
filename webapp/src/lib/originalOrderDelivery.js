// Order-card receipt delivery after the original financial RPC has committed.
// The private Edge function checks signed Telegram identity and reloads the
// canonical usdt_orders row. Browser amounts/chat IDs are never authoritative.
import {getInitData} from './telegram';
const URL='https://cvernmhpnsgdtegvblyc.supabase.co/functions/v1/saraf-original-order-card';

export async function sendOriginalOrderCard(orderId,blob){
 if(!Number.isSafeInteger(Number(orderId))||Number(orderId)<=0)
  throw Error('شماره سفارش معتبر نیست.');
 if(!(blob instanceof Blob)||blob.type!=='image/png'||
    !blob.size||blob.size>5*1024*1024)
  throw Error('تصویر کارت مشتری معتبر نیست.');
 const initData=getInitData();
 if(!initData)throw Error('Mini App را از ربات اصلی صراف باز کنید.');
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),25000);
 const body=new FormData();
 body.append('order_id',String(orderId));
 body.append('card',blob,'saraf-order.png');
 try{
  const res=await fetch(URL,{
   method:'POST',mode:'cors',credentials:'omit',cache:'no-store',
   headers:{'X-Telegram-Init-Data':initData},body,signal:controller.signal,
  });
  const json=await res.json().catch(()=>null);
  if(!res.ok||!json||json.error)
   throw Error('ارسال کارت سفارش ممکن نشد؛ می‌توانید دوباره امتحان کنید.');
  return json;
 }finally{clearTimeout(timeout);}
}
