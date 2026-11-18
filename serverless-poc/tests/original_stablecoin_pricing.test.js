import test from 'node:test';
import assert from 'node:assert/strict';
import {
 originalBuyPricing,originalSellPricing,originalRemittancePricing,
} from '../tgcloud/lib/legacy_stablecoin_pricing.js';

test('existing Saraf 50/30/20 model at 100 USD without separate 2% fee',()=>{
 const p=originalBuyPricing('100','66.1');
 assert.equal(p.market_margin_usd,2.5);
 assert.equal(p.supplier_profit_usd,1.25);
 assert.equal(p.saraf_profit_usd,.75);
 assert.equal(p.customer_discount_usd,.5);
 assert.equal(p.customer_payable_usd,102);
 assert.equal(p.total_afn,6742.2);
 assert.equal(p.effective_premium_percent,2);
});
test('existing minimum USD 2 market margin at 10,80,1000',()=>{
 assert.equal(originalBuyPricing('10','65').market_margin_usd,2);
 assert.equal(originalBuyPricing('80','65').market_margin_usd,2);
 assert.equal(originalBuyPricing('1000','65').market_margin_usd,25);
});
test('SELL uses the same market-margin 50/30/20 customer fee as BUY, not a 2% fee',()=>{
 for(const [amount,margin,fee] of [['10',2,1.6],['50',2,1.6],
   ['80',2,1.6],['100',2.5,2],['1000',25,20]]){
  const b=originalBuyPricing(amount,'65');
  const s=originalSellPricing(amount,'65');
  assert.equal(s.market_margin_usd,b.market_margin_usd);
  assert.equal(s.market_margin_usd,margin);
  assert.equal(s.supplier_profit_usd,b.supplier_profit_usd);
  assert.equal(s.saraf_profit_usd,b.saraf_profit_usd);
  assert.equal(s.customer_discount_usd,b.customer_discount_usd);
  assert.equal(s.fee_usd,fee);
  assert.ok(Math.abs(s.fee_usd-(b.customer_payable_usd-Number(amount)))<1e-8);
  assert.equal(s.fee_percent,0);
  assert.equal(s.pricing_model,'local_margin_share_50_30_20_sell');
  assert.equal(s.total_usd,Number(amount)-fee);
  assert.equal(s.receivable_usd,Number(amount)-fee);
  assert.equal(s.total_afn,s.base_afn-s.fee_afn);
  assert.equal(s.supplier_profit_afn+s.saraf_profit_afn,s.fee_afn);
 }
});
test('SELL at $50 has a $1.60 fixed market fee, unlike old 2% commission',()=>{
 const p=originalSellPricing('50','65.925');
 assert.equal(p.usd_rate,65.925);
 assert.equal(p.base_afn,3296.3);
 assert.equal(p.fee_usd,1.6);
 assert.equal(p.fee_afn,105.5);
 assert.equal(p.total_afn,3190.8);
 assert.equal(p.total_usd,48.4);
 assert.equal(p.supplier_profit_usd,1);
 assert.equal(p.saraf_profit_usd,.6);
 assert.equal(p.customer_discount_usd,.4);
 assert.equal(p.fee_percent,0);
});
test('USDC SELL and already-quoted old SELL orders keep their original no-fee economics',async()=>{
 const {originalSellPricingNoFee}=await import('../tgcloud/lib/legacy_stablecoin_pricing.js');
 const q=originalSellPricingNoFee('100','65');
 assert.equal(q.total_afn,6500);
 assert.equal(q.total_usd,100);
 assert.equal(q.receivable_usd,100);
 assert.equal(q.fee_percent,0);
 assert.equal(q.fee_usd,undefined);
});
test('SELL and BUY margin components match in Supabase and Telegram runtimes',async()=>{
 const edge=await import('../../supabase/functions/saraf-original-transactions/pricing.mjs');
 for(const [a,r] of [['10','65'],['50','65.925'],['100','65'],
  ['250.25','69.4'],['1000','65.75']]){
  assert.deepEqual(edge.originalSellPricing(a,r),originalSellPricing(a,r));
  assert.deepEqual(edge.originalBuyPricing(a,r),originalBuyPricing(a,r));
  const telegram=await import('../tgcloud/lib/legacy_stablecoin_pricing.js');
  assert.deepEqual(edge.originalSellPricingNoFee(a,r),
   telegram.originalSellPricingNoFee(a,r));
 }
 assert.throws(()=>originalSellPricing('NaN','66'));
 assert.throws(()=>originalSellPricing('-1','66'));
 assert.throws(()=>originalSellPricing('50','0'));
});
test('original remittance fee and AFN rounding',()=>{
 const p=originalRemittancePricing('75','65.25','0');
 assert.deepEqual(p,{
  crypto_amount:75,usd_rate:65.25,gross_afn:4893.8,
  fee_percent:0,fee_afn:0,payout_afn:4893.8,
 });
 const fees=originalRemittancePricing('100','65','1.25');
 assert.equal(fees.fee_afn,81.3);
 assert.equal(fees.payout_afn,6418.8);
});
test('invalid financial inputs never produce prices',()=>{
 assert.throws(()=>originalBuyPricing('NaN','66'));
 assert.throws(()=>originalBuyPricing('-1','66'));
 assert.throws(()=>originalBuyPricing('50','0'));
 assert.throws(()=>originalRemittancePricing('20','70','101'));
});
