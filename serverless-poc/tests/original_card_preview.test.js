import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=(path)=>readFileSync(new URL('../../'+path,import.meta.url),'utf8');
const edge=read('supabase/functions/saraf-original-transactions/index.ts');
const api=read('webapp/src/lib/api.js');
const render=read('webapp/src/lib/originalOrderCardPng.js');
const qr=read('webapp/src/lib/vendor/qrcodegen.ts');
const bridge=read('webapp/src/lib/originalFinanceBridge.js');

test('original card preview validates the actual owner quote and expiry BEFORE sending verified card data',()=>{
 assert.match(edge,/if\(action==='card\.preview'\)/);
 assert.match(edge,/\.eq\('chat_id',user\.id\)\.maybeSingle\(\)/);
 assert.match(edge,/q\.data!?\.status!=='active'/);
 assert.match(edge,/Date\.parse\(q\.data!?\.expires_at\)<=Date\.now\(\)/);
 assert.match(edge,/Math\.abs\(Number\(q\.data!?\.usdt_amount\)-a\)>0\.0000001/);
 assert.match(edge,/methodNetworks\(type,input\.network/);
 assert.match(edge,/walletShape\(network,wallet\)/);
 assert.match(edge,/\.eq\('chat_id',user\.id\)\.maybeSingle\(\)/);
 assert.match(edge,/first_name,last_name,phone,kyc_status,trust_score,successful_orders/);
 assert.match(edge,/if\(!LIVE\)return out\(origin,503/);
});
test('Mini App uses signed Edge validation then local PNG without Railway fallback',()=>{
 assert.match(bridge,/'card\.preview'/);
 assert.match(api,/originalFinanceCall\('card\.preview',body\)/);
 assert.match(api,/renderOriginalOrderCardPreview\(verified\)/);
 assert.match(render,/canvas\.width=SIZE\.width;canvas\.height=SIZE\.height/);
 assert.match(render,/width:1320,height:900/);
 assert.match(render,/PREVIEW/);
 assert.match(render,/qrcodegen\.QrCode\.encodeText\(address/);
 assert.match(render,/qr\.getModule\(col,row\)/);
 assert.doesNotMatch(render,/qrserver|quickchart|railway\.app/);
 assert.match(qr,/Copyright \(c\) Project Nayuki\. \(MIT License\)/);
});
