// Cron-only EVM stablecoin transfer verifier for canonical Saraf remittances.
// Deploy only after validating public RPC endpoints + TOKEN contracts + wallets.
// No private keys or automatic payouts. Disabled by default.
// Requires a dedicated long SARAF_BLOCKCHAIN_WATCHER_TOKEN as a server-side secret.
import { createClient } from 'npm:@supabase/supabase-js@2.57.0';
import { verifyEvmTransfer } from './evm.mjs';

const url=Deno.env.get('SUPABASE_URL')||'';
const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const cronToken=Deno.env.get('SARAF_BLOCKCHAIN_WATCHER_TOKEN')||'';
const enabled=Deno.env.get('SARAF_BLOCKCHAIN_WATCH_ENABLED')==='true';
const configRaw=Deno.env.get('SARAF_EVM_NETWORK_CONFIG_JSON')||'{}';
const results={ 'content-type':'application/json','cache-control':'no-store' };
const json=(status:number,body:unknown)=>new Response(JSON.stringify(body),{status,headers:results});
function equal(a:string,b:string) {
  if(a.length!==b.length)return false;
  let result=0;
  for(let i=0;i<a.length;i++)result|=a.charCodeAt(i)^b.charCodeAt(i);
  return result===0;
}
function decimal(units:string,precision:number){
  const n=BigInt(units);
  const base=10n**BigInt(precision);
  const integral=n/base;
  const frac=(n%base).toString().padStart(precision,'0').replace(/0+$/,'');
  return integral.toString()+(frac?'.'+frac:'');
}
function getConfiguredNetwork(config:Record<string,any>,asset:string,network:string) {
  const value=config?.[network]?.[asset];
  if(!value || typeof value!=='object')return null;
  const full={...value};
  if(!Number.isSafeInteger(full.chainId)||!Number.isSafeInteger(full.decimals)||
      !Number.isSafeInteger(full.minConfirmations)||
      full.minConfirmations<12 || full.minConfirmations>1000||
      typeof full.wallet!=='string'||typeof full.tokenContract!=='string'||
      typeof full.rpcUrl!=='string'||!full.rpcUrl.startsWith('https://'))
    return null;
  return full;
}
Deno.serve(async(req:Request)=>{
  if(req.method!=='POST')return json(405,{error:'METHOD_NOT_ALLOWED'});
  // NEVER accept the current request's Telegram ID as a cron/operator credential.
  const bearer=req.headers.get('authorization')||'';
  if(cronToken.length<32 || !equal(bearer,'Bearer '+cronToken))
    return json(401,{error:'UNAUTHORIZED'});
  if(!enabled)return json(503,{error:'BLOCKCHAIN_WATCH_DISABLED'});
  if(!url || !key)return json(503,{error:'DATABASE_NOT_CONFIGURED'});
  let configs:Record<string,any>;
  try{configs=JSON.parse(configRaw);}catch{return json(503,{error:'NETWORK_CONFIG_INVALID'});}
  const db=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:orders,error}=await db.from('remittance_orders').select(
    'id,asset,network,crypto_amount,deposit_wallet,tx_hash,status,verification_status'
  ).eq('status','transfer_submitted')
   .in('verification_status',['pending','confirming']).not('tx_hash','is',null)
   .limit(20);
  if(error)return json(503,{error:'DATABASE_QUERY_FAILED'});
  let verified=0,confirming=0,mismatch=0,unavailable=0;
  for(const order of orders||[]){
    const asset=String(order.asset||''),network=String(order.network||'');
    const config=getConfiguredNetwork(configs,asset,network);
    if(!config || String(order.deposit_wallet||'').toLowerCase()!==config.wallet.toLowerCase()){
      unavailable++;continue;
    }
    try{
      const result=await verifyEvmTransfer(config,{
        txHash:String(order.tx_hash),amount:String(order.crypto_amount),
      });
      const now=new Date().toISOString();
      const base={chain_last_checked_at:now};
      let changes:Record<string,unknown>=base;
      if(result.status==='verified'){
        const proof=result.proof;
        changes={...base,verification_status:'verified',
          chain_confirmations:proof.confirmations,
          chain_block_number:proof.blockNumber,
          chain_verified_amount:decimal(proof.verifiedUnits,config.decimals),
          chain_verified_asset:asset,chain_verified_network:network,
          chain_verified_at:now,chain_verification_error:null,
          chain_verification_meta:{blockHash:proof.blockHash,
            tokenContract:proof.tokenContract,logIndexes:proof.logIndexes}};
        verified++;
      }else if(result.status==='confirming') {
        changes={...base,verification_status:'confirming',
          chain_confirmations:result.proof.confirmations,
          chain_verification_error:null};
        confirming++;
      }else if(result.status==='mismatch'){
        changes={...base,verification_status:'mismatch',
          chain_verification_error:result.reason};
        mismatch++;
      }else {
        changes={...base,chain_verification_error:result.reason};
        unavailable++;
      }
      // Compare-and-swap prevents a stale worker overwriting a newer
      // transaction claim or a record already marked paid by an operator.
      const update=await db.from('remittance_orders').update(changes)
        .eq('id',order.id).eq('tx_hash',order.tx_hash)
        .eq('status','transfer_submitted')
        .in('verification_status',['pending','confirming']).select('id');
      if(update.error)throw update.error;
    }catch(error){
      unavailable++;
      console.warn('Verifier failed for an order',String(error).slice(0,80));
    }
  }
  return json(200,{ok:true,inspected:(orders||[]).length,verified,
    confirming,mismatch,unavailable});
});
