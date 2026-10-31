import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {signOriginalMarketJob,verifyOriginalMarketJob} from
 '../../supabase/functions/saraf-original-market-snapshots/market-auth.mjs';
import {fetchOriginalCurrencyRates,fetchOriginalMetal,goldSnapshot,
 silverSnapshot,parseOriginalLocalRates} from
 '../../supabase/functions/saraf-original-market-snapshots/markets.mjs';
const token='123456789:fake_original_bot_token_long_enough_123456789';
const other='123456789:another_fake_original_bot_token_xyz_123456789';
const t=1770000000000;
test('private market history cron HMAC authorizes correct ORIGINAL bot action for only 45s',async()=>{
 const stamp=String(Math.floor(t/1000));
 const sig=await signOriginalMarketJob(token,'reference',stamp);
 assert.equal(await verifyOriginalMarketJob(token,'reference',stamp,sig,t),true);
 assert.equal(await verifyOriginalMarketJob(token,'local',stamp,sig,t),false);
 assert.equal(await verifyOriginalMarketJob(other,'reference',stamp,sig,t),false);
 assert.equal(await verifyOriginalMarketJob(token,'reference',stamp,sig,t+46000),false);
 assert.equal(await verifyOriginalMarketJob(token,'reference',stamp,'0'.repeat(64),t),false);
 assert.equal(await verifyOriginalMarketJob(token,'order.buy',stamp,sig,t),false);
});
test('original FX gold and silver history rounding preserves Python numeric formula',async()=>{
 const rates=await fetchOriginalCurrencyRates(async()=>({ok:true,json:async()=>({
  afn:{usd:1/70,eur:1/80,pkr:1/0.26,irr:1/0.002,gbp:1/95},
 })}));
 assert.equal(rates.usd,70);
 assert.equal(rates.eur,80);
 assert.equal(rates.pkr,.26);
 const gold=goldSnapshot(3100,70);
 const silver=silverSnapshot(32,70);
 assert.equal(gold.price_usd_per_oz,3100);
 assert.equal(gold.afn_per_gram_24k,Math.round(3100*70/31.1034768*10)/10);
 assert.equal(silver.afn_per_gram,Math.round(32*70/31.1034768*10)/10);
 const m=await fetchOriginalMetal('XAU',async()=>({ok:true,json:async()=>({price:3100})}));
 assert.equal(m,3100);
});
test('historic local Sarai Shahzada markets preserve original thousand-unit normalization',()=>{
 const html=`<table>
 <tr><td><a href="/exchange-rates/sarai-shahzada/USD-AFN">USD</a></td>
 <td>70.50</td><td>70.80</td></tr>
 <tr><td><a href="/exchange-rates/khorasan-market/PKR-AFN">هزار کلدار</a></td>
 <td>4000</td><td>4200</td></tr>
 </table>`;
 const m=parseOriginalLocalRates(html);
 assert.deepEqual(m.sarai_shahzada.usd,{buy:70.5,sell:70.8});
 assert.deepEqual(m.khorasan_market.pkr,{buy:4,sell:4.2});
});
test('original market worker cannot access user orders, balances, payment media, or admin approvals',()=>{
 const worker=readFileSync(new URL(
  '../../supabase/functions/saraf-original-market-snapshots/index.ts',import.meta.url),'utf8');
 assert.match(worker,/verifyOriginalMarketJob/);
 for(const table of ['currency_history','gold_history','silver_history','local_market_history'])
  assert.ok(worker.includes("'"+table+"'"),table+' history missing');
 for(const mutation of ['usdt_orders','remittance_orders','user_profiles',
  'order.confirm','order.buy','broadcast.create','kyc.review','payments'])
  assert.ok(!worker.includes("'"+mutation+"'"),'unsafe mutation '+mutation);
 assert.match(worker,/if\(!valid\)return json\(401/);
});
