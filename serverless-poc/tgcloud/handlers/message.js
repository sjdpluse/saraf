// TEST BOT ONLY. This is a platform connectivity smoke test, not Saraf's actual bot.
// IMPORTANT: Never deploy to the active financial bot before the full migration passes review.
import { api, db } from 'sdk';
import { sql } from 'sdk/db';
import { smokeCounters } from '../schema.js';

export default async function (message) {
  const chatId = message?.chat?.id;
  if (!Number.isSafeInteger(chatId)) return;

  const input = String(message.text ?? '').trim();
  if (!/^\/(start|ping)(?:@[a-zA-Z0-9_]+)?(?:\s|$)/.test(input)) return;

  const [row] = await db.insert(smokeCounters)
    .values({ chatId, seen: 1 })
    .onConflictDoUpdate({
      target: smokeCounters.chatId,
      set: { seen: sql`${smokeCounters.seen} + 1` },
    })
    .returning()
    .run();

  await api.sendMessage({
    chat_id: chatId,
    text:
      '🧪 Saraf – Telegram Serverless TEST ONLY\n' +
      'اتصال Telegram Serverless و SQLite موفق است.\n' +
      'تعداد تست‌های شما: ' + row.seen + '\n\n' +
      '⚠️ این نسخه سفارش، پرداخت، حواله یا نرخ واقعی ارائه نمی‌کند.',
  });
}
