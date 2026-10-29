import { actor } from '../lib/native_auth.js';
import { getOwnOrders } from '../lib/native_orders.js';
export default async function(_input,ctx) {
  return getOwnOrders(actor(ctx).id);
}
