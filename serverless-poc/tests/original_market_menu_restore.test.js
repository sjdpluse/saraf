import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {originalBotMenu,currencyList,goldList,converterFrom,compareTarget} from '../tgcloud/lib/legacy_menus.js';

const source=readFileSync(new URL('../tgcloud/handlers/message.js',import.meta.url),'utf8');
const callbacks=readFileSync(new URL('../tgcloud/handlers/callback_query.js',import.meta.url),'utf8');
const fullMenu=[
 'خرید و فروش | USDT/USDC','Saraf - JustMarkets','💵 نرخ ارزها',
 '🥇 نرخ طلا','🥈 نرخ نقره','🔄 مبدل ارز جهانی',
 '🪙 نرخ رمزارزها','📊 مقایسه با گذشته','ℹ️ درباره ربات',
];
test('Telegram-native /start restores every ORIGINAL market button persistently',()=>{
 const menu=originalBotMenu();
 assert.equal(menu.resize_keyboard,true);
 assert.equal(menu.is_persistent,true);
 assert.equal(menu.one_time_keyboard,false);
 const labels=menu.keyboard.flat().map(x=>x.text);
 assert.deepEqual(labels,fullMenu);
 assert.match(source,/isMainMenuRequest\(input\)/);
 assert.match(source,/originalBotMenu\(\)/);
 assert.match(source,/case '💵 نرخ ارزها'/);
 assert.match(source,/case '🥇 نرخ طلا'/);
 assert.match(source,/case '🥈 نرخ نقره'/);
 assert.match(source,/case '🔄 مبدل ارز جهانی'/);
});
test('the ORIGINAL foreign currency, gold, converter, and history callback menus are not stripped',()=>{
 const rates=currencyList().inline_keyboard.flat().map(x=>x.callback_data);
 assert.ok(rates.includes('cur:all'));
 assert.ok(rates.includes('cur:usd'));
 const gold=goldList().inline_keyboard.flat().map(x=>x.callback_data);
 assert.deepEqual(gold.slice(-2),['gold:all','gold:calc']);
 const convert=converterFrom().inline_keyboard.flat().map(x=>x.callback_data);
 const compare=compareTarget().inline_keyboard.flat().map(x=>x.callback_data);
 assert.ok(convert.includes('convfrom:usd'));
 assert.ok(compare.includes('cmp_target:usd'));
 for(const prefix of ["type==='cur'","type==='gold'","type==='convfrom'","type==='cmp_target'"]){
  assert.ok(callbacks.includes(prefix),prefix+' callback missing');
 }
});
test('invalid messages recover original main keyboard instead of trapping user in USDT-only flow',()=>{
 assert.match(source,/if \(!m\) return reply\(chatId,/);
 assert.match(source,/originalBotMenu\(\)/);
 assert.match(source,/case '\/rates'/);
 assert.match(source,/case '\/gold'/);
 assert.match(source,/case '\/silver'/);
});
