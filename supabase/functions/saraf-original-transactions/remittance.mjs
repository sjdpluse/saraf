// Faithful JavaScript port of ORIGINAL main:
// services/remittance_asset_registry.py, remittance_wallet_config.py,
// remittance_price_service.py, remittance_v2.py and money.py.
// Uses the EXISTING remittance_orders table, with NO new wallets, assets,
// provider prices, or client-provided settlement values.
// Production finance remains gated off in index.ts.
import {originalRemittancePricing,exactMoney} from './pricing.mjs';

const ICON_BASE='https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/128/color';
const icon=s=>ICON_BASE+'/'+s.toLowerCase()+'.png';
export const ORIGINAL_ASSETS=Object.freeze({
 USDT:{name:'Tether USD',logo_url:'https://i.postimg.cc/250WhXsF/tether.png',
  networks:['BEP20','TRC20','ERC20','ARBITRUM','BASE','POLYGON','SOL']},
 USDC:{name:'USD Coin',logo_url:'https://i.postimg.cc/0QndtT7N/usd-coin-usdc-logo.jpg',
  networks:['BEP20','ERC20','ARBITRUM','BASE','POLYGON','SOL']},
 DAI:{name:'Dai',logo_url:icon('DAI'),networks:['ERC20','ARBITRUM','BASE','POLYGON']},
 TUSD:{name:'TrueUSD',logo_url:icon('TUSD'),networks:['BEP20','ERC20','ARBITRUM','POLYGON']},
 TRX:{name:'TRON',logo_url:icon('TRX'),networks:['TRC20']},
 BNB:{name:'BNB',logo_url:icon('BNB'),networks:['BEP20']},
 ETH:{name:'Ethereum',logo_url:icon('ETH'),networks:['ERC20','ARBITRUM','BASE']},
 SOL:{name:'Solana',logo_url:icon('SOL'),networks:['SOL']},
 WBTC:{name:'Wrapped Bitcoin',logo_url:icon('WBTC'),networks:['ERC20','ARBITRUM','POLYGON']},
 PAXG:{name:'PAX Gold',logo_url:icon('PAXG'),networks:['ERC20']},
 PYUSD:{name:'PayPal USD',logo_url:icon('PYUSD'),networks:['ERC20']},
 WETH:{name:'Wrapped Ether',logo_url:icon('WETH'),networks:['BEP20','ERC20']},
 BTCB:{name:'Bitcoin BEP20',logo_url:icon('BTCB'),networks:['BEP20']},
 POL:{name:'Polygon Ecosystem Token',logo_url:icon('POL'),networks:['POLYGON']},
 BTC:{name:'Bitcoin',logo_url:icon('BTC'),networks:['BITCOIN']},
});
export const ORIGINAL_NETWORK_LABELS=Object.freeze({
 BEP20:'BNB Smart Chain (BSC)',TRC20:'Tron (TRX)',
 ERC20:'Ethereum (ETH)',ARBITRUM:'Arbitrum One (ARB)',BASE:'Base',
 POLYGON:'Polygon (POL)',SOL:'Solana (SOL)',BITCOIN:'Bitcoin (BTC)',
});
export const ORIGINAL_PRICE_IDS=Object.freeze({
 USDT:'tether',USDC:'usd-coin',DAI:'dai',TUSD:'true-usd',
 TRX:'tron',BNB:'binancecoin',ETH:'ethereum',SOL:'solana',
 BTC:'bitcoin',PAXG:'pax-gold',PYUSD:'paypal-usd',
 POL:'polygon-ecosystem-token',
});
const PRICE_ALIASES={WBTC:'BTC',BTCB:'BTC',WETH:'ETH'};
const LEGACY=['USDT','USDC'];
export function normalizeOriginalRemittanceAsset(value,v2=false){
 const asset=String(value||'').trim().toUpperCase();
 if(!Object.hasOwn(ORIGINAL_ASSETS,asset)||
    (!v2&&!LEGACY.includes(asset)))throw Error('ORIGINAL_REMITTANCE_ASSET_NOT_ENABLED');
 return asset;
}
export function normalizeOriginalRemittanceNetwork(asset,value){
 const raw=String(value||'').trim().toUpperCase();
 const network=raw==='SOLANA'?'SOL':raw==='BTC'?'BITCOIN':raw;
 if(!ORIGINAL_ASSETS[asset]?.networks.includes(network))
   throw Error('ORIGINAL_REMITTANCE_NETWORK_NOT_SUPPORTED');
 return network;
}
function validWallet(value) {
 const text=String(value||'').trim();
 return text.length>=8 && text.length<=180 && !/\s/.test(text);
}
function originalWalletObject(env) {
 const raw=env.REMITTANCE_WALLETS_JSON??env.SARAF_REMITTANCE_WALLETS_JSON??'{}';
 let parsed;
 try{parsed=JSON.parse(raw);}catch{throw Error('ORIGINAL_REMITTANCE_WALLETS_INVALID');}
 if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))
   throw Error('ORIGINAL_REMITTANCE_WALLETS_INVALID');
 return parsed;
}
export function originalRemittanceWallets(env={},v2=false){
 const json=originalWalletObject(env);
 let usdtFallback={};
 try{usdtFallback=JSON.parse(env.SARAF_USDT_DEPOSIT_WALLETS_JSON||
  env.USDT_DEPOSIT_WALLETS_JSON||'{}');}catch{}
 const available={};
 for(const [asset,meta] of Object.entries(ORIGINAL_ASSETS)){
  if(!v2&&!LEGACY.includes(asset))continue;
  const networks={};
  for(const network of meta.networks){
   const lookup=json[asset];
   const primary=lookup&&typeof lookup==='object'&&!Array.isArray(lookup)
     ?lookup[network]:undefined;
   const configured=primary||env['REMITTANCE_'+asset+'_'+network+'_WALLET']||
    (asset==='USDT'?usdtFallback?.[network]:null);
   if(validWallet(configured))networks[network]=String(configured).trim();
  }
  if(Object.keys(networks).length)available[asset]=networks;
 }
 return available;
}
export function originalRemittanceConfig(env={},v2=false) {
 const wallets=originalRemittanceWallets(env,v2);
 return Object.entries(wallets).map(([asset,networks])=>({
  asset,name:ORIGINAL_ASSETS[asset].name,logo_url:ORIGINAL_ASSETS[asset].logo_url,
  networks:Object.keys(networks).map(code=>({
    code,label:ORIGINAL_NETWORK_LABELS[code]||code,
  })),
 }));
}
export async function originalAssetPriceUsd(asset,http=fetch) {
 const normalized=normalizeOriginalRemittanceAsset(asset,true);
 const underlying=PRICE_ALIASES[normalized]||normalized;
 const id=ORIGINAL_PRICE_IDS[underlying];
 if(!id)throw Error('ORIGINAL_REMITTANCE_PRICE_SOURCE_MISSING');
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),10000);
 try{
  const qs=new URLSearchParams({ids:id,vs_currencies:'usd'});
  const response=await http('https://api.coingecko.com/api/v3/simple/price?'+qs,{
   signal:controller.signal,headers:{Accept:'application/json'},
  });
  if(!response?.ok)throw Error('ORIGINAL_REMITTANCE_PRICE_UNAVAILABLE');
  const data=await response.json();
  const n=Number(data?.[id]?.usd);
  if(!Number.isFinite(n)||n<=0||n>1e10)
    throw Error('ORIGINAL_REMITTANCE_PRICE_UNAVAILABLE');
  return {price:n,source:'CoinGecko'};
 }finally{clearTimeout(timer);}
}
const money=n=> {
 if(!Number.isFinite(Number(n))||Number(n)<0)
  throw Error('ORIGINAL_REMITTANCE_INVALID_AMOUNT');
 // Convert JS numeric form into a fixed decimal input for exactMoney;
 // original UI passes numbers but the Python backend uses Decimal(str()).
 const v=Number(n);
 if(v!==0 && v<0.00000001)throw Error('ORIGINAL_REMITTANCE_INVALID_AMOUNT');
 return v.toFixed(8).replace(/0+$/,'').replace(/\.$/,'')||'0';
};
export function originalRemittanceValuation({
 amount,asset,network,priceUsd,usdRate,feePercent=0,minUsd=10,maxUsd=10000,
 depositWallet,v2=false,
}){
 const type=normalizeOriginalRemittanceAsset(asset,v2);
 const net=normalizeOriginalRemittanceNetwork(type,network);
 if(!validWallet(depositWallet)||!Number.isFinite(Number(priceUsd))||
    Number(priceUsd)<=0||!Number.isFinite(Number(usdRate))||
    Number(usdRate)<=0)throw Error('ORIGINAL_REMITTANCE_CONFIGURATION_INVALID');
 const units=exactMoney.parse(money(amount));
 if(units<=0n)throw Error('ORIGINAL_REMITTANCE_INVALID_AMOUNT');
 const price=exactMoney.parse(money(priceUsd));
 const usdValueDecimal=exactMoney.multiply(units,price);
 const value=exactMoney.toNumber(usdValueDecimal);
 if(value<Number(minUsd)||value>Number(maxUsd))
  throw Error('ORIGINAL_REMITTANCE_USD_LIMIT');
 const quote=originalRemittancePricing(
   money(value),money(usdRate),money(feePercent));
 const quantUsd=n=>Math.round(n*100)/100;
 return {
  asset:type,network:net,crypto_amount:exactMoney.toNumber(units),
  asset_price_usd:Number(priceUsd),
  asset_price_source:'CoinGecko',
  usd_value:quantUsd(value),usd_rate:quote.usd_rate,
  gross_afn:quote.gross_afn,fee_percent:quote.fee_percent,
  fee_afn:quote.fee_afn,payout_afn:quote.payout_afn,
  deposit_wallet:String(depositWallet).trim(),
 };
}
