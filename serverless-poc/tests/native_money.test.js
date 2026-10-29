import test from 'node:test';
import assert from 'node:assert/strict';
import { parseMinor, afnTenthFor, buyPricing, rateToBasisPoints } from '../tgcloud/lib/native_money.js';

test('parses valid decimal financial inputs with half-up rounding',()=>{
  assert.equal(parseMinor('12.345',2),1235);
  assert.equal(parseMinor('12.344',2),1234);
  assert.equal(parseMinor('0.00001',2),0);
  assert.throws(()=>parseMinor('1e5',2));
  assert.throws(()=>parseMinor('-1',2));
  assert.throws(()=>parseMinor('abc',2));
});
test('rounds basis points and afghani tenths',()=>{
  assert.equal(rateToBasisPoints('70.1234'),701234);
  assert.equal(afnTenthFor(10000,701234),70123);
});
test('matches 50/30/20 market margin economics for 100 USD',()=>{
 const p=buyPricing(10000,700000);
 assert.equal(p.marginCents,250);
 assert.equal(p.supplierCents,125);
 assert.equal(p.sarafCents,75);
 assert.equal(p.discountCents,50);
 assert.equal(p.totalUsdCents,10200);
 assert.equal(p.totalAfnTenth,71400);
});
