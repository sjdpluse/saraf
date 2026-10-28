// Proof-of-concept database only. The real Saraf financial data remains in Supabase.
import { table, integer } from 'sdk/db';

export const smokeCounters = table('saraf_poc_counters', {
  chatId: integer('chat_id').primaryKey(),
  seen: integer('seen').notNull().default(0),
});
