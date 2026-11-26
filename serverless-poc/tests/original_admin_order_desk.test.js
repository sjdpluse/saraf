import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {readOrderPage, receiptObject} from '../../supabase/functions/saraf-original-admin/order-desk.mjs';
import {orderNumber, amount, kabulTime} from '../../webapp/src/lib/adminOrders.js';

test('signed admin bridge permits both operational reads used by the desk', () => {
  const bridge = readFileSync(new URL('../../webapp/src/lib/originalAdminBridge.js', import.meta.url), 'utf8');
  const allowlist = bridge.match(/const allowed=\[([^\]]+)\]/)[1];
  for (const action of ['dashboard','orders.detail','orders.pending','orders.confirmed']) {
    assert.ok(allowlist.includes("'" + action + "'"), action);
  }
});

test('order lookup accepts pasted codes, Persian and Arabic digits, rejects unsafe IDs', () => {
  for (const code of ['USDT-۰۰۰۱۲', 'usdc-00012', ' ١٢ ', '12']) assert.equal(orderNumber(code), 12);
  for (const code of ['1e3','123x','USDT-0','-12','9999999999999999']) assert.equal(orderNumber(code), null);
  assert.notEqual(amount(0), amount(null));
  assert.match(kabulTime('2026-11-26T00:00:00Z'), /۰۴:۳۰/);
});

test('signed receipt renewal uses only the order owner and the receipt bucket', () => {
  const origin = 'https://original.example';
  const path = '/storage/v1/object/sign/usdt-receipts/123_a12bc.jpg';
  assert.equal(receiptObject(origin + path + '?token=expired', origin, 123), '123_a12bc.jpg');
  for (const ref of ['legacy-file-id', 'https://elsewhere.example' + path, origin + path.replace('123_', '1234_'),
    origin + path.replace('usdt-receipts', 'private'), origin + path.replace('a12bc', 'a%2Fb')]) {
    assert.equal(receiptObject(ref, origin, 123), null);
  }
});

test('queue pagination applies side and status before slicing across transitions', async () => {
  let rows = Array.from({length:90}, (_, i) => ({id:i+1, order_type:i%2?'sell':'buy', status:i%3?'pending':'confirmed'}));
  const db = {from(table) {
    assert.equal(table, 'usdt_orders');
    let values = [...rows].reverse();
    return {select() {return this;}, eq(key, value) {values = values.filter(r => r[key] === value); return this;},
      gt(key, value) {values = values.filter(r => r[key] > value); return this;},
      order(key, options) {assert.deepEqual(options,{ascending:true}); values.sort((a,b)=>a[key]-b[key]); return this;},
      limit(n) {return {data:values.slice(0,n)};}};
  }};
  const first = (await readOrderPage(db,'pending',{side:'sell'})).body;
  assert.equal(first.orders.length,20);
  assert.ok(first.orders.every(o=>o.order_type==='sell' && o.status==='pending'));
  rows = rows.filter(row=>row.id!==first.orders[0].id);
  const last = (await readOrderPage(db,'pending',{side:'sell',after:first.next_cursor})).body;
  assert.equal(last.orders.length,10);
  assert.equal(last.next_cursor,null);
  assert.ok(last.orders.every(row => row.id > first.next_cursor));
  for(const input of [{side:'other'},{after:-1},{after:'22'}]) {
    assert.equal((await readOrderPage(null, 'pending', input)).status,400);
  }
});
