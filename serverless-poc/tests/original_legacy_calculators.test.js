import test from 'node:test';
import assert from 'node:assert/strict';
import {
 originalCurrencyCalculation, originalMetalCalculation, metalBreakdown,
 GRAMS_PER_TROY_OUNCE, GRAMS_PER_METHQAL,
} from '../tgcloud/lib/legacy_calculators.js';

// Fixtures reproduce the original main:services/rate_engine.py result shape.
test('currency calculator uses original local and Saraf BUY/SELL sides',()=>{
 const q={local:{market_label:'سرای شهزاده (کابل)',buy:65.90,sell:65.95},
  saraf_quote:{buy:65.60,sell:66.25}};
 const result=originalCurrencyCalculation(100,q);
 assert.deepEqual(result,{
  local:{sell_afn:6590,buy_afn:6595},
  local_market_label:'سرای شهزاده (کابل)',
  saraf:{sell_afn:6560,buy_afn:6625},
 });
 // This would incorrectly be 7,110 AFN if using the global mid-market.
 assert.notEqual(result.saraf.sell_afn,7110);
});

test('currency calculator works when local-market scraping has failed',()=>{
 const q={local:null,saraf_quote:{buy:71.13,sell:71.49}};
 const result=originalCurrencyCalculation(5,q);
 assert.equal(result.local,null);
 assert.equal(result.saraf.sell_afn,355.6);
 assert.equal(result.saraf.buy_afn,357.4);
 assert.throws(()=>originalCurrencyCalculation(0,q),/INVALID_AMOUNT/);
 assert.throws(()=>originalCurrencyCalculation(1,{}),/SARAF_RATE_UNAVAILABLE/);
});

test('gold breakdown and transaction rounding follow original Python service',()=>{
 const price=2400,usdRate=70,grams=4.6;
 const rows=metalBreakdown('XAU',price,usdRate);
 assert.deepEqual(rows.map(x=>x.karat),[24,22,21,18]);
 const gold24=rows[0];
 assert.equal(gold24.afnGram,Number((price*usdRate/GRAMS_PER_TROY_OUNCE).toFixed(1)));
 assert.equal(gold24.usdGram,Number((price/GRAMS_PER_TROY_OUNCE).toFixed(2)));
 assert.equal(gold24.afnMethqal,Number((price*usdRate/GRAMS_PER_TROY_OUNCE*GRAMS_PER_METHQAL).toFixed(1)));
 const buy=originalMetalCalculation('XAU',rows,18,grams,'buy');
 const sell=originalMetalCalculation('XAU',rows,18,grams,'sell');
 const gramsBase=rows.find(x=>x.karat===18).afnGram*grams;
 assert.equal(buy.base_afn,Number(gramsBase.toFixed(1)));
 assert.equal(buy.final_afn,Number((gramsBase*1.05).toFixed(1)));
 assert.equal(sell.final_afn,Number((gramsBase*.98).toFixed(1)));
 assert.equal(buy.adjustment_label,'اجرت ساخت');
 assert.equal(sell.adjustment_label,'کسر صرافی');
});

test('silver uses four decimal USD per gram like silver_service.py',()=>{
 const price=34.5,usdRate=71.8,grams=12.5;
 const silver=metalBreakdown('XAG',price,usdRate);
 assert.equal(silver.length,1);
 assert.equal(silver[0].karat,24);
 assert.equal(silver[0].usdGram,Number((price/GRAMS_PER_TROY_OUNCE).toFixed(4)));
 assert.notEqual(silver[0].usdGram,Number((price/GRAMS_PER_TROY_OUNCE).toFixed(2)));
 const buy=originalMetalCalculation('XAG',silver,24,grams,'buy');
 assert.equal(buy.base_usd,Number((silver[0].usdGram*grams).toFixed(2)));
 assert.equal(buy.final_usd,Number((silver[0].usdGram*grams*1.05).toFixed(2)));
 assert.throws(()=>originalMetalCalculation('XAG',silver,18,grams,'buy'),/INVALID_METAL/);
 assert.throws(()=>metalBreakdown('XAU',0,usdRate),/INVALID_METAL_PRICE/);
});
