import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {ApiError,asOriginalApiError} from '../../webapp/src/lib/apiError.mjs';

test('original customer must reach identity verification after high-value buy/sell (not a generic failed trade)',()=>{
 const e=asOriginalApiError(Object.assign(new Error('درخواست تأیید هویت الزامی است.'),{
  code:'IDENTITY_VERIFICATION_REQUIRED',status:403,
 }));
 assert.ok(e instanceof ApiError);
 assert.equal(e.code,'IDENTITY_VERIFICATION_REQUIRED');
 assert.equal(e.status,403);
 assert.match(e.message,/تأیید هویت/);
});
test('quote expiry and idempotency/conflict preserve codes, no silent create',()=>{
 const cases=[
  ['QUOTE_EXPIRED_OR_CONSUMED',409],
  ['QUOTE_MISMATCH',409],
  ['IDEMPOTENCY_PAYLOAD_CONFLICT',409],
  ['INVALID_TELEGRAM_AUTH',401],
  ['INVALID_PAYMENT_METHOD',400],
  ['UPLOAD_FAILED',503],
  ['RATE_LIMIT',429],
 ];
 for(const [code,status] of cases){
  const e=asOriginalApiError({message:'error',code,status});
  assert.ok(e instanceof ApiError);
  assert.equal(e.code,code);assert.equal(e.status,status);
 }
 const already=new ApiError('existing',409,'QUOTE_EXPIRED_OR_CONSUMED');
 assert.equal(asOriginalApiError(already),already);
});
test('unexpected adapter exceptions are service failures, never false successes',()=>{
 assert.equal(asOriginalApiError(null).status,503);
 assert.equal(asOriginalApiError(new Error('network')).code,'SERVICE_UNAVAILABLE');
 assert.equal(asOriginalApiError({status:200}).status,503);
 assert.equal(asOriginalApiError({code:'BAD',status:999}).status,503);
});
test('original native UI wraps every signed customer and admin-agnostic financial/identity transport',()=>{
 const code=readFileSync(new URL('../../webapp/src/lib/api.js',import.meta.url),'utf8');
 assert.match(code,/from ['"]\.\/apiError\.mjs['"]/);
 assert.match(code,/if \(IS_TELEGRAM_NATIVE\) \{\s*try \{/);
 assert.match(code,/throw asOriginalApiError\(error\)/);
 assert.match(code,/return await renderOriginalOrderCardPreview\(verified\)/);
 for(const route of [
  '/usdt/quote','/usdt/orders/buy','/usdt/orders/sell',
  '/usdt/kyc','/usdt/upload-receipt','/remittances/quote','/remittances',
  '/usdt/orders/me','/remittances/me'
 ])assert.ok(code.includes(route),'missing original '+route);
});
