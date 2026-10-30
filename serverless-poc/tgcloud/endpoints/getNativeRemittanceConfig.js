import { actor } from '../lib/native_auth.js';
import {
  PUBLIC_DEPOSIT_WALLETS,SUPPORTED_NETWORKS,FINANCIAL_WRITES_ENABLED,
  REMITTANCE_FEE_PERCENT,IDENTITY_THRESHOLD_USD,
  MIN_STABLECOIN_USD,MAX_STABLECOIN_USD,
} from '../lib/native_config.js';
export default async function(_input,ctx) {
  actor(ctx);
  return {
    assets: FINANCIAL_WRITES_ENABLED
      ? Object.entries(SUPPORTED_NETWORKS).map(([code,networks])=>({
        code,name:code,networks:networks.filter(network=>PUBLIC_DEPOSIT_WALLETS[code+'_'+network])
          .map(network=>({code:network,label:network,
            deposit_wallet:PUBLIC_DEPOSIT_WALLETS[code+'_'+network]})),
      })).filter(a=>a.networks.length>0) : [],
    fee_percent:REMITTANCE_FEE_PERCENT,
    identity_verification_threshold_usd:IDENTITY_THRESHOLD_USD,
    min_usd:MIN_STABLECOIN_USD,max_usd:MAX_STABLECOIN_USD,
  };
}
