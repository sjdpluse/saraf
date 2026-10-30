import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {originalReleaseSignature,verifyOriginalReleaseProof} from
 '../../supabase/functions/saraf-original-transactions/preflight.mjs';
const key='12345678:synthetic_bot_Api_token_ABC_verylong_secure_example123';
const other='12345679:other_original_bot_token_ABC_verylong_secure_example123';
const t=1750000000000;
test('bot HMAC release challenge verifies only fresh original token, never expires into production orders',async()=>{
 const stamp=String(Math.floor(t/1000));
 const signed=await originalReleaseSignature(key,stamp);
 assert.match(signed,/^[0-9a-f]{64}$/);
 assert.equal(await verifyOriginalReleaseProof(key,stamp,signed,t),true);
 assert.equal(await verifyOriginalReleaseProof(other,stamp,signed,t),false);
 assert.equal(await verifyOriginalReleaseProof(key,stamp,signed,t+46000),false);
 assert.equal(await verifyOriginalReleaseProof(key,stamp,signed,t-46000),false);
 assert.equal(await verifyOriginalReleaseProof(key,stamp,signed.replace(/^./,'0'),t),false);
 assert.equal(await verifyOriginalReleaseProof(key,stamp,'',t),false);
 assert.equal(await verifyOriginalReleaseProof('',stamp,signed,t),false);
});
test('HMAC authorizes only read-only release action before any signed customer route',()=>{
 const source=readFileSync(new URL(
  '../../supabase/functions/saraf-original-transactions/index.ts',import.meta.url),'utf8');
 const script=readFileSync(new URL(
  '../../scripts/verify_original_saraf_machine_release.mjs',import.meta.url),'utf8');
 assert.ok(source.indexOf("if(req.headers.has('X-Saraf-Release-Signature'))")<
  source.indexOf("const user=await verifyTelegramInitData("));
 assert.match(source,/if\(!valid\)return out\(origin,401,\{error:'INVALID_RELEASE_PROOF'\}\)/);
 assert.match(source,/body\?\.action!=='release\.preflight'/);
 assert.match(source,/return out\(origin,403,\{error:'RELEASE_PROOF_READ_ONLY'\}\)/);
 assert.match(source,/bank_ready:bankReady/);
 assert.match(source,/ready_for_cutover:ready/);
 assert.doesNotMatch(script,/action:'(orders.create|order.confirm|remittances.create|kyc.review)'/);
 assert.doesNotMatch(source,/return out\(origin,200,\{.*secret/i);
});
