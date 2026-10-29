// STAGED ORIGINAL SARAF Financial API (NOT deployed).
// Port of main: services/usdt_service.py, quote_service.py,
// stablecoin_networks.py, usdt_api_guard.py, usdt_order_service.py.
// It reuses ORIGINAL usdt_quotes/usdt_orders/user_profiles tables only.
// Never accepts client-supplied prices, chat_id, payout status or wallets.
import {createClient} from 'npm:@supabase/supabase-js@2.57.0';
import {verifyTelegramInitData} from '../saraf-telegram-bridge/telegram-auth.mjs';
import {originalBuyPricing,originalSellPricing,originalRemittancePricing}
 from './pricing.mjs';
import {selectOriginalBasis} from './rates.mjs';
import {fetchOriginalCurrencyRates,fetchOriginalLocalMarkets} from './markets.mjs';

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
async function originalRates(db:ReturnType<typeof createClient>){
 // Match original rate_engine: LIVE Sarai Shahzada first, LIVE reference
 // second; last cached history is allowed only within 20 minutes.
 let references:Json={};
 let local:Json={};
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
  if(action==='stablecoins.config'){
   return out(origin,200,Object.fromEntries(
    (['USDT','USDC'] as Asset[]).map(type=>{
     const addresses=wallets(type);
     return [type,{buy_networks:TYPES[type],
      sell_networks:TYPES[type].filter(n=>addresses[n.code]).map(n=>({
       ...n,deposit_address:addresses[n.code]}))}];
    })));
  }
  if(action==='quote'){
   const type=asset(input.asset),a=amount(input.amount);
   const side=String(input.action);
   if(!['buy','sell'].includes(side))deny('INVALID_ORDER_TYPE');
   const rate=await originalRates(db);
   const localSell=rate.local?.sell;
   const usdRate=side==='buy'
    ?localSell||rate.saraf_quote.sell:rate.saraf_quote.buy;
   const pricing:Json=side==='buy'
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
   if(stored.error)deny('QUOTE_STORE_FAILED',503);
   return out(origin,200,safeQuote({
    ...pricing,asset:type,amount:a,
    usd_rate:values.usd_rate,fee_percent:0,
    fee_afn:0,original_fee_percent:0,
    basis:side==='buy'&&localSell?'local_sell':rate.saraf_quote.basis,
    total_usd:values.total_usd,
    payable_usd:side==='buy'?values.total_usd:undefined,
    pricing_model:side==='buy'?'local_margin_share_50_30_20':undefined,
    quote_id:stored.data.id,expires_at:stored.data.expires_at,
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
     let link:URL;
     try{link=new URL(raw);}catch{deny('OWN_RECEIPT_REQUIRED');}
     if(link.origin!==new URL(SUPABASE).origin ||
       !link.pathname.startsWith('/storage/v1/object/sign/usdt-receipts/'+user.id+'_')
       ||!link.searchParams.get('token'))deny('OWN_RECEIPT_REQUIRED');
     // Supabase independently authenticates the signature before accepting
     // a receipt claim. A fabricated path is NOT sufficient.
     const image=await fetch(link.href,{method:'GET',
      signal:AbortSignal.timeout(5500)});
     if(!image.ok)deny('OWN_RECEIPT_UNAVAILABLE');
     details.receipt_file_id=link.href;
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
