// STAGED ORIGINAL SARAF Financial API (NOT deployed).
// Port of main: services/usdt_service.py, quote_service.py,
// stablecoin_networks.py, usdt_api_guard.py, usdt_order_service.py.
// It reuses ORIGINAL usdt_quotes/usdt_orders/user_profiles tables only.
// Never accepts client-supplied prices, chat_id, payout status or wallets.
import {createClient} from 'npm:@supabase/supabase-js@2.57.0';
import {verifyTelegramInitData} from './telegram-auth.mjs';
import {originalBuyPricing,originalSellPricing,originalRemittancePricing}
 from './pricing.mjs';
import {selectOriginalBasis} from './rates.mjs';
import {fetchOriginalCurrencyRates,fetchOriginalLocalMarkets} from './markets.mjs';
import {
 originalRemittanceWallets,originalRemittanceConfig,originalAssetPriceUsd,
 ORIGINAL_ASSETS,
 originalRemittanceValuation,
} from './remittance.mjs';
import {originalRiskLevel} from './risk.mjs';

const ORIGIN='https://app8533795882.tgcloud.ai';
const TOKEN=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const SUPABASE=Deno.env.get('SUPABASE_URL')||'https://cvernmhpnsgdtegvblyc.supabase.co';
const LIVE=Deno.env.get('SARAF_ORIGINAL_FINANCIAL_API_ENABLED')==='true';
const ADMINS=(Deno.env.get('SARAF_ADMIN_CHAT_IDS')||'').split(',')
 .map(x=>x.trim()).filter(x=>/^[1-9][0-9]{0,15}$/.test(x));
const ADMIN_TOKEN=Deno.env.get('SARAF_ADMIN_BOT_TOKEN')||'';
const TYPES={
 USDT:[
  {code:'TRC20',label:'Tron (TRC20)',family:'tron'},
  {code:'ERC20',label:'Ethereum (ERC20)',family:'evm'},
  {code:'BEP20',label:'BNB Smart Chain (BEP20)',family:'evm'},
 ],
 USDC:[
  {code:'BEP20',label:'BNB Smart Chain',family:'evm'},
  {code:'ERC20',label:'Ethereum',family:'evm'},
  {code:'ARBITRUM',label:'Arbitrum One',family:'evm'},
  {code:'BASE',label:'Base',family:'evm'},
  {code:'POLYGON',label:'Polygon PoS',family:'evm'},
  {code:'SOLANA',label:'Solana',family:'solana'},
  {code:'AVALANCHE',label:'Avalanche C-Chain',family:'evm'},
  {code:'OPTIMISM',label:'OP Mainnet',family:'evm'},
 ],
};
type Asset='USDT'|'USDC';
type Json=Record<string,unknown>;
function out(origin:string,status:number,value:unknown){
 return new Response(JSON.stringify(value),{status,headers:{
  'Content-Type':'application/json;charset=utf-8','Cache-Control':'no-store',
  'Vary':'Origin',...(origin===ORIGIN?{'Access-Control-Allow-Origin':ORIGIN}:{}),
  'Access-Control-Allow-Headers':'X-Telegram-Init-Data,Content-Type',
  'Access-Control-Allow-Methods':'POST,OPTIONS',
 }});
}
class Denied extends Error{
 constructor(public code:string,public status=400){super(code);}
}
const deny=(name:string,status=400):never=>{throw new Denied(name,status);};
const asset=(x:unknown):Asset=>{
 const v=String(x||'USDT').toUpperCase();
 if(v!=='USDT'&&v!=='USDC')deny('ASSET_NOT_SUPPORTED');
 return v as Asset;
};
const amount=(x:unknown)=>{
 const n=Number(x);
 if(typeof x==='boolean'||x==null||!Number.isFinite(n)||n<10||n>10000)
  deny('INVALID_TRADE_AMOUNT');
 return n;
};
function methodNetworks(kind:Asset,network:unknown,direction:'buy'|'sell',wallets:Json){
 const n=String(network||'').toUpperCase();
 if(!TYPES[kind].some(x=>x.code===n))deny('NETWORK_NOT_SUPPORTED');
 if(direction==='sell'&&!wallets[n])deny('DEPOSIT_WALLET_NOT_CONFIGURED');
 return n;
}
const walletShape=(network:string,address:string)=>{
 const v=String(address||'').trim();
 if(v.length<8||v.length>128||/\s/.test(v))return false;
 if(['ERC20','BEP20','ARBITRUM','BASE','POLYGON','AVALANCHE','OPTIMISM'].includes(network))
  return /^0x[0-9a-fA-F]{40}$/.test(v);
 if(network==='TRC20')return /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(v);
 if(network==='SOLANA')return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(v);
 return false;
};
function remittanceV2Enabled(){
 return (Deno.env.get('REMITTANCE_V2_ENABLED')||
    Deno.env.get('SARAF_REMITTANCE_V2_ENABLED')||'false')
    .toLowerCase()==='true';
}
function remittanceEnv():Record<string,string>{
 // Original main:services/remittance_wallet_config.py uses environment
 // configuration supplied by the operator. Never hardcode deposit wallets.
 const names=['REMITTANCE_WALLETS_JSON','SARAF_REMITTANCE_WALLETS_JSON',
  'SARAF_USDT_DEPOSIT_WALLETS_JSON','USDT_DEPOSIT_WALLETS_JSON'];
 const config:Record<string,string>={};
 for(const name of names)config[name]=Deno.env.get(name)||'';
 for(const [asset,metadata] of Object.entries(ORIGINAL_ASSETS)){
  for(const net of metadata.networks){
   const name='REMITTANCE_'+asset+'_'+net+'_WALLET';
   config[name]=Deno.env.get(name)||'';
  }
 }
 return config;
}
function remittancePercent(){
 const raw=Deno.env.get('REMITTANCE_FEE_PERCENT')||
   Deno.env.get('SARAF_REMITTANCE_FEE_PERCENT')||'0';
 const rate=Number(raw);
 if(!Number.isFinite(rate)||rate<0||rate>25)
   deny('REMITTANCE_FEE_NOT_CONFIGURED',503);
 return rate;
}
function remittanceLimit(name:string,defaultValue:number){
 const value=Number(Deno.env.get(name)||String(defaultValue));
 if(!Number.isFinite(value)||value<=0||value>1000000)
  deny('ORIGINAL_REMITTANCE_LIMIT_INVALID',503);
 return value;
}
async function remittancePreview(input:Json,rate:number,feePercent:number,
  assetPrice?:{price:number,source:string}){
 const v2=remittanceV2Enabled();
 const asset=String(input.asset||'').toUpperCase();
 const network=String(input.network||'').toUpperCase();
 const wallets=originalRemittanceWallets(remittanceEnv(),v2);
 const net=network==='SOLANA'?'SOL':network==='BTC'?'BITCOIN':network;
 const deposit=wallets?.[asset]?.[net];
 if(!deposit)deny('DEPOSIT_WALLET_NOT_CONFIGURED',503);
 const price=assetPrice||await originalAssetPriceUsd(asset);
 let quote;
 try{
  quote=originalRemittanceValuation({
    asset,network:net,amount:input.amount,priceUsd:price.price,
    usdRate:rate,feePercent,depositWallet:deposit,v2,
    minUsd:remittanceLimit('REMITTANCE_MIN_USD',10),
    maxUsd:remittanceLimit('REMITTANCE_MAX_USD',10000),
  });
 }catch{deny('ORIGINAL_REMITTANCE_INVALID_QUOTE');}
 return {...quote,basis:'local_or_reference',asset_price_source:price.source};
}
function wallets(kind:Asset):Json{
 // Same server-side source as main:services/stablecoin_networks.py.
 const env=kind==='USDT'?'SARAF_USDT_DEPOSIT_WALLETS_JSON':'SARAF_USDC_DEPOSIT_WALLETS_JSON';
 let config:unknown={};
 try{config=JSON.parse(Deno.env.get(env)||'{}');}catch{return {};}
 if(!config||typeof config!=='object'||Array.isArray(config))return {};
 const map:Json={};
 for(const item of TYPES[kind]){
  const addr=(config as Json)[item.code];
  if(addr&&walletShape(item.code,String(addr)))map[item.code]=String(addr);
 }
 return map;
}
async function originalRates(db:any):Promise<any>{
 // Match original rate_engine: LIVE Sarai Shahzada first, LIVE reference
 // second; last cached history is allowed only within 20 minutes.
 let references:any={};
 let local:any={};
 try{references=await fetchOriginalCurrencyRates();}catch{}
 try{local=await fetchOriginalLocalMarkets();}catch{}
 const freshness=new Date(Date.now()-20*60*1000).toISOString();
 if(!(Number(references.usd)>0)){
  const r=await db.from('currency_history').select('afn_rate')
   .eq('currency','usd').gte('recorded_at',freshness)
   .order('recorded_at',{ascending:false}).limit(1).maybeSingle();
  if(!r.error && Number(r.data?.afn_rate)>0)references.usd=r.data!.afn_rate;
 }
 const sarai=(local as Json).sarai_shahzada as Json|undefined;
 const localUsd=sarai?.usd as Json|undefined;
 if(!(Number(localUsd?.buy)>0&&Number(localUsd?.sell)>0)){
  const r=await db.from('local_market_history').select('buy,sell')
   .eq('market','sarai_shahzada').eq('currency','usd')
   .gte('recorded_at',freshness).order('recorded_at',{ascending:false})
   .limit(1).maybeSingle();
  if(!r.error&&Number(r.data?.buy)>0&&Number(r.data?.sell)>0)
    local={sarai_shahzada:{usd:{buy:Number(r.data.buy),sell:Number(r.data.sell)}}};
 }
 const spread=await db.from('spread_settings')
  .select('spread_percent').eq('currency','usd').maybeSingle();
 if(spread.error)deny('RATE_SERVICE_UNAVAILABLE',503);
 const pct=spread.data?.spread_percent==null?{}:{usd:Number(spread.data.spread_percent)};
 try{return selectOriginalBasis('usd',references,local,pct);}
 catch{deny('RATE_SERVICE_UNAVAILABLE',503);}
}
function safeQuote(q:Json){
 // These fields match ORIGINAL Mini App return contract, no extra fee.
 return q;
}
async function notifyAdmin(text:string){
 if(!ADMINS.length||!ADMIN_TOKEN)return;
 await Promise.allSettled(ADMINS.map(async chat=>{
  const response=await fetch('https://api.telegram.org/bot'+ADMIN_TOKEN+'/sendMessage',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({chat_id:chat,text}),signal:AbortSignal.timeout(7000),
  });
  if(!response.ok)console.warn('Saraf admin alert non-200',response.status);
 }));
}
Deno.serve(async req=>{
 const origin=req.headers.get('Origin')||'';
 if(req.method==='OPTIONS')return origin===ORIGIN
   ?new Response(null,{status:204,headers:{
       'Access-Control-Allow-Origin':ORIGIN,
       'Access-Control-Allow-Headers':'Content-Type,X-Telegram-Init-Data',
       'Access-Control-Allow-Methods':'POST,OPTIONS',
      }})
   :out('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(req.method!=='POST')return out(origin,405,{error:'METHOD_NOT_ALLOWED'});
 if(origin && origin!==ORIGIN)return out('',403,{error:'ORIGIN_NOT_ALLOWED'});
 if(!TOKEN||!KEY)return out(origin,503,{error:'SERVICE_NOT_CONFIGURED'});
 const user=await verifyTelegramInitData(
   req.headers.get('X-Telegram-Init-Data')||'',TOKEN);
 if(!user)return out(origin,401,{error:'INVALID_TELEGRAM_AUTH'});
 if(!LIVE)return out(origin,503,{error:'ORIGINAL_FINANCIAL_API_DISABLED'});
 let body:Json;
 try{
  const raw=await req.text();
  if(raw.length>12000)deny('PAYLOAD_TOO_LARGE',413);
  const p=JSON.parse(raw);
  if(!p||typeof p!=='object'||Array.isArray(p))deny('INVALID_REQUEST');
  body=p as Json;
 }catch{return out(origin,400,{error:'INVALID_JSON'});}
 const db=createClient(SUPABASE,KEY,{
  auth:{persistSession:false,autoRefreshToken:false},
 });
 const action=String(body.action||'');
 const input=(body.input||{}) as Json;
 try{
  if(!input||typeof input!=='object'||Array.isArray(input))
    deny('INVALID_INPUT');
  if(action==='payment.info'){
   // Original main:api.py /api/usdt/payment-info uses BANK_* config.py.
   // Never invent/hardcode a different settlement bank account.
   const bank_name=Deno.env.get('BANK_NAME')||'';
   const bank_account_holder=Deno.env.get('BANK_ACCOUNT_HOLDER')||'';
   const bank_account_number=Deno.env.get('BANK_ACCOUNT_NUMBER')||'';
   if(!bank_name||!bank_account_holder||!bank_account_number)
    return out(origin,503,{error:'ORIGINAL_BANK_DETAILS_NOT_CONFIGURED'});
   return out(origin,200,{bank_name,bank_account_holder,bank_account_number});
  }
  if(action==='stablecoins.config'){
   return out(origin,200,Object.fromEntries(
    (['USDT','USDC'] as Asset[]).map(type=>{
     const addresses=wallets(type);
     return [type,{buy_networks:TYPES[type],
      sell_networks:TYPES[type].filter(n=>addresses[n.code]).map(n=>({
       ...n,deposit_address:addresses[n.code]}))}];
    })));
  }
  if(action==='remittances.config'){
    const pct=remittancePercent();
    const assets=originalRemittanceConfig(remittanceEnv(),remittanceV2Enabled());
    return out(origin,200,{
      assets,fee_percent:pct,
      identity_verification_threshold_usd:
       Number(Deno.env.get('USDT_IDENTITY_VERIFICATION_THRESHOLD_USD')||250),
      min_usd:remittanceLimit('REMITTANCE_MIN_USD',10),
      max_usd:remittanceLimit('REMITTANCE_MAX_USD',10000),
    });
  }
  if(action==='remittances.quote'||action==='remittances.create'){
    const fee=remittancePercent();
    // Original live USD FX and CoinGecko asset prices are independent.
    // Fetch them concurrently so the 18s signed Mini App timeout is respected.
    const [rate,price]=await Promise.all([
      originalRates(db),originalAssetPriceUsd(String(input.asset||'').toUpperCase()),
    ]);
    const quote=await remittancePreview(input,rate.saraf_quote.buy,fee,price);
    quote.basis=rate.saraf_quote.basis;
    if(action==='remittances.quote')return out(origin,200,quote);
    if(!ADMINS.length||!ADMIN_TOKEN)
      deny('ADMIN_REVIEW_NOT_CONFIGURED',503);
    const key=String(input.idempotency_key||'').trim();
    if(key.length<1||key.length>120)deny('IDEMPOTENCY_KEY_REQUIRED');
    const ownPath=String(input.beneficiary_id_document_path||'').trim();
    const prefix='remittances/'+user.id+'/';
    if(!ownPath.startsWith(prefix)||ownPath.includes('..')
      ||ownPath.length>500)deny('OWN_BENEFICIARY_ID_REQUIRED');
    const fileName=ownPath.slice(prefix.length);
    if(!/^[a-f0-9]{32}\.(jpg|png|webp)$/.test(fileName))
       deny('INVALID_BENEFICIARY_DOCUMENT');
    const listed=await db.storage.from('usdt-kyc-docs').list(prefix.slice(0,-1),{
      search:fileName,limit:2,
    });
    if(listed.error||!listed.data?.some(x=>x.name===fileName))
      deny('BENEFICIARY_DOCUMENT_NOT_FOUND');
    const profile=await db.from('user_profiles').select('phone')
      .eq('chat_id',user.id).maybeSingle();
    if(profile.error||!profile.data?.phone)
      deny('BASIC_PROFILE_REQUIRED',403);
    // Matches original V2: KYC threshold is USD value, not raw crypto count.
    if(!quote||!Number.isFinite(Number(quote.usd_value)))
      deny('ORIGINAL_REMITTANCE_INVALID_QUOTE',503);
    if(Number(quote.usd_value)>
      remittanceLimit('USDT_IDENTITY_VERIFICATION_THRESHOLD_USD',250)){
      const verified=await db.from('user_profiles').select(
        'kyc_status,id_document_path,selfie_path')
        .eq('chat_id',user.id).maybeSingle();
      if(verified.error||!['verified','trusted'].includes(
        String(verified.data?.kyc_status||''))||
        !verified.data?.id_document_path||!verified.data?.selfie_path)
        deny('IDENTITY_VERIFICATION_REQUIRED',403);
    }
   const beneficiary=(key:string)=>{
      const v=String(input[key]||'').trim();
      if(!v)deny('BENEFICIARY_FIELDS_REQUIRED');
      return v;
    };
    const rpc=await db.rpc('saraf_original_create_remittance',{
      p_chat_id:user.id,p_idempotency_key:key,
      p_asset:quote.asset,p_network:quote.network,
      p_amount:quote.crypto_amount,p_usd_rate:quote.usd_rate,
      p_gross_afn:quote.gross_afn,p_fee_percent:quote.fee_percent,
      p_fee_afn:quote.fee_afn,p_payout_afn:quote.payout_afn,
      p_asset_price_usd:quote.asset_price_usd,p_usd_value:quote.usd_value,
      p_kyc_threshold:remittanceLimit('USDT_IDENTITY_VERIFICATION_THRESHOLD_USD',250),
      p_deposit_wallet:quote.deposit_wallet,
      p_sender_name:beneficiary('sender_full_name'),
      p_sender_country:beneficiary('sender_country'),
      p_sender_phone:profile.data!.phone,
      p_beneficiary_name:beneficiary('beneficiary_full_name'),
      p_beneficiary_phone:beneficiary('beneficiary_phone'),
      p_province:beneficiary('beneficiary_province'),
      p_city:beneficiary('beneficiary_city'),
      p_address:beneficiary('beneficiary_address'),
      p_beneficiary_document:ownPath,
    });
    if(rpc.error)return out(origin,503,{
      error:rpc.error.code==='P0001'?rpc.error.message:'DATABASE_UNAVAILABLE'});
    if(rpc.data&&!rpc.data.duplicate){
      // Original remittance_service.create_order notifies admins only after
      // first successful insert. No money moves before manual approval.
      await notifyAdmin('💸 حوالهٔ جدید صراف — بررسی دستی الزامی است\n'+
        'کد: '+rpc.data.order_code+'\nشناسهٔ فرستنده: '+user.id+
        '\nدارایی: '+quote.asset+' / '+quote.network+
        '\nمقدار: '+quote.crypto_amount+'\nارزش دلاری: '+quote.usd_value+
        '\nپرداخت افغانی: '+quote.payout_afn);
    }
    return out(origin,200,rpc.data);
  }
  if(action==='remittances.tx'){
    const orderId=Number(input.order_id),hash=String(input.tx_hash||'').trim();
    if(!Number.isSafeInteger(orderId)||orderId<=0
      ||hash.length<12||hash.length>200)deny('INVALID_TX_HASH');
    if(!ADMINS.length||!ADMIN_TOKEN)
      deny('ADMIN_REVIEW_NOT_CONFIGURED',503);
    const saved=await db.rpc('saraf_original_claim_remittance_tx',{
     p_chat_id:user.id,p_order_id:orderId,p_tx_hash:hash,
    });
    if(saved.error)return out(origin,503,{
      error:saved.error.code==='P0001'?saved.error.message:'DATABASE_UNAVAILABLE'});
    await notifyAdmin('💸 حوالهٔ صراف — ثبت TX\n'+
      'کد: '+saved.data?.order_code+'\nشناسهٔ کاربر: '+user.id+
      '\nشناسه تراکنش: '+hash+'\nلطفاً حواله را در پنل اصلی بررسی کنید.');
    return out(origin,200,saved.data);
  }
  if(action==='card.preview'){
    // Original Python card-preview checks signed identity, active quote,
    // exact amount, exchange and asset/network wallet before image rendering.
    // Browser rasterization avoids Railway and never uploads private media.
    const side=String(input.action||''),type=asset(input.asset),a=amount(input.amount);
    if(side!=='buy'&&side!=='sell')deny('INVALID_ORDER_TYPE');
    const qid=Number(input.quote_id);
    if(!Number.isSafeInteger(qid)||qid<=0)deny('INVALID_QUOTE_ID');
    const q=await db.from('usdt_quotes').select(
      'id,order_type,asset,usdt_amount,usd_rate,fee_percent,total_afn,total_usd,status,expires_at'
     ).eq('id',qid).eq('chat_id',user.id).maybeSingle();
    if(q.error)deny('QUOTE_UNAVAILABLE',503);
    if(!q.data||q.data!.order_type!==side||q.data!.asset!==type
       ||Math.abs(Number(q.data!.usdt_amount)-a)>0.0000001)
      deny('QUOTE_MISMATCH',409);
    if(q.data!.status!=='active'||Date.parse(q.data!.expires_at)<=Date.now())
      deny('QUOTE_EXPIRED_OR_CONSUMED',409);
    const exchange=String(input.exchange_name||'').trim();
    if(!exchange||exchange.length>200)deny('EXCHANGE_REQUIRED');
    const depositWallets=wallets(type);
    const network=methodNetworks(type,input.network,side as 'buy'|'sell',depositWallets);
    const wallet=String(input.wallet_address||'').trim();
    if(side==='buy'&&!walletShape(network,wallet))deny('INVALID_WALLET_ADDRESS');
    const profile=await db.from('user_profiles').select('first_name,last_name,phone,kyc_status,trust_score,successful_orders,selfie_path,cancelled_orders,payment_info_change_count,restricted_reason').eq('chat_id',user.id).maybeSingle();
    if(profile.error)deny('PROFILE_UNAVAILABLE',503);
    if(!profile.data?.first_name||!profile.data!.last_name||!profile.data!.phone)
      deny('BASIC_PROFILE_REQUIRED',403);
    const risk=originalRiskLevel(profile.data!,a,{
      USDT_RISK_HIGH_AMOUNT_THRESHOLD:
       Deno.env.get('USDT_RISK_HIGH_AMOUNT_THRESHOLD')||'1000',
      USDT_RISK_NEW_USER_ORDER_THRESHOLD:
       Deno.env.get('USDT_RISK_NEW_USER_ORDER_THRESHOLD')||'3',
      USDT_RISK_CANCEL_COUNT_THRESHOLD:
       Deno.env.get('USDT_RISK_CANCEL_COUNT_THRESHOLD')||'3',
      USDT_RISK_PAYMENT_CHANGE_THRESHOLD:
       Deno.env.get('USDT_RISK_PAYMENT_CHANGE_THRESHOLD')||'3',
    });
    // Private selfie path is NEVER sent to the browser; only a 60-second
    // storage-signed URL for the correctly authenticated Telegram owner.
    let selfie_url:null|string=null;
    if(profile.data!.selfie_path){
      const bucket=Deno.env.get('USDT_KYC_DOCS_BUCKET')||'usdt-kyc-docs';
      const signed=await db.storage.from(bucket).createSignedUrl(
        String(profile.data!.selfie_path),60);
      if(!signed.error&&signed.data?.signedUrl)
        selfie_url=signed.data.signedUrl;
    }
    return out(origin,200,{
      order_preview:{
        order_type:side,asset:type,usdt_amount:Number(q.data!.usdt_amount),
        usd_rate:Number(q.data!.usd_rate),
        fee_percent:Number(q.data!.fee_percent||0),
        total_afn:Number(q.data!.total_afn),total_usd:Number(q.data!.total_usd),
        exchange_name:exchange,network,risk_level:risk.level,
        wallet_address:side==='buy'?wallet:String(depositWallets[network]||''),
        deposit_address:side==='sell'?String(depositWallets[network]||''):null,
      },
      selfie_url,
      profile:{
        first_name:profile.data!.first_name,last_name:profile.data!.last_name,
        phone:profile.data!.phone,kyc_status:profile.data!.kyc_status,
        trust_score:profile.data!.trust_score,
        successful_orders:profile.data!.successful_orders,
      },
    });
  }
  if(action==='quote'){
   const type=asset(input.asset),a=amount(input.amount);
   const side=String(input.action);
   if(!['buy','sell'].includes(side))deny('INVALID_ORDER_TYPE');
   const rate=await originalRates(db);
   const localSell=rate.local?.sell;
   const usdRate=side==='buy'
    ?localSell||rate.saraf_quote.sell:rate.saraf_quote.buy;
   const pricing:any=side==='buy'
    ?originalBuyPricing(String(a),String(usdRate))
    :originalSellPricing(String(a),String(usdRate));
   const values:Json={
    chat_id:user.id,order_type:side,asset:type,
    usdt_amount:a,usd_rate:pricing.usd_rate??usdRate,
    fee_percent:0,total_afn:pricing.total_afn,
    total_usd:side==='buy'?pricing.customer_payable_usd:pricing.total_usd,
    status:'active',expires_at:new Date(Date.now()+600000).toISOString(),
   };
   if(side==='buy'){
    values.pricing_model='local_margin_share_50_30_20';
    for(const name of ['market_margin_usd','supplier_profit_usd',
     'saraf_profit_usd','customer_discount_usd','supplier_payout_usd',
     'market_price_usd','supplier_profit_afn','saraf_profit_afn',
     'customer_discount_afn','supplier_payout_afn','market_price_afn']){
      values[name]=(pricing as Json)[name];
    }
   }
   const stored=await db.from('usdt_quotes').insert(values)
    .select('id,expires_at').single();
   if(stored.error || !stored.data)deny('QUOTE_STORE_FAILED',503);
   return out(origin,200,safeQuote({
    ...pricing,asset:type,amount:a,
    usd_rate:values.usd_rate,fee_percent:0,
    fee_afn:0,original_fee_percent:0,
    basis:side==='buy'&&localSell?'local_sell':rate.saraf_quote.basis,
    total_usd:values.total_usd,
    payable_usd:side==='buy'?values.total_usd:undefined,
    pricing_model:side==='buy'?'local_margin_share_50_30_20':undefined,
    quote_id:stored.data!.id,expires_at:stored.data!.expires_at,
   }));
  }
  if(action==='order.buy'||action==='order.sell'){
   if(!ADMINS.length||!ADMIN_TOKEN)
     deny('ADMIN_REVIEW_NOT_CONFIGURED',503);
   const side=action.split('.')[1],type=asset(input.asset),a=amount(input.amount);
   const quoteId=Number(input.quote_id);
   const key=String(input.idempotency_key||'').trim();
   if(!Number.isSafeInteger(quoteId)||quoteId<=0
      ||key.length<16||key.length>200)
     deny('QUOTE_OR_IDEMPOTENCY_REQUIRED');
   const addresses=wallets(type);
   const network=methodNetworks(type,input.network,side as 'buy'|'sell',addresses);
   const method=String(input.payment_method||input.receive_method||'');
   if(!['online','in_person'].includes(method))deny('INVALID_PAYMENT_METHOD');
   const provider=String(input.payment_provider||input.receive_provider||'').toLowerCase();
   if(method==='online' && (!['hesabpay','azizi'].includes(provider)
     ||(provider==='azizi'&&a<=500)))deny('INVALID_PAYMENT_PROVIDER');
   const exchange=String(input.exchange_name||'').trim();
   if(!exchange||exchange.length>200)deny('EXCHANGE_REQUIRED');
   const inCode=String(input.in_person_code||'');
   if(method==='in_person'&&!/^[0-9]{4}$/.test(inCode))
     deny('INVALID_IN_PERSON_CODE');
   const details:Json={
    network,method,provider,exchange_name:exchange,in_person_code:inCode,
    telegram_username:String(user.username||'').slice(0,80),
    telegram_full_name:[user.first_name,user.last_name].filter(Boolean)
     .join(' ').slice(0,160),
   };
   if(side==='buy'){
    const wallet=String(input.wallet_address||'').trim();
    if(!walletShape(network,wallet))deny('INVALID_WALLET_ADDRESS');
    details.wallet_address=wallet;
    if(method==='online'){
     const raw=String(input.receipt_url||input.receipt_file_id||'');
     let link:URL|null=null;
     try{link=new URL(raw);}catch{deny('OWN_RECEIPT_REQUIRED');}
     if(!link)deny('OWN_RECEIPT_REQUIRED');
     if(link!.origin!==new URL(SUPABASE).origin ||
       !link!.pathname.startsWith('/storage/v1/object/sign/usdt-receipts/'+user.id+'_')
       ||!link!.searchParams.get('token'))deny('OWN_RECEIPT_REQUIRED');
     // Supabase independently authenticates the signature before accepting
     // a receipt claim. A fabricated path is NOT sufficient.
     const image=await fetch(link!.href,{method:'GET',
      signal:AbortSignal.timeout(5500)});
     if(!image.ok)deny('OWN_RECEIPT_UNAVAILABLE');
     details.receipt_file_id=link!.href;
    }
   }else{
    const proof=String(input.tx_proof||'').trim();
    if(proof.length<8||proof.length>1500)deny('TX_PROOF_REQUIRED');
    details.tx_proof=proof;
    if(method==='online'){
      const bank=String(input.bank_info||'').trim();
      if(bank.length<4||bank.length>1200)deny('BANK_INFO_REQUIRED');
      details.bank_info=bank;
    }
   }
   const rpc=await db.rpc('saraf_original_submit_usdt_order',{
    p_chat_id:user.id,p_quote_id:quoteId,p_action:side,
    p_asset:type,p_amount:a,p_idempotency_key:key,p_payload:details,
   });
   if(rpc.error){
    const code=rpc.error.code==='P0001'?rpc.error.message:'DATABASE_UNAVAILABLE';
    const safe=new Set(['INVALID_ORIGINAL_ORDER_INPUT','QUOTE_MISMATCH',
      'QUOTE_EXPIRED_OR_CONSUMED','IDEMPOTENCY_PAYLOAD_CONFLICT',
      'BASIC_PROFILE_REQUIRED','IDENTITY_VERIFICATION_REQUIRED',
      'ORIGINAL_ORDER_VALIDATION_FAILED','IN_PERSON_CODE_INVALID',
      'ONLINE_PROVIDER_INVALID','NETWORK_UNSUPPORTED','WALLET_INVALID',
      'OWN_RECEIPT_REQUIRED','TX_PROOF_REQUIRED','BANK_INFO_REQUIRED']);
    return out(origin,safe.has(code)?409:503,{
      error:safe.has(code)?code:'DATABASE_UNAVAILABLE'});
   }
   const item=rpc.data as Json;
   if(!item?.duplicate){
    await notifyAdmin('🆕 سفارش '+(side==='buy'?'خرید':'فروش')+' '+type+
     '\nکد: '+item.order_code+'\nمقدار: '+a+
     '\nکاربر: '+user.id+'\nشبکه: '+network+
     '\nوضعیت: pending — بررسی دستی الزامی است.');
   }
   return out(origin,200,{
     order_id:item.order_id,order_code:item.order_code,
     quote:{asset:type,amount:a},duplicate:item.duplicate,
     risk_level:item.risk_level,status:item.status,
   });
  }
  return out(origin,404,{error:'ORIGINAL_ROUTE_NOT_PORTED'});
 }catch(e){
  if(e instanceof Denied)return out(origin,e.status,{error:e.code});
  console.warn('Original Saraf port denied (no details)',String(e).slice(0,60));
  return out(origin,503,{error:'SERVICE_UNAVAILABLE'});
 }
});
