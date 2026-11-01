import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildOriginalOrderReports} from '../../supabase/functions/saraf-original-transactions/original-order-reports.mjs';
const source=readFileSync(new URL('../../supabase/functions/saraf-original-transactions/index.ts',import.meta.url),'utf8');
const order={
 id:79,chat_id:123456789,username:'test',full_name:'مشتری آزمون',
 asset:'USDT',order_type:'buy',usdt_amount:100,usd_rate:70.2,
 total_afn:7140,total_usd:101.7,network:'TRC20',
 exchange_name:'Binance',wallet_address:'TexampleAddressForTestingOnly123',
 payment_method:'online',in_person_code:null,
 risk_level:'low',risk_reasons:null,source:'miniapp',
 saraf_profit_usd:0.51,saraf_profit_afn:35.802,
 supplier_profit_usd:0.85,supplier_profit_afn:59.67,
 supplier_payout_usd:100.85,supplier_payout_afn:7079.67,
 receipt_file_id:'private-receipt',
};
const profile={first_name:'مشتری',last_name:'آزمون',phone:'0700000000',
 kyc_status:'verified',successful_orders:2,trust_score:85};
test('buy customer report preserves original recipient, address, status and wording',()=>{
 const res=buildOriginalOrderReports(order,profile);
 for(const phrase of ['سفارش خرید USDT','USDT-00079','100.00 USDT','7,140.0',
   'آدرس دریافت','TexampleAddressForTestingOnly123','TRC20',
   'در انتظار بررسی','@SJDPLUS'])
  assert.ok(res.customer.includes(phrase),phrase);
 assert.ok(!res.customer.includes('تسویه با تأمین‌کننده'));
});
test('buy admin report preserves original supplier economics, trust, net profit and customer fees',()=>{
 const {admin}=buildOriginalOrderReports(order,profile);
 for(const phrase of ['سفارش خرید USDT','USDT-00079','مبلغ پرداختی مشتری',
   'کارمزد صراف از مشتری','سود خالص صراف','تسویه با تأمین‌کننده',
   'سود تأمین‌کننده','مبلغ کامل تأمین‌کننده','85/100','2 معامله موفق',
   'Binance','ریسک پایین','رسید پرداخت مشتری'])
  assert.ok(admin.includes(phrase),phrase);
 assert.match(admin,/\$0\.51/);
 assert.match(admin,/\$100\.85/);
 assert.match(admin,/\$1\.70/);
});
test('sell notification has actual persisted payout, proof, bank and in-person details',()=>{
 const sell={...order,order_type:'sell',total_afn:6960,total_usd:100,
   receive_method:'online',payment_method:null,
   tx_proof:'0xexampletransactionhash',bank_info:'HesabPay 00000',
   receipt_file_id:null};
 const messages=buildOriginalOrderReports(sell,profile);
 for(const phrase of ['سفارش فروش USDT','مبلغ قابل دریافت','6,960 افغانی',
   'روش دریافت','در انتظار بررسی'])assert.ok(messages.customer.includes(phrase),phrase);
 assert.match(messages.admin,/0xexampletransactionhash/);
 assert.match(messages.admin,/HesabPay 00000/);
});
test('user-input HTML is escaped and cannot inject Telegram formatting',()=>{
 const x=buildOriginalOrderReports({...order,exchange_name:'<b>fake</b>',
   username:'<script>'},profile);
 assert.ok(!x.admin.includes('<script>'));
 assert.ok(x.admin.includes('&lt;script&gt;'));
 assert.ok(x.customer.includes('&lt;b&gt;fake&lt;/b&gt;'));
});
test('server produces official notifications after canonical financial RPC with no repricing or new ledger',()=>{
 assert.match(source,/buildOriginalOrderReports\(saved\.data,profile\.data\|\|\{\}\)/);
 assert.match(source,/if\(!item\?\.duplicate\)/);
 assert.match(source,/notifyAdmin\(messages\.admin,true\)/);
 assert.match(source,/notifyCustomer\(user\.id,messages\.customer,true\)/);
 assert.match(source,/db\.rpc\('saraf_original_submit_usdt_order'/);
 assert.doesNotMatch(source,/db\.from\('new_usdt_orders'/);
});
test('issued card is owner signed and independent of consumed 10-minute quote',()=>{
 const idx=source.indexOf("if(action==='card.issued')");
 const part=source.slice(idx,source.indexOf("if(action==='card.preview')",idx));
 assert.ok(idx>0);
 assert.match(part,/db\.from\('usdt_orders'\)/);
 assert.match(part,/\.eq\('id',orderId\)\.eq\('chat_id',user\.id\)/);
 assert.match(part,/order\.usd_rate/);
 assert.doesNotMatch(part,/db\.from\('usdt_quotes'\)/);
});
