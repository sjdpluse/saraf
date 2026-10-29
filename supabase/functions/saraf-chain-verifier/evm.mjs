// Pure EVM receipt checker for Saraf USDT/USDC remittances.
// NEVER derive contract, destination wallet, chain ID or token decimals from
// the customer's input; these must be verified server-side configuration.
// No payout or financial status transition is implemented in this module.
const TRANSFER_TOPIC='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const HEX_ADDRESS=/^0x[0-9a-fA-F]{40}$/;
const HEX_TX=/^0x[0-9a-fA-F]{64}$/;
const RPC_TIMEOUT_MS=10000;

export function amountToTokenUnits(input,decimals) {
  if(!Number.isSafeInteger(decimals)||decimals<0||decimals>18)
    throw new Error('INVALID_TOKEN_DECIMALS');
  const s=String(input);
  if(!/^(0|[1-9][0-9]{0,18})(\.[0-9]{1,18})?$/.test(s))
    throw new Error('INVALID_AMOUNT');
  const [integer,fraction='']=s.split('.');
  if(fraction.length>decimals)
    throw new Error('AMOUNT_PRECISION_INVALID');
  return BigInt(integer)*10n**BigInt(decimals)
     +BigInt((fraction.padEnd(decimals,'0')||'0'));
}
function quantity(raw) {
  if(typeof raw!=='string'||!/^0x[0-9a-fA-F]+$/.test(raw))
    throw new Error('BAD_CHAIN_QUANTITY');
  return BigInt(raw);
}
function requiredString(value,regex) {
  if(typeof value!=='string'||!regex.test(value))throw new Error('CHAIN_CONFIG_INVALID');
  return value.toLowerCase();
}
function tokenReceiver(log) {
  if(!Array.isArray(log?.topics)||log.topics.length<3||
     typeof log.topics[2]!=='string'||!/^0x[0-9a-fA-F]{64}$/.test(log.topics[2]))
    return null;
  return '0x'+log.topics[2].slice(-40).toLowerCase();
}
export async function verifyEvmTransfer(config,request,http=fetch) {
  const expectedTx=requiredString(request?.txHash,HEX_TX);
  const wallet=requiredString(config?.wallet,HEX_ADDRESS);
  const contract=requiredString(config?.tokenContract,HEX_ADDRESS);
  const rpcUrl=config?.rpcUrl;
  if(typeof rpcUrl!=='string'||!rpcUrl.startsWith('https://')||
     !Number.isSafeInteger(config.chainId)||config.chainId<=0)
    throw new Error('CHAIN_CONFIG_INVALID');
  const decimals=config.decimals;
  const expectedUnits=amountToTokenUnits(request.amount,decimals);
  const confirmations=Math.max(12,Number(config.minConfirmations)||12);
  if(!Number.isSafeInteger(confirmations)||confirmations>1000)
    throw new Error('CHAIN_CONFIG_INVALID');
  const call=async(method,params)=>{
    const ctrl=new AbortController();
    const timer=setTimeout(()=>ctrl.abort(),RPC_TIMEOUT_MS);
    try{
      const res=await http(rpcUrl,{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({jsonrpc:'2.0',id:1,method,params}),
        signal:ctrl.signal,
      });
      if(!res.ok)throw new Error('RPC_UNAVAILABLE');
      const data=await res.json();
      if(data?.error||typeof data?.result==='undefined')throw new Error('RPC_UNAVAILABLE');
      return data.result;
    }finally{clearTimeout(timer);}
  };
  const chain=await call('eth_chainId',[]);
  if(quantity(chain)!==BigInt(config.chainId))return {status:'mismatch',reason:'WRONG_CHAIN'};
  const receipt=await call('eth_getTransactionReceipt',[expectedTx]);
  if(!receipt)return {status:'pending',reason:'RECEIPT_NOT_FOUND'};
  if(String(receipt.transactionHash||'').toLowerCase()!==expectedTx||
     receipt.status!=='0x1')
    return {status:'mismatch',reason:'FAILED_OR_DIFFERENT_TRANSACTION'};
  if(!receipt.blockNumber||!/^0x[0-9a-fA-F]{64}$/.test(receipt.blockHash||''))
    return {status:'pending',reason:'BLOCK_NOT_FINAL'};
  const current=quantity(await call('eth_blockNumber',[]));
  const receiptBlock=quantity(receipt.blockNumber);
  if(current<receiptBlock)return {status:'pending',reason:'CHAIN_REORG'};
  const canonical=await call('eth_getBlockByNumber',[receipt.blockNumber,false]);
  if(!canonical||String(canonical.hash||'').toLowerCase()!==receipt.blockHash.toLowerCase())
    return {status:'pending',reason:'CHAIN_REORG'};
  const count=current-receiptBlock+1n;
  let received=0n;
  const matched=[];
  for(const log of receipt.logs||[]){
    if(String(log.address||'').toLowerCase()!==contract)continue;
    if(String(log.topics?.[0]||'').toLowerCase()!==TRANSFER_TOPIC)continue;
    if(tokenReceiver(log)!==wallet)continue;
    if(typeof log.data!=='string'||!/^0x[0-9a-fA-F]{64}$/.test(log.data))continue;
    received+=quantity(log.data);
    matched.push(log.logIndex);
  }
  if(received<expectedUnits||matched.length===0)
    return {status:'mismatch',reason:'WRONG_WALLET_CONTRACT_OR_AMOUNT'};
  const proof={
    blockNumber:Number(receiptBlock),
    blockHash:receipt.blockHash.toLowerCase(),
    confirmations:Number(count>BigInt(Number.MAX_SAFE_INTEGER)?BigInt(Number.MAX_SAFE_INTEGER):count),
    verifiedUnits:received.toString(),
    tokenContract:contract,
    wallet,
    logIndexes:matched,
  };
  if(count<BigInt(confirmations))return {status:'confirming',proof};
  return {status:'verified',proof};
}
