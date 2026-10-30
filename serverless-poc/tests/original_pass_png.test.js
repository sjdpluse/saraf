import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {originalPassInput} from '../../webapp/src/lib/originalPassData.mjs';

test('original pass validates four ASCII digits and asset/action whitelist',()=>{
 assert.deepEqual(originalPassInput({action:'buy',asset:'USDT',code:'0007'}),{
  action:'buy',asset:'USDT',code:'0007',actionFa:'پرداخت حضوری',
  fileName:'saraf-buy-USDT-0007.png',
 });
 assert.equal(originalPassInput({action:'sell',asset:'usdc',code:'9999'}).actionFa,'دریافت حضوری');
 for(const code of ['', '123','12345','12a4','۱۲۳۴','../../']){
  assert.throws(()=>originalPassInput({action:'buy',asset:'USDT',code}));
 }
 assert.throws(()=>originalPassInput({action:'refund',asset:'USDT',code:'1234'}));
 assert.throws(()=>originalPassInput({action:'buy',asset:'BTC',code:'1234'}));
});
test('native Mini App renders original PNG locally without Railway or public pass token',()=>{
 const render=readFileSync(new URL('../../webapp/src/lib/originalPassPng.js',import.meta.url),'utf8');
 const ui=readFileSync(new URL('../../webapp/src/components/InPersonPass.jsx',import.meta.url),'utf8');
 assert.match(render,/canvas\.width=1200;canvas\.height=760;/);
 assert.match(render,/canvas\.toBlob\(/);
 assert.match(render,/blob\.type!=='image\/png'/);
 assert.match(render,/File System Access confirms a \*real\* write/);
 assert.match(render,/return await showConfirm\(/);
 assert.doesNotMatch(render,/railway\.app|service_role|BOT_TOKEN|receipt_file_id/);
 assert.match(ui,/if \(IS_TELEGRAM_NATIVE\)/);
 assert.match(ui,/renderOriginalInPersonPass/);
 assert.match(ui,/saveOriginalPassLocally/);
 assert.match(ui,/await api\.getInPersonPassLink/);
});
