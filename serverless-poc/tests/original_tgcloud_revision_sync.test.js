import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const publisher=readFileSync(new URL(
 '../../scripts/publish_original_saraf_serverless.mjs',import.meta.url),'utf8');
const packager=readFileSync(new URL(
 '../../scripts/prepare_saraf_original_release.mjs',import.meta.url),'utf8');

test('published original bot is fetched before deployment and no forced/unscoped push is permitted',()=>{
 const fetchIndex=publisher.indexOf("await cli(['fetch'])");
 const statusIndex=publisher.indexOf("await cli(['status'])");
 const pushIndex=publisher.indexOf("await cli(['push',...items,'dist/'])");
 const webhookIndex=publisher.indexOf("await cli(['webhook','sync'])");
 assert.ok(fetchIndex>=0&&fetchIndex<statusIndex&&statusIndex<pushIndex&&pushIndex<webhookIndex);
 assert.doesNotMatch(publisher,/cli\(\['push'\]\)/);
 assert.doesNotMatch(publisher,/'--force'/);
 assert.doesNotMatch(publisher,/cli\(\['webhook','sync','--drop-pending'\]\)/);
});
test('packaged original React and handlers use an exact allowlist; remote modules are preserved',()=>{
 assert.match(packager,/RELEASE_MODULES\.json/);
 assert.match(packager,/JSON\.stringify\(\[\.\.\.allowlist\]\.map/);
 assert.match(publisher,/new Set\(items\)\.size!==items\.length/);
 assert.match(publisher,/INVALID_SARAF_EXACT_RELEASE_ALLOWLIST/);
 assert.match(publisher,/if\(started&&previous\)/);
 assert.match(publisher,/await botApi\('getWebhookInfo'\)/);
 assert.match(publisher,/RESTORED_PREVIOUS_TELEGRAM_WEBHOOK/);
});
