import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {originalBotMenu,originalMiniAppLink,originalStablecoinMenu} from '../tgcloud/lib/legacy_menus.js';
import {parseOriginalAdminCommand} from '../tgcloud/lib/original_admin_parse.js';

const read=(name)=>readFileSync(new URL('../tgcloud/'+name,import.meta.url),'utf8');
test('Telegram Serverless V8 has no URLSearchParams/URL constructor: all released modules avoid them',()=>{
 const modules=[
  'handlers/message.js','handlers/callback_query.js',
  'lib/legacy_menus.js','lib/legacy_calc.js','lib/legacy_calculators.js',
  'lib/legacy_rate_engine.js','lib/legacy_compare.js','lib/legacy_live_rates.js',
  'lib/original_admin_entry.js','lib/original_admin_parse.js',
  'lib/currencies.js','lib/reference_rates.js','lib/metals.js',
  'lib/cryptos.js','lib/local_market_parser.js','lib/local_market_service.js',
  'endpoints/getReadOnlyMarket.js','endpoints/getLocalMarket.js',
  'endpoints/getMarketSnapshot.js','endpoints/getSarafCapabilities.js',
 ];
 for(const name of modules)assert.doesNotMatch(read(name),/\bnew\s+URL(?:SearchParams)?\s*\(/,
  'unsupported URL constructor in '+name);
});
test('/start original reply keyboard works without browser URL globals',()=>{
 const m=originalBotMenu();
 assert.equal(m.keyboard[1][0].web_app.url,
  'https://app8533795882.tgcloud.ai/?v=20260905-v3&action=justmarkets');
 assert.equal(originalMiniAppLink('buy','USDT'),
  'https://app8533795882.tgcloud.ai/?v=20260905-v3&action=buy&asset=USDT');
 assert.equal(originalMiniAppLink('sell','USDC'),
  'https://app8533795882.tgcloud.ai/?v=20260905-v3&action=sell&asset=USDC');
 assert.equal(originalStablecoinMenu().inline_keyboard.length,3);
});
test('original administrator commands preserve get/set/toString and percent-escaped broadcast text',()=>{
 for(const command of ['/post','/publish','/stats','/spreads','/usdtpending']){
  const parsed=parseOriginalAdminCommand(command);
  assert.equal(parsed.query.get('action'),'admin');
  assert.ok(parsed.query.toString().includes('action=admin'));
 }
 const post=parseOriginalAdminCommand('📢 نشر پست (فیسبوک/اینستاگرام)');
 assert.equal(post.query.get('admin'),'post');
 const message='سلام & نرخ دلار + ۱۰٪';
 const parsed=parseOriginalAdminCommand('/broadcast '+message);
 assert.equal(parsed.query.get('broadcast'),message);
 assert.equal(decodeURIComponent(parsed.query.toString().split('broadcast=')[1]),message);
});
