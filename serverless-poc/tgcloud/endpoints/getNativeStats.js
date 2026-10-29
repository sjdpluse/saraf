import { db } from 'sdk';
import { sql } from 'sdk/db';
import { actor } from '../lib/native_auth.js';
export default async function(_input,ctx) {
  actor(ctx);
  const stats=await db.get(sql`select count(*) as total, avg(rating) as average
    from saraf_native_orders where status='completed'`);
  return {completed_orders:Number(stats?.total || 0),
    average_rating:Number(stats?.average || 0)};
}
