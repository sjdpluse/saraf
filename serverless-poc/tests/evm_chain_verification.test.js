import test from 'node:test';
import assert from 'node:assert/strict';
import { verifyEvmTransfer, amountToTokenUnits } from '../../supabase/functions/saraf-chain-verifier/evm.mjs';

const DEST='0x2222222222222222222222222222222222222222';
const CONTRACT='0x3333333333333333333333333333333333333333';
const TX='0x'+'a'.repeat(64);
const BLOCK_HASH='0x'+'b'.repeat(64);
const EVENT='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const receipt={
  transactionHash:TX,status:'0x1',blockNumber:'0x64',blockHash:BLOCK_HASH,
  logs:[{address:CONTRACT,topics:[EVENT,'0x'+'0'.repeat(64),
      '0x'+'0'.repeat(24)+DEST.slice(2)],data:'0x'+(75n*1_000_000n).toString(16).padStart(64,'0'),
      logIndex:'0x0'}]
};
const config={
  chainId:1,rpcUrl:'https://rpc.example.invalid',wallet:DEST,
  tokenContract:CONTRACT,decimals:6,minConfirmations:12,
};
const req={txHash:TX,amount:'75'};
function httpFactory(overrides={}){
 const answers={
   eth_chainId:'0x1',eth_getTransactionReceipt:receipt,
   eth_blockNumber:'0x70',
   eth_getBlockByNumber:{hash:BLOCK_HASH},
   ...overrides,
 };
 return async (_url,options)=>{
   const {method}=JSON.parse(options.body);
   return {ok:true,json:async()=>({jsonrpc:'2.0',id:1,result:answers[method]})};
 };
}
test('amount decimal precision is exact, never float rounded',()=>{
 assert.equal(amountToTokenUnits('75.123456',6),75123456n);
 assert.equal(amountToTokenUnits('0.000001',6),1n);
 assert.throws(()=>amountToTokenUnits('0.0000001',6));
 assert.throws(()=>amountToTokenUnits('1e9',6));
});
test('verifies matching EVM token contract, wallet, amount, chain and 12+ canonical confirmations',async()=>{
 const result=await verifyEvmTransfer(config,req,httpFactory());
 assert.equal(result.status,'verified');
 assert.equal(result.proof.verifiedUnits,'75000000');
 assert.equal(result.proof.confirmations,13);
});
test('rejects token from a different contract or amount shortage',async()=>{
 assert.equal((await verifyEvmTransfer({...config,tokenContract:DEST},req,httpFactory())).status,'mismatch');
 assert.equal((await verifyEvmTransfer(config,{...req,amount:'75.01'},httpFactory())).status,'mismatch');
});
test('does not verify wrong chain, failed tx, or non-canonical block',async()=>{
 assert.equal((await verifyEvmTransfer(config,req,httpFactory({eth_chainId:'0x89'}))).status,'mismatch');
 assert.equal((await verifyEvmTransfer(config,req,httpFactory({eth_getTransactionReceipt:{...receipt,status:'0x0'}}))).status,'mismatch');
 assert.equal((await verifyEvmTransfer(config,req,httpFactory({eth_getBlockByNumber:{hash:'0x'+'0'.repeat(64)}}))).status,'pending');
});
test('waits for enough final confirmations',async()=>{
 assert.equal((await verifyEvmTransfer(config,req,httpFactory({eth_blockNumber:'0x65'}))).status,'confirming');
 assert.equal((await verifyEvmTransfer(config,req,httpFactory({eth_getTransactionReceipt:null}))).status,'pending');
});
test('rejects invalid configuration and transaction hashes',async()=>{
 await assert.rejects(verifyEvmTransfer({...config,tokenContract:'wrong'},req,httpFactory()));
 await assert.rejects(verifyEvmTransfer(config,{txHash:'not-a-tx',amount:'75'},httpFactory()));
});
