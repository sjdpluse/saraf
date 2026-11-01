// Original Saraf: post-commit, no-click order-card dispatch.
// A short-lived local recovery queue is only an availability aid; Supabase
// re-verifies Telegram HMAC and canonical order ownership on every attempt.
// NO new financial order, quote, fee, payment, or status mutation occurs here.
const STORAGE='saraf_original_card_post_commit_v1';
const MAX_AGE=7*86400000;
const inflight=new Map();
const valid=row=>row&&Number.isSafeInteger(Number(row.order_id))&&row.order_id>0&&
  ['buy','sell'].includes(row.action)&&['USDT','USDC'].includes(row.asset)&&
  Number.isFinite(Number(row.amount))&&Number(row.amount)>0&&
  String(row.order_code)===row.asset+'-'+String(row.order_id).padStart(5,'0');
const load=()=>{
  try{
    const data=JSON.parse(window.localStorage.getItem(STORAGE)||'[]');
    return Array.isArray(data)?data.filter(row=>valid(row)&&
      Date.now()-Number(row.created_at||0)<MAX_AGE).slice(-12):[];
  }catch{return [];}
};
const save=rows=>{
  try{window.localStorage.setItem(STORAGE,JSON.stringify(rows.slice(-12)));}
  catch{/* Private browser or disabled storage. Immediate delivery still runs. */}
};
export function rememberOriginalOrderCard(order){
  if(!valid(order))return false;
  const entries=load().filter(row=>row.order_id!==order.order_id);
  entries.push({
    order_id:Number(order.order_id),order_code:String(order.order_code),
    action:order.action,asset:order.asset,amount:Number(order.amount),
    created_at:Date.now(),attempts:0,state:'pending',
  });
  save(entries);
  return true;
}
const update=(id,patch,remove=false)=>{
  const items=load(),index=items.findIndex(row=>row.order_id===id);
  if(index<0)return;
  if(remove)items.splice(index,1);
  else items[index]={...items[index],...patch};
  save(items);
};
const isComplete=result=>result?.customer==='sent'&&
  Array.isArray(result?.admins)&&result.admins.length>0&&
  result.admins.every(r=>r.state==='sent');
export async function dispatchOriginalOrderCard(order,send){
  if(!valid(order))throw Error('INVALID_COMMITTED_ORDER_CARD');
  const id=Number(order.order_id);
  if(inflight.has(id))return inflight.get(id);
  const task=(async()=>{
    const found=load().find(row=>row.order_id===id);
    try{
      const result=await send(order);
      if(isComplete(result)){update(id,{},true);return {state:'sent',result};}
      const needsReview=result?.requires_manual_review||
        result?.customer==='uncertain'||result?.customer==='sending'||
        result?.admins?.some(r=>['uncertain','sending'].includes(r.state));
      const state=needsReview?'uncertain':'failed';
      update(id,{state,attempts:(found?.attempts||0)+1});
      return {state,result};
    }catch(error){
      update(id,{state:'failed',attempts:(found?.attempts||0)+1});
      throw error;
    }
  })().finally(()=>inflight.delete(id));
  inflight.set(id,task);
  return task;
}
export async function resumeOriginalOrderCards(send,onResult=()=>{}){
  for(const item of load()){
    // Never blindly resend an uncertain Telegram sendPhoto response. Outbox
    // has its own exactly-once guard, but this state requires operator review.
    if(item.state==='uncertain'||item.attempts>=3)continue;
    try{const result=await dispatchOriginalOrderCard(item,send);onResult(item,result);}
    catch{/* The next app-opening may retry a safe, failed dispatch. */}
  }
}
