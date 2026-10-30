import test from 'node:test';
import assert from 'node:assert/strict';
import {
  originalBotMenu,currencyList,goldList,goldCalcMode,goldCalcKarat,
  silverCalcMode,compareTarget,comparePeriod,converterFrom,converterTo,
  converterAmounts,aboutKeyboard,codeLabel,validKarat
} from '../tgcloud/lib/legacy_menus.js';
import { VALID_CODES } from '../tgcloud/lib/currencies.js';
const allCallbacks=markup=>markup.inline_keyboard.flat().map(x=>x.callback_data).filter(Boolean);

test('port original main keyboard text and order from main:keyboards.py',()=>{
  const labels=originalBotMenu().keyboard.map(row=>row.map(x=>x.text));
  assert.deepEqual(labels,[
    ['خرید و فروش | USDT/USDC'],['Saraf - JustMarkets'],
    ['💵 نرخ ارزها','🥇 نرخ طلا'],['🥈 نرخ نقره','🔄 مبدل ارز جهانی'],
    ['🪙 نرخ رمزارزها','📊 مقایسه با گذشته'],['ℹ️ درباره ربات'],
  ]);
});
test('original currency callback prefix and complete currencies preserved',()=>{
  const callbacks=allCallbacks(currencyList());
  assert.equal(callbacks.length,VALID_CODES.length+1);
  assert.deepEqual(callbacks.filter(x=>x.startsWith('cur:')&&x!=='cur:all'),
    VALID_CODES.map(c=>'cur:'+c));
  assert.ok(callbacks.includes('cur:all'));
  assert.equal(codeLabel('usd'),'🇺🇸 دالر امریکایی');
});
test('original gold, silver, compare and about routes are kept',()=>{
  assert.deepEqual(allCallbacks(goldList()),[
    'gold:24','gold:22','gold:21','gold:18','gold:all','gold:calc'
  ]);
  assert.deepEqual(allCallbacks(goldCalcMode()),['goldcalc_mode:buy','goldcalc_mode:sell']);
  assert.deepEqual(allCallbacks(goldCalcKarat('buy')),[
    'goldcalc_karat:buy:24','goldcalc_karat:buy:22',
    'goldcalc_karat:buy:21','goldcalc_karat:buy:18'
  ]);
  assert.deepEqual(allCallbacks(silverCalcMode()),['silvercalc_mode:buy','silvercalc_mode:sell']);
  assert.ok(allCallbacks(compareTarget()).includes('cmp_target:gold'));
  assert.deepEqual(allCallbacks(comparePeriod('usd')),[
    'cmp_period:usd:1','cmp_period:usd:7','cmp_period:usd:30','cmp_period:usd:90'
  ]);
  assert.deepEqual(allCallbacks(aboutKeyboard()).slice(0,2),
    ['about:markets','about:tools']);
  assert.equal(validKarat(19),false);
});
test('original converter choices and preset amounts preserved',()=>{
  assert.equal(allCallbacks(converterFrom()).length,VALID_CODES.length);
  assert.ok(allCallbacks(converterTo('usd')).includes('convfrom:back'));
  assert.ok(!allCallbacks(converterTo('usd')).includes('convto:usd:usd'));
  assert.deepEqual(allCallbacks(converterAmounts('usd','eur')),[
    'convamt:usd:eur:1','convamt:usd:eur:10',
    'convamt:usd:eur:50','convamt:usd:eur:100',
    'convamt:usd:eur:500','convamt:usd:eur:1000',
    'convamt:usd:eur:custom'
  ]);
});
