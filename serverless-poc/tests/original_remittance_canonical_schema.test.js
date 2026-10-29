import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const sql=readFileSync(new URL('../../supabase/sql/saraf_original_remittance_rpc_STAGED.sql',import.meta.url),'utf8');
const edge=readFileSync(new URL('../../supabase/functions/saraf-original-transactions/index.ts',import.meta.url),'utf8');

test('staged original remittance RPC keeps the existing schema V2 USD valuation columns',()=>{
  assert.match(sql,/status,verification_status,asset_price_usd,usd_value/);
  assert.match(sql,/p_asset_price_usd\s+numeric,p_usd_value\s+numeric/);
  assert.match(sql,/p_usd_value>250/);
  assert.doesNotMatch(sql,/IF p_amount>250/);
  assert.match(sql,/p_usd_value<10 OR p_usd_value>10000/);
});
test('signed financial bridge does not silently lose original remittance USD values',()=>{
  assert.match(edge,/p_asset_price_usd:quote\.asset_price_usd,p_usd_value:quote\.usd_value/);
  assert.match(edge,/if\(Number\(quote\.usd_value\)>250\)/);
  assert.match(edge,/IDENTITY_VERIFICATION_REQUIRED/);
  assert.match(edge,/SARAF_ORIGINAL_FINANCIAL_API_ENABLED/);
});
test('original remittance RPC never creates an alternative ledger or grants public roles',()=>{
  assert.match(sql,/INSERT INTO public\.remittance_orders/);
  assert.match(sql,/SECURITY INVOKER/);
  assert.match(sql,/REVOKE ALL ON FUNCTION public\.saraf_original_create_remittance/);
  assert.doesNotMatch(sql,/CREATE TABLE/);
});
