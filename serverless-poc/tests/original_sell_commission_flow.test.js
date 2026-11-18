import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {originalSellPricing} from '../tgcloud/lib/legacy_stablecoin_pricing.js';
import {buildOriginalOrderReports} from '../../supabase/functions/saraf-original-transactions/original-order-reports.mjs';

const source=path=>readFileSync(new URL('../../'+path,import.meta.url),'utf8');
const fakeOrder={
 id:123,chat_id:12345678,username:'owner',asset:'USDT',order_type:'sell',
 usdt_amount:100,usd_rate:65,total_afn:6370,total_usd:98,fee_percent:2,
 saraf_profit_usd:2,saraf_profit_afn:130,
 wallet_address:'TRC20-TEST-ONLY',exchange_name:'Source wallet',network:'TRC20',
 receive_method:'online',bank_info:'Account (test)',status:'pending'
};
const profile={first_name:'Test',last_name:'Customer',phone:'000000',
 kyc_status:'pending',successful_orders:0,trust_score:0};
test('sell customer/admin texts show only persisted commission and net payout',()=>{
 const {customer,admin}=buildOriginalOrderReports(fakeOrder,profile);
 assert.match(customer,/کمیسیون صراف \(2\.00٪\): \$2\.00 \| 130\.0 افغانی/);
 assert.match(customer,/مبلغ قبل از کمیسیون: 6,500\.0 افغانی/);
 assert.match(customer,/مبلغ قابل دریافت پس از کمیسیون: <b>6,370\.0 افغانی<\/b>/);
 assert.match(admin,/مبلغ قابل پرداخت به مشتری: <b>6,370\.0 افغانی<\/b>/);
 assert.match(admin,/کمیسیون صراف: \$2\.00 \| 130\.0 افغانی/);
 const prior={...fakeOrder,id:124,total_afn:6500,total_usd:100,
  fee_percent:0,saraf_profit_usd:null,saraf_profit_afn:null};
 const existing=buildOriginalOrderReports(prior,profile);
 assert.doesNotMatch(existing.customer,/کمیسیون صراف/);
 assert.doesNotMatch(existing.admin,/کمیسیون صراف/);
});
test('server writes SELL net payout and profit atomically through existing quote/order ledger',()=>{
 const index=source('supabase/functions/saraf-original-transactions/index.ts');
 const rpc=source('supabase/sql/saraf_original_usdt_order_rpc_STAGED.sql');
 const api=source('webapp/src/lib/api.js');
 const review=source('webapp/src/components/OrderReview.jsx');
 const sell=source('webapp/src/pages/Sell.jsx');
 assert.match(index,/sellCommissionPercent\(\)/);
 assert.match(index,/SARAF_ORIGINAL_SELL_COMMISSION_PERCENT/);
 assert.match(index,/type==='USDT'\?sellCommissionPercent\(\):'0'/);
 assert.match(index,/originalSellPricing\(String\(a\),String\(usdRate\),/);
 assert.match(index,/fee_percent:pricing\.fee_percent\?\?0/);
 assert.match(index,/values\.saraf_profit_usd=pricing\.saraf_profit_usd/);
 assert.match(index,/values\.saraf_profit_afn=pricing\.saraf_profit_afn/);
 assert.match(index,/input\.pricing_version!=='sell_commission_v1'/);
 assert.match(index,/SELL_COMMISSION_UPDATE_REQUIRED/);
 assert.doesNotMatch(index,/input\.fee_percent/);
 assert.match(rpc,/q\.fee_percent,q\.total_afn,q\.total_usd/);
 assert.match(rpc,/q\.saraf_profit_afn/);
 assert.match(api,/pricing_version: "sell_commission_v1"/);
 assert.match(sell,/مبلغ فروش قبل از کمیسیون/);
 assert.match(sell,/کمیسیون صراف/);
 assert.match(review,/sellFeeUsd = Number\(quote\?\.fee_usd/);
 assert.match(review,/sellFeeAfn = Number\(quote\?\.fee_afn/);
 const png=source('webapp/src/lib/originalOrderCardPng.js');
 assert.match(png,/مبلغ پس از کمیسیون/);
 const card=source('supabase/functions/saraf-original-order-card/index.ts');
 assert.match(card,/sellCommission/);
 assert.match(card,/saraf_profit_afn/);
});
test('SELL fee is per-quote, never reapplied to historic immutable orders',()=>{
 const fresh=originalSellPricing('100','65','2');
 const older=originalSellPricing('100','65','0');
 assert.equal(fresh.total_afn,6370);
 assert.equal(older.total_afn,6500);
 assert.equal(fresh.base_afn-older.base_afn,0);
 assert.equal(fresh.base_afn-fresh.fee_afn,fresh.total_afn);
});
