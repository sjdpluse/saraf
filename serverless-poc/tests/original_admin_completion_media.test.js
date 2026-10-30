import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {issueOriginalProof,verifyOriginalProof}
 from '../../supabase/functions/saraf-original-admin/proof.mjs';
const read=path=>readFileSync(new URL('../../'+path,import.meta.url),'utf8');
const key='1234567890:synthetic-private-migration-test-bot-token';
const original={order_id:18,actor_id:77,
 file_id:'AgACAgQAAxkBAAMQ_example12345_-ABC',
 file_type:'photo',file_name:'transaction-details.jpg'};
test('original Telegram proof binds the exact admin and original order with 600s expiry',async()=>{
 const time=1750000000000;
 const token=await issueOriginalProof(key,original,time);
 assert.deepEqual(await verifyOriginalProof(key,token,77,18,time+300000),{
  file_id:original.file_id,file_type:'photo',
  file_name:'transaction-details.jpg',
 });
 await assert.rejects(verifyOriginalProof(key,token,78,18,time),/INVALID_COMPLETION_PROOF/);
 await assert.rejects(verifyOriginalProof(key,token,77,19,time),/INVALID_COMPLETION_PROOF/);
 await assert.rejects(verifyOriginalProof(key,token,77,18,time+601000),/INVALID_COMPLETION_PROOF/);
 await assert.rejects(verifyOriginalProof(key,token+'x',77,18,time),/INVALID_COMPLETION_PROOF/);
 await assert.rejects(verifyOriginalProof(key+'.other',token,77,18,time),/INVALID_COMPLETION_PROOF/);
});
test('file ID and filename are whitelisted, no arbitrary server URLs',async()=>{
 await assert.rejects(issueOriginalProof(key,{...original,file_id:'https://evil.test'}));
 await assert.rejects(issueOriginalProof(key,{...original,file_name:'../../passport.pdf'}));
 await assert.rejects(issueOriginalProof(key,{...original,file_type:'command'}));
 const token=await issueOriginalProof(key,{...original,file_type:'document',
  file_name:'transaction-details.pdf'});
 assert.equal((await verifyOriginalProof(key,token,77,18)).file_type,'document');
});
test('only signed original admin can upload a real Telegram bot file_id and complete',()=>{
 const edge=read('supabase/functions/saraf-original-admin/index.ts');
 const upload=read('supabase/functions/saraf-original-admin/proof-upload.mjs');
 const sql=read('supabase/sql/saraf_original_admin_commands_STAGED.sql');
 const web=read('webapp/src/lib/originalAdminBridge.js');
 assert.match(edge,/verifyTelegramInitData/);
 assert.match(edge,/if\(!isOwner\(actor\.id\)\)/);
 assert.match(edge,/if\(!WRITE\)return answer\(origin,503/);
 assert.match(edge,/verifyOriginalProof\(BOT,attestation,actor\.id,orderId\)/);
 assert.match(edge,/p_file_id:media\?\.file_id\|\|null/);
 assert.match(upload,/\.eq\('id',orderId\)\.maybeSingle\(\)/);
 assert.match(upload,/current\.data\.status!=='confirmed'/);
 assert.match(upload,/Telegram\.org\/bot/i);
 assert.match(upload,/issueOriginalProof\(bot/);
 assert.match(upload,/8\*1024\*1024/);
 assert.match(sql,/completion_proof_file_id=CASE WHEN p_action='complete'/);
 assert.ok(sql.includes("p_file_id ~ '^[A-Za-z0-9_-]+$'"));
 assert.ok(sql.includes('length(p_file_id) BETWEEN 12 AND 300'));
 assert.match(web,/uploadOriginalAdminCompletionProof/);
});
