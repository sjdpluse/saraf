import test from 'node:test';
import assert from 'node:assert/strict';
import {
 ORIGINAL_ASSETS,normalizeOriginalRemittanceAsset,
 normalizeOriginalRemittanceNetwork,originalRemittanceWallets,
 originalRemittanceConfig,originalAssetPriceUsd,originalRemittanceValuation,
} from '../../supabase/functions/saraf-original-transactions/remittance.mjs';
const addr='0x1111111111111111111111111111111111111111';

test('remittance V2 registry is exactly original Python registry, no invented assets',()=>{
 assert.deepEqual(Object.keys(ORIGINAL_ASSETS),[
  'USDT','USDC','DAI','TUSD','TRX','BNB','ETH','SOL',
  'WBTC','PAXG','PYUSD','WETH','BTCB','POL','BTC',
 ]);
 assert.deepEqual(ORIGINAL_ASSETS.USDT.networks,
  ['BEP20','TRC20','ERC20','ARBITRUM','BASE','POLYGON','SOL']);
 assert.deepEqual(ORIGINAL_ASSETS.USDC.networks,
  ['BEP20','ERC20','ARBITRUM','BASE','POLYGON','SOL']);
 assert.equal(normalizeOriginalRemittanceNetwork('BTC','btc'),'BITCOIN');
 assert.equal(normalizeOriginalRemittanceNetwork('USDC','SOLANA'),'SOL');
 assert.throws(()=>normalizeOriginalRemittanceNetwork('USDC','TRC20'));
 assert.throws(()=>normalizeOriginalRemittanceAsset('ETH',false));
 assert.equal(normalizeOriginalRemittanceAsset('ETH',true),'ETH');
 assert.throws(()=>normalizeOriginalRemittanceAsset('OTHER',true));
});

test('original wallet env precedence and disabled V2 assets are preserved',()=>{
 const env={
  REMITTANCE_WALLETS_JSON:JSON.stringify({
   USDT:{ERC20:addr},ETH:{BASE:addr},USDC:{SOL:'So1anaValidWalletStringExample12345'},
  }),
  REMITTANCE_USDT_TRC20_WALLET:'T'.repeat(34),
 };
 const v1=originalRemittanceWallets(env,false);
 assert.deepEqual(Object.keys(v1).sort(),['USDC','USDT']);
 assert.equal(v1.USDT.ERC20,addr);
 assert.equal(v1.USDT.TRC20,'T'.repeat(34));
 assert.equal(v1.ETH,undefined);
 const v2=originalRemittanceConfig(env,true);
 assert.ok(v2.some(x=>x.asset==='ETH'&&x.networks.some(n=>n.code==='BASE')));
 assert.ok(v2.some(x=>x.asset==='USDC'&&x.logo_url.includes('usd-coin')));
 assert.ok(v2.some(x=>x.asset==='USDT'&&x.networks.some(n=>n.code==='TRC20')));
 assert.throws(()=>originalRemittanceWallets({REMITTANCE_WALLETS_JSON:'oops'},true));
 const fallback=originalRemittanceWallets({SARAF_REMITTANCE_WALLETS_JSON:
  JSON.stringify({USDT:{ERC20:addr}}),REMITTANCE_WALLETS_JSON:''},false);
 assert.equal(fallback.USDT.ERC20,addr);
});
test('coin price comes only from CoinGecko and wrapped Bitcoin aliases original BTC',async()=>{
 let url='';
 const sampleFetch=async(request)=>{
  url=request;
  return {ok:true,json:async()=>({bitcoin:{usd:70500.12}})};
 };
 const p=await originalAssetPriceUsd('WBTC',sampleFetch);
 assert.equal(p.price,70500.12);
 assert.equal(p.source,'CoinGecko');
 assert.match(url,/ids=bitcoin/);
 await assert.rejects(originalAssetPriceUsd('WBTC',async()=>({ok:false})));
 await assert.rejects(originalAssetPriceUsd('WBTC',async()=>({
  ok:true,json:async()=>({bitcoin:{usd:0}}),
 })));
});
test('nonstable remittance quotes use USD *asset market price*, not token quantity',()=>{
 const q=originalRemittanceValuation({
  amount:0.1,asset:'BTC',network:'BITCOIN',
  priceUsd:70000,usdRate:65,feePercent:1.25,
  minUsd:10,maxUsd:10000,depositWallet:'bc1syntheticwallet123456789',v2:true,
 });
 assert.equal(q.crypto_amount,.1);
 assert.equal(q.asset_price_usd,70000);
 assert.equal(q.usd_value,7000);
 assert.equal(q.gross_afn,455000);
 assert.equal(q.fee_afn,5687.5);
 assert.equal(q.payout_afn,449312.5);
 assert.equal(q.network,'BITCOIN');
});
test('original USD threshold checks value in USD, not coin count',()=>{
 const q=originalRemittanceValuation({
  amount:1000,asset:'TRX',network:'TRC20',priceUsd:0.3,
  usdRate:65,depositWallet:'Tsyntheticwallet1234567890123456789',v2:true,
 });
 assert.equal(q.usd_value,300);
 assert.equal(q.gross_afn,19500);
 assert.throws(()=>originalRemittanceValuation({
  amount:1,asset:'BTC',network:'BITCOIN',priceUsd:70000,usdRate:65,
  depositWallet:'bc1syntheticwallet123456789',v2:true,
 }),/ORIGINAL_REMITTANCE_USD_LIMIT/);
 assert.throws(()=>originalRemittanceValuation({
  amount:1000,asset:'TRX',network:'TRC20',priceUsd:0,
  usdRate:65,depositWallet:'Tsyntheticwallet1234567890123456789',v2:true,
 }),/ORIGINAL_REMITTANCE_CONFIGURATION_INVALID/);
});
