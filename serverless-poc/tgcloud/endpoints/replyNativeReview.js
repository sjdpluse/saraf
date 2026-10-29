// Deprecated native SQLite endpoint. The ORIGINAL Supabase project is the
// only canonical store for users, orders, remittances and reviews.
// This handler fails closed rather than creating a parallel record or returning
// an empty, misleading history. Use saraf-telegram-bridge instead.
import { EndpointError } from 'sdk';
export default async function (_input, ctx) {
  if (!Number.isSafeInteger(ctx?.initData?.user?.id) || ctx.initData.user.id <= 0)
    throw new EndpointError('Telegram authorization required',{code:'UNAUTHORIZED'});
  throw new EndpointError('سوابق اصلی صراف فقط در Supabase محفوظ است؛ اتصال امن در حال آماده‌سازی است.',{
    code:'CANONICAL_SUPABASE_REQUIRED',
  });
}
