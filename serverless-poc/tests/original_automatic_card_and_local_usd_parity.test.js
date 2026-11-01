import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const state=new Map();
globalThis.window={localStorage:{
 getItem:key=>state.get(key)||null,
 setItem:(key,value)=>state.set(key,String(value)),
}};
const {rememberOriginalOrderCard,dispatchOriginalOrderCard,resumeOriginalOrderCards}=
 await import('../../webapp/src/lib/originalAutoOrderCard.js');
const job=id=>({order_id:id,order_code:'USDT-'+String(id).padStart(5,'0'),
 action:'buy',asset:'USDT',amount:90});
const good={customer:'sent',admins:[{state:'sent'}]};
test('automatically dispatched committed order sends customer/admin exactly once',async()=>{
 const r=job(901);
 assert.equal(rememberOriginalOrderCard(r),true);
 let count=0;
 const result=await dispatchOriginalOrderCard(r,async()=>{count++;return good;});
 assert.equal(result.state,'sent');
 assert.equal(count,1);
 await resumeOriginalOrderCards(async()=>{throw Error('must not retry already sent')});
 assert.equal(JSON.parse(state.values().next().value).length,0);
});
test('app opening retries failed photo without resubmitting orders or user button',async()=>{
 const r=job(902);rememberOriginalOrderCard(r);
 await assert.rejects(()=>dispatchOriginalOrderCard(r,async()=>{throw Error('network interruption')}));
 let count=0;
 await resumeOriginalOrderCards(async row=>{
  assert.equal(row.order_id,902);
  count++;return good;
 });
 assert.equal(count,1);
 assert.equal(JSON.parse(state.values().next().value).length,0);
});
test('uncertain Telegram photo outcome is not blindly retried',async()=>{
 const r=job(903);rememberOriginalOrderCard(r);
 const result=await dispatchOriginalOrderCard(r,async()=>({
  customer:'uncertain',admins:[{state:'sent'}],requires_manual_review:true,
 }));
 assert.equal(result.state,'uncertain');
 let count=0;
 await resumeOriginalOrderCards(async()=>{count++;return good;});
 assert.equal(count,0);
});
test('simultaneous auto event and user final step share one in-flight dispatch',async()=>{
 const r=job(904);rememberOriginalOrderCard(r);
 let count=0;
 const send=async()=>{count++;await new Promise(done=>setTimeout(done,20));return good;};
 const [a,b]=await Promise.all([
  dispatchOriginalOrderCard(r,send),dispatchOriginalOrderCard(r,send),
 ]);
 assert.equal(count,1);assert.equal(a.state,'sent');assert.equal(b.state,'sent');
});
test('auto dispatch is immediately awaited after original submit in both original screens',()=>{
 for(const path of ['Buy.jsx','Sell.jsx']){
  const s=readFileSync(new URL('../../webapp/src/pages/'+path,import.meta.url),'utf8');
  assert.match(s,/rememberOriginalOrderCard\(\{/);
  assert.match(s,/await deliverCard\(res\.order_id,res\.order_code\)/);
  assert.ok(s.indexOf('rememberOriginalOrderCard({')<s.indexOf('await deliverCard(res.order_id,res.order_code)'));
  assert.match(s,/dispatchOriginalOrderCard\(/);
 }
 const app=readFileSync(new URL('../../webapp/src/App.jsx',import.meta.url),'utf8');
 assert.match(app,/resumeOriginalOrderCards\(/);
 assert.match(app,/addEventListener\('online',retry\)/);
 assert.match(app,/addEventListener\('visibilitychange',whenVisible\)/);
});
test('original Python and port use the same BUY local sell and SELL local-spread buy; no global mid-market repricing',()=>{
 const python=readFileSync(new URL('../../services/usdt_service.py',import.meta.url),'utf8');
 const edge=readFileSync(new URL('../../supabase/functions/saraf-original-transactions/index.ts',import.meta.url),'utf8');
 assert.match(python,/local_sell\s*=\s*\(quote\.get\("local"\)/);
 assert.match(python,/usd_buy_rate:\s*Decimal\s*=\s*D\(quote\["saraf_quote"\]\["buy"\]\)/);
 assert.match(edge,/const localSell=rate\.local\?\.sell/);
 assert.match(edge,/\?localSell\|\|rate\.saraf_quote\.sell:rate\.saraf_quote\.buy/);
 assert.match(edge,/selectOriginalBasis\('usd',references,local,pct\)/);
 assert.match(edge,/\.rpc\('saraf_original_submit_usdt_order'/);
});
