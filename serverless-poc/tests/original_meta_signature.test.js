import test from 'node:test';
import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
import {constantTimeEqual,metaSignatureValid,contentHash}
 from '../../supabase/functions/saraf-original-meta-webhook/signature.mjs';
const secret='a-super-secret-for-migration-test-only';
const payload=Buffer.from('{"object":"instagram","entry":[{"id":"synthetic"}]}');
const signature='sha256='+createHmac('sha256',secret).update(payload).digest('hex');
test('Meta signature authenticates ORIGINAL raw payload bytes',async()=>{
 assert.equal(await metaSignatureValid(secret,payload,signature),true);
 assert.equal(await metaSignatureValid(secret,Buffer.from(payload.toString()+' '),signature),false);
 assert.equal(await metaSignatureValid('wrong-super-secret-at-least-16',payload,signature),false);
 assert.equal(await metaSignatureValid(secret,payload,'sha1=invalid'),false);
 assert.equal(await metaSignatureValid(secret,payload,null),false);
});
test('Meta webhook verify tokens are compared without prefix attacks',()=>{
 assert.equal(constantTimeEqual(secret,secret),true);
 assert.equal(constantTimeEqual(secret,secret+'x'),false);
 assert.equal(constantTimeEqual('', ''),false);
 assert.equal(constantTimeEqual(secret,secret.slice(0,-1)+'X'),false);
});
test('duplicate Meta POST retries have the same stable fingerprint',async()=>{
 const first=await contentHash(payload);
 const second=await contentHash(Buffer.from(payload));
 assert.match(first,/^[0-9a-f]{64}$/);
 assert.equal(first,second);
 assert.notEqual(first,await contentHash(Buffer.from('altered')));
});
