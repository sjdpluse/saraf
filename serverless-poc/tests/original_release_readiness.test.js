import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const edge=readFileSync(
 new URL('../../supabase/functions/saraf-original-transactions/index.ts',import.meta.url),'utf8');
const check=readFileSync(
 new URL('../../scripts/verify_original_finance_prerequisites.mjs',import.meta.url),'utf8');

test('original bank and wallet release readiness needs signed Telegram authorized administrator',()=>{
 assert.match(edge,/verifyTelegramInitData/);
 assert.match(edge,/if\(!user\)return out\(origin,401/);
 assert.match(edge,/if\(action==='release\.readiness'\)/);
 assert.match(edge,/if\(!ADMINS\.includes\(String\(user\.id\)\)\)/);
 assert.match(edge,/if\(!LIVE\)return out\(origin,503/);
 assert.ok(edge.indexOf("if(action==='release.readiness')")<
  edge.indexOf("if(!LIVE)return out(origin,503"));
 assert.match(edge,/note:'SIGNED_ADMIN_ONLY_READ_ONLY_NO_MONEY_OPERATIONS'/);
});
test('original Python stablecoin deposit wallet variable names are supported',()=>{
 assert.match(edge,/'SARAF_USDT_DEPOSIT_WALLETS_JSON':'SARAF_USDC_DEPOSIT_WALLETS_JSON'/);
 assert.match(edge,/'USDT_DEPOSIT_WALLETS_JSON':'USDC_DEPOSIT_WALLETS_JSON'/);
 assert.match(edge,/Deno\.env\.get\(primary\)\|\|Deno\.env\.get\(legacy\)/);
});
test('production prereq prints missing secret NAMES only, never financial values',()=>{
 assert.match(check,/action:'release\.readiness'/);
 assert.match(check,/ready_for_cutover/);
 assert.match(check,/missing_secret_names/);
 assert.doesNotMatch(check,/console\.log\([^\n]*(?:bank_account_number|deposit_wallet|address)/i);
 assert.doesNotMatch(check,/action:'remittances\.create'|action:'quote'/);
});
