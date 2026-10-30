import { actor } from '../lib/native_auth.js';
import { PUBLIC_DEPOSIT_WALLETS,SUPPORTED_NETWORKS,FINANCIAL_WRITES_ENABLED,
 MIN_STABLECOIN_USD,MAX_STABLECOIN_USD } from '../lib/native_config.js';
export default async function (_input,ctx) {
  actor(ctx);
  return {
    assets:['USDT','USDC'].map(asset=>({
      code:asset,name:asset,networks:SUPPORTED_NETWORKS[asset].map(code=>({
        code,label:code,deposit_wallet: PUBLIC_DEPOSIT_WALLETS[asset+'_'+code] || null,
      })),
    })),
    enabled:FINANCIAL_WRITES_ENABLED,
    min_amount:MIN_STABLECOIN_USD,max_amount:MAX_STABLECOIN_USD,
  };
}
