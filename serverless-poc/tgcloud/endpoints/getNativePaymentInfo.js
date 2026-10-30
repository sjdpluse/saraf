import { actor } from '../lib/native_auth.js';
import { BANK_DETAILS,FINANCIAL_WRITES_ENABLED } from '../lib/native_config.js';
export default async function (_input,ctx) {
  actor(ctx);
  return FINANCIAL_WRITES_ENABLED ? BANK_DETAILS : {
    bank_name:'',bank_account_holder:'',bank_account_number:'',
    unavailable:true,
  };
}
