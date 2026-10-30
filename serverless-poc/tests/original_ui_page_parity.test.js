// Migration parity regression checks: the original UI is NOT a read-only
// replacement. No backend payment permission is implied by rendering a page.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const app=readFileSync(new URL('../../webapp/src/App.jsx',import.meta.url),'utf8');
const api=readFileSync(new URL('../../webapp/src/lib/api.js',import.meta.url),'utf8');
test('all existing original React pages remain in the Telegram build source',()=>{
 const pages=[
  'home','buy','sell','orders','remittances','remittance',
  'reviews','terms','kyc','about','menu','justmarkets',
  'justmarkets-guide','justmarkets-verification','justmarkets-deposit'
 ];
 for(const page of pages)
  assert.ok(app.includes('page === "'+page+'"'), 'Original UI page removed: '+page);
 assert.ok(!app.includes('!IS_TELEGRAM_NATIVE'),'A native-only ban has been reintroduced');
 assert.ok(!app.includes('readOnly={IS_TELEGRAM_NATIVE}'),
   'Native-only read-only redesign has been reintroduced');
});
test('financial operations never fall through to non-existent Railway API on Telegram',()=>{
 assert.ok(api.includes('if (IS_TELEGRAM_NATIVE)'));
 const last=api.indexOf('const headers = { "X-Telegram-Init-Data"');
 const first=api.indexOf('if (IS_TELEGRAM_NATIVE)');
 assert.ok(last>first && api.slice(first,last).includes('NOT_MIGRATED'),
   'Original Railway fallback must not be used on Telegram');
});
