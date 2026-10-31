import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseOriginalAdminCommand} from '../tgcloud/lib/original_admin_parse.js';
const root=(relative)=>readFileSync(new URL('../../'+relative,import.meta.url),'utf8');
const edge=root('supabase/functions/saraf-original-admin/index.ts');
const ui=root('webapp/src/pages/OriginalAdmin.jsx');
const bridge=root('webapp/src/lib/originalAdminBridge.js');
const runner=root('scripts/run_original_manual_social_worker.py');
const sql=root('supabase/migrations/20261031_original_social_manual_queue.sql');
const timeoutSql=root('supabase/migrations/20261031_original_social_manual_unknown_timeout.sql');

test('original manual post text/button and /post point to existing signed admin view',()=>{
 for(const input of ['/post','/publish','📢 نشر پست (فیسبوک/اینستاگرام)']){
  const parsed=parseOriginalAdminCommand(input);
  assert.equal(parsed?.query?.get('action'),'admin');
  assert.equal(parsed?.query?.get('admin'),'post');
 }
 assert.match(ui,/manualSocialPost\(/);
 assert.match(ui,/social\.post\.create/);
 assert.match(ui,/social\.post\.status/);
 assert.match(ui,/await showConfirm\(/);
 assert.match(bridge,/['"]social\.post\.create['"]/);
 assert.match(bridge,/['"]social\.post\.status['"]/);
});
test('public cannot bypass signed original Telegram admin and independent Meta publish switch',()=>{
 const auth=edge.indexOf('const actor=await verifyTelegramInitData(');
 const userCheck=edge.indexOf('if(!isOwner(actor.id))');
 const command=edge.indexOf("if(action==='social.post.create')");
 assert.ok(auth>=0&&auth<command,'signature checked before social publish');
 assert.ok(userCheck>=0&&userCheck<command,'private admin allowlist verified before posting');
 assert.match(edge,/SARAF_ORIGINAL_SOCIAL_POST_ENABLED/);
 assert.match(edge,/if\(!SOCIAL_POSTS\)/);
 assert.match(edge,/if\(isWrite\(action\)&&!WRITE\)/);
 assert.match(edge,/eq\('admin_chat_id',actor\.id\)/);
});
test('original manual queue is idempotent private and never automatically repeats uncertain Meta posts',()=>{
 assert.match(sql,/enable row level security/i);
 assert.match(sql,/revoke all on table public\.saraf_original_manual_social_requests from public,anon,authenticated/i);
 assert.match(sql,/unique \(admin_chat_id,idempotency_key\)/i);
 assert.match(sql,/for update skip locked/i);
 assert.match(sql,/security invoker/i);
 assert.match(timeoutSql,/state='needs_review'/);
 assert.match(timeoutSql,/where state='processing' and started_at</);
});
test('same original Python services still perform actual branded image posting, no alternate Meta writer',()=>{
 assert.match(runner,/from jobs import get_current_quotes_and_metals/);
 assert.match(runner,/facebook_service\.check_and_maybe_post/);
 assert.match(runner,/instagram_service\.check_and_maybe_post/);
 assert.match(runner,/force=True/);
 assert.match(runner,/return_exceptions=True/);
 assert.match(runner,/ORIGINAL_SOCIAL_PUBLICATION_NOT_ENABLED/);
 assert.match(runner,/classify\(facebook\)/);
 assert.doesNotMatch(edge,/graph\.facebook\.com|graph\.instagram\.com/);
});
