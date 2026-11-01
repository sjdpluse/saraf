import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../../supabase/functions/saraf-original-transactions/index.ts',import.meta.url),'utf8');
test('original customer bot confirmations are after canonical commit, without premature payout',()=>{
 assert.match(source,/async function notifyCustomer\(chatId:number,text:string,html=false\)/);
 assert.match(source,/if\(rpc\.data&&!rpc\.data\.duplicate\)\{/);
 assert.match(source,/await Promise\.allSettled\(\[\s*notifyAdmin\('💸 حوالهٔ جدید/);
 assert.match(source,/notifyCustomer\(user\.id,'✅ درخواست حواله/);
 assert.match(source,/if\(!item\?\.duplicate\)\{/);
 assert.match(source,/notifyCustomer\(user\.id,messages\.customer,true\)/);
 assert.match(source,/db\.from\('usdt_orders'\)\.select\(/);
 assert.match(source,/buildOriginalOrderReports\(saved\.data,profile\.data\|\|\{\}\)/);
 assert.doesNotMatch(source,/notifyCustomer\(user\.id,[^\n]*pickup_code/);
 assert.match(source,/AbortSignal\.timeout\(6500\)/);
});
