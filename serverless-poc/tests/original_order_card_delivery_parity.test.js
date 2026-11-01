import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const read=p=>readFileSync(new URL('../../'+p,import.meta.url),'utf8');
const edge=read('supabase/functions/saraf-original-order-card/index.ts');
const admin=read('supabase/functions/saraf-original-admin/index.ts');
const bridge=read('webapp/src/lib/originalOrderDelivery.js');
const api=read('webapp/src/lib/api.js');
const buy=read('webapp/src/pages/Buy.jsx');
const sell=read('webapp/src/pages/Sell.jsx');
const card=read('webapp/src/lib/originalOrderCardPng.js');
const sql=read('supabase/sql/saraf_original_card_delivery_outbox_STAGED.sql');
test('new customer/admin photo transport requires signed Telegram HMAC and canonical order ownership',()=>{
 assert.match(edge,/verifyTelegramInitData\(/);
 assert.match(edge,/\.eq\('id',id\)\.eq\('chat_id',user\.id\)/);
 assert.match(edge,/db\.from\('usdt_orders'\)/);
 assert.match(edge,/db\.from\('user_profiles'\)/);
 assert.match(edge,/customer:customer\.state/);
 assert.match(edge,/sendPhoto/);
 assert.doesNotMatch(edge,/p_quote_id|saraf_original_submit_usdt_order|saraf_original_admin_finalize_order/);
 assert.doesNotMatch(edge,/\.upsert\(\{.*usdt_amount|\.update\(\{.*total_afn/);
});
test('customer/admin receipts use exactly persisted amounts and server-generated captions',()=>{
 assert.match(edge,/cash\(order\.usdt_amount\)/);
 assert.match(edge,/cash\(order\.total_afn\)/);
 assert.match(edge,/cash\(order\.usd_rate\)/);
 assert.match(edge,/تصویر توسط Mini App تولید شده/);
 assert.match(edge,/\['pending','confirmed','completed'\]/);
 assert.match(edge,/card_image_path/);
 assert.match(edge,/usdt-cards/);
 assert.match(edge,/MAX_BYTES=5\*1024\*1024/);
});
test('idempotent delivery outbox prevents repeat photo sends after success or uncertain Telegram response',()=>{
 assert.match(sql,/primary key \(order_id,recipient,chat_id\)/);
 assert.match(sql,/enable row level security/);
 assert.match(sql,/revoke all .* from public, anon, authenticated/);
 assert.match(edge,/previous\.data\.state==='sent'/);
 assert.match(edge,/previous\.data\.state==='failed'/);
 assert.match(edge,/state:'sending'/);
 assert.match(edge,/state='uncertain'|state:previous\.data\.state/);
 assert.match(edge,/sendPhoto/);
});
test('card sent only after successful original financial order, with issued code and retry without new order',()=>{
 for(const page of [buy,sell]){
  assert.ok(page.indexOf('await api.create')<page.indexOf('await deliverCard(res.order_id,res.order_code)'));
  assert.match(page,/rememberOriginalOrderCard\(\{/);
  assert.match(page,/deliverOriginalOrderCard/);
  assert.match(page,/setCardDelivery\('sending'\)/);
  assert.match(page,/بدون ثبت سفارش جدید/);
  assert.match(page,/dispatchOriginalOrderCard/);
  assert.match(page,/rememberOriginalOrderCard/);
 }
 assert.match(api,/verifiedCardSnapshot/);
 assert.match(api,/originalFinanceCall\('card\.issued',\{order_id:Number\(order_id\)\}\)/);
 assert.match(api,/renderOriginalOrderCardPreview\(issued\)/);
 assert.match(card,/realCode\?issuedCode:'PREVIEW'/);
 assert.match(bridge,/X-Telegram-Init-Data/);
 assert.match(bridge,/new FormData\(/);
});
test('admin dashboard retains Telegram HMAC, server allowlist, review gates and strictly signed private card links',()=>{
 assert.match(admin,/if\(!isOwner\(actor\.id\)\)/);
 assert.match(admin,/if\(!READ\)/);
 assert.match(admin,/if\(action==='dashboard'\)/);
 assert.match(admin,/if\(action==='orders\.detail'\)/);
 assert.match(admin,/createSignedUrl\(path,90\)/);
 assert.match(admin,/saraf_original_order_card_deliveries/);
 assert.match(admin,/card_delivery:delivery.data\|\|\[\]/);
 const adminUi=read('webapp/src/pages/OriginalAdmin.jsx');
 assert.match(adminUi,/گزارش ارسال کارت دیجیتال مشتری و مدیر/);
 assert.match(adminUi,/record.recipient==='customer'/);
 assert.match(admin,/action==='order\.complete'/);
 assert.match(admin,/if\(action==='kyc\.review'\)/);
 assert.match(admin,/if\(action==='remittances\.transition'\)/);
});
