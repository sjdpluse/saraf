import test from 'node:test';
import assert from 'node:assert/strict';
import {applyOriginalSpread,selectOriginalBasis,historicalOriginalBasis}
 from '../tgcloud/lib/legacy_rate_engine.js';

test('the existing Saraf half-spread buy/sell on USD',()=>{
 const actual=applyOriginalSpread(70,'usd');
 assert.equal(actual.buy,69.79);
 assert.equal(actual.sell,70.21);
 assert.equal(actual.spread_percent,.6);
});

test('original Sarai Shahzada market takes precedence over world reference',()=>{
 const quote=selectOriginalBasis('usd',{usd:70},
  {sarai_shahzada:{usd:{buy:65.9,sell:65.95}}});
 assert.equal(quote.saraf_quote.basis,'local');
 assert.equal(quote.saraf_quote.basis_rate,65.925);
 assert.equal(quote.saraf_quote.buy,65.7272);
});

test('original historical local, then international fallback',()=>{
 assert.deepEqual(historicalOriginalBasis({buy:65.9,sell:65.95},70),
  {rate:65.925,basis:'local'});
 assert.deepEqual(historicalOriginalBasis(null,70),{rate:70,basis:'reference'});
});
