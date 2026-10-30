import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {originalRiskLevel} from '../../supabase/functions/saraf-original-transactions/risk.mjs';

test('original Python risk engine: restricted, cancellation and payment changes',()=>{
 assert.equal(originalRiskLevel(null,100).level,'high');
 assert.equal(originalRiskLevel({kyc_status:'restricted'},10).level,'high');
 assert.equal(originalRiskLevel({kyc_status:'verified',cancelled_orders:3},10).level,'high');
 assert.equal(originalRiskLevel({kyc_status:'verified',payment_info_change_count:3},10).level,'high');
 assert.equal(originalRiskLevel({kyc_status:'verified',cancelled_orders:2},10).level,'low');
});
test('original Python risk engine: pending KYC and new-user large trade',()=>{
 assert.equal(originalRiskLevel({kyc_status:'pending',successful_orders:10},10).level,'medium');
 assert.equal(originalRiskLevel({kyc_status:'verified',successful_orders:2},999).level,'low');
 assert.equal(originalRiskLevel({kyc_status:'verified',successful_orders:2},1000).level,'medium');
 assert.equal(originalRiskLevel({kyc_status:'trusted',successful_orders:3},1000).level,'low');
 assert.equal(originalRiskLevel({kyc_status:'trusted',successful_orders:2},1500,{
  USDT_RISK_HIGH_AMOUNT_THRESHOLD:'2000',
 }).level,'low');
});
test('original signed selfie preview never exposes private storage paths or fetches images cross-provider',()=>{
 const edge=readFileSync(new URL('../../supabase/functions/saraf-original-transactions/index.ts',import.meta.url),'utf8');
 const card=readFileSync(new URL('../../webapp/src/lib/originalOrderCardPng.js',import.meta.url),'utf8');
 assert.match(edge,/\.eq\('chat_id',user\.id\)\.maybeSingle\(\)/);
 assert.match(edge,/\.createSignedUrl\(/);
 assert.match(edge,/selfie_path/);
 assert.match(edge,/const risk=originalRiskLevel/);
 assert.match(card,/source\.origin!=='https:\/\/cvernmhpnsgdtegvblyc\.supabase\.co'/);
 assert.match(card,/source\.searchParams\.get\('token'\)/);
 assert.match(card,/bytes\.size>8\*1024\*1024/);
 assert.match(card,/URL\.revokeObjectURL/);
 assert.match(card,/qr\.getModule\(col,row\)/);
});
