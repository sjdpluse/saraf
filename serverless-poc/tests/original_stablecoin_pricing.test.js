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
test('sell uses the original unmodified Saraf buy rate',()=>{
 const p=originalSellPricing('50','65.925');
 assert.equal(p.total_afn,3296.3);
 assert.equal(p.total_usd,50);
 assert.equal(p.receivable_usd,50);
 assert.equal(p.usd_rate,65.925);
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
