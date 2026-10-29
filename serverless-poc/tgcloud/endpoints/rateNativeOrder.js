import { actor } from '../lib/native_auth.js';
import { rateOrder } from '../lib/native_orders.js';
export default async function(input,ctx) {
  return rateOrder(actor(ctx).id,input?.order_id,input?.rating,input?.comment);
}
