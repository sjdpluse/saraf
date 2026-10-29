// Explicit operational controls. Defaults are SAFE and cannot be flipped by clients.
// IMPORTANT: Fill these server-side values only after bank/wallet validation and
// historic Supabase reconciliation. Never put secrets in this module.
export const ADMIN_USER_IDS = Object.freeze([]); // Owner supplies Telegram numeric IDs.
export const FINANCIAL_WRITES_ENABLED = false;
export const REQUIRE_VERIFIED_KYC = true;
export const IDENTITY_THRESHOLD_USD = 250;
export const MIN_STABLECOIN_USD = 10;
export const MAX_STABLECOIN_USD = 10000;
export const QUOTE_TTL_SECONDS = 300;
export const REMITTANCE_FEE_PERCENT = 0;
export const PUBLIC_DEPOSIT_WALLETS = Object.freeze({
  // Set validated network+asset wallets for deposits, e.g. USDT_TRC20.
  // No wallet is invented or copied from unverified defaults.
});
export const BANK_DETAILS = Object.freeze({
  bank_name: '', bank_account_holder: '', bank_account_number: '',
});
export const SUPPORTED_NETWORKS = Object.freeze({
  USDT: ['TRC20','ERC20','BEP20'],
  USDC: ['ERC20','BEP20','ARBITRUM','BASE','POLYGON','SOLANA','AVALANCHE','OPTIMISM'],
});
