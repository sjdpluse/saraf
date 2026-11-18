import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 originalBuyPricing,originalSellPricing,originalSellPricingNoFee,
} from '../tgcloud/lib/legacy_stablecoin_pricing.js';
import {buildOriginalOrderReports} from
 '../../supabase/functions/saraf-original-transactions/original-order-reports.mjs';

const source=path=>readFileSync(new URL('../../'+path,import.meta.url),'utf8');
const profile={first_name:'Test',last_name:'Customer',phone:'000000',
 kyc_status:'pending',successful_orders:0,trust_score:0};
const testOrder={
 id:123,chat_id:12345678,username:'owner',asset:'USDT',order_type:'sell',
 usdt_amount:100,usd_rate:65,total_afn:6370,total_usd:98,
 pricing_model:'local_margin_share_50_30_20_sell',
 fee_percent:0,supplier_profit_usd:1.25,supplier_profit_afn:81.3,
 saraf_profit_usd:.75,saraf_profit_afn:48.7,
 wallet_address:'TRC20-TEST-ONLY',exchange_name:'Source wallet',network:'TRC20',
 receive_method:'online',bank_info:'Account (test)',status:'pending'
};

test('new USDT SELL customer/admin reports disclose flat fee and net without a percent',()=>{
 const {customer,admin}=buildOriginalOrderReports(testOrder,profile);
 assert.match(customer,/مبلغ پایه: 6,500\.0 افغانی/);
 assert.match(customer,/کارمزد صراف: \$2\.00 \| 130\.0 افغانی/);
 assert.match(customer,/مبلغ نهایی قابل دریافت: <b>6,370\.0 افغانی<\/b>/);
 assert.doesNotMatch(customer,/٪/);
 assert.match(admin,/مبلغ قابل پرداخت به مشتری: <b>6,370\.0 افغانی<\/b>/);
 assert.match(admin,/کارمزد صراف: \$2\.00 \| 130\.0 افغانی/);
 assert.match(admin,/سهم تأمین‌کننده: \$1\.25 \| 81\.3 افغانی/);
 assert.match(admin,/سود خالص صراف: \$0\.75 \| 48\.7 افغانی/);
 assert.doesNotMatch(admin,/کمیسیون صراف.*٪/);
});

test('old 2%-quoted SELL remains unchanged, no-fee USDC history stays no-fee',()=>{
 const legacy={...testOrder,id:124,pricing_model:'sell_saraf_commission_v1',
  fee_percent:2,supplier_profit_usd:null,supplier_profit_afn:null,
  saraf_profit_usd:2,saraf_profit_afn:130};
 const old=buildOriginalOrderReports(legacy,profile);
 assert.match(old.customer,/مبلغ قبل از کمیسیون: 6,500\.0 افغانی/);
 assert.match(old.customer,/کمیسیون صراف \(2\.00٪\)/);
 assert.match(old.customer,/مبلغ قابل دریافت پس از کمیسیون: <b>6,370\.0 افغانی<\/b>/);
 const noFee={...testOrder,id:125,asset:'USDC',pricing_model:null,total_afn:6500,
  total_usd:100,fee_percent:0,supplier_profit_afn:null,saraf_profit_afn:null,
  supplier_profit_usd:null,saraf_profit_usd:null};
 const historic=buildOriginalOrderReports(noFee,profile);
 assert.doesNotMatch(historic.customer,/کارمزد صراف|کمیسیون صراف/);
 assert.doesNotMatch(historic.admin,/کارمزد صراف|کمیسیون صراف/);
 assert.equal(originalSellPricingNoFee('100','65').total_afn,6500);
});
test('server owns market-margin quote; finance RPC persists agreed immutable USDT payout',()=>{
 const index=source('supabase/functions/saraf-original-transactions/index.ts');
 const rpc=source('supabase/sql/saraf_original_usdt_order_rpc_STAGED.sql');
 const api=source('webapp/src/lib/api.js');
 const sell=source('webapp/src/pages/Sell.jsx');
 const review=source('webapp/src/components/OrderReview.jsx');
 assert.match(index,/input\.pricing_version!=='sell_market_margin_v2'/);
 assert.match(index,/type==='USDT'\?originalSellPricing/);
 assert.match(index,/originalSellPricingNoFee\(String\(a\),String\(usdRate\)\)/);
 assert.match(index,/values\.pricing_model=pricing\.pricing_model/);
 assert.match(index,/supplier_profit_usd/);
 assert.match(index,/saraf_profit_afn/);
 assert.doesNotMatch(index,/SARAF_ORIGINAL_SELL_COMMISSION_PERCENT/);
 assert.doesNotMatch(index,/sellCommissionPercent/);
 assert.doesNotMatch(index,/input\.fee_percent/);
 assert.match(rpc,/q\.fee_percent,q\.total_afn,q\.total_usd/);
 assert.match(rpc,/q\.saraf_profit_afn/);
 assert.match(api,/pricing_version: "sell_market_margin_v2"/);
 assert.match(sell,/کارمزد صراف/);
 assert.doesNotMatch(sell,/کمیسیون صراف \(\{Number\(quote\.fee_percent/);
 assert.match(review,/sellFeeUsd = Number\(quote\?\.fee_usd/);
 assert.match(review,/sellFeeAfn = Number\(quote\?\.fee_afn/);
 assert.match(review,/<DetailRow label="کارمزد صراف"/);
 const png=source('webapp/src/lib/originalOrderCardPng.js');
 assert.match(png,/مبلغ پس از کارمزد/);
 const card=source('supabase/functions/saraf-original-order-card/index.ts');
 assert.match(card,/marketMarginSell/);
 assert.match(card,/supplier_profit_afn/);
});
test('BUY vs SELL fees match while reverse settlement leaves full USDT amount untouched',()=>{
 for(const amount of [10,20,50,80,100,150,1000]){
  const buy=originalBuyPricing(String(amount),'65');
  const sell=originalSellPricing(String(amount),'65');
  const fee=buy.customer_payable_usd-amount;
  assert.ok(Math.abs(sell.fee_usd-fee)<1e-8);
  assert.equal(sell.total_usd,amount-fee);
  assert.equal(sell.amount,amount);
  assert.equal(sell.fee_percent,0);
  assert.equal(sell.base_afn-sell.fee_afn,sell.total_afn);
 }
});
