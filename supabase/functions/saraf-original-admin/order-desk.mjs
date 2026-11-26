// The desk pages by the immutable order number so a transition in another
// administrator's session cannot shift the offset of the following page.
export async function readOrderPage(db, status, input) {
  const {side = 'all', after = 0} = input;
  if (!['all', 'buy', 'sell'].includes(side) || !Number.isSafeInteger(after) || after < 0) {
    return {status: 400, body: {error: 'INVALID_ORDER_FILTER'}};
  }
  const limit = 20;
  let query = db.from('usdt_orders')
    .select('id,order_type,asset,usdt_amount,total_afn,status,created_at,risk_level,network,exchange_name')
    .eq('status', status).gt('id', after);
  if (side !== 'all') query = query.eq('order_type', side);
  const {data, error} = await query.order('id', {ascending: true}).limit(limit + 1);
  if (error) throw error;
  const orders = data.slice(0, limit);
  return {status: 200, body: {orders, next_cursor: data.length > limit ? orders.at(-1).id : null}};
}

// The order column can contain an old Telegram file ID, a typed hash, or an
// expired signed receipt URL. Only re-sign the original customer's upload.
export function receiptObject(reference, origin, chatId) {
  try {
    const url = new URL(reference);
    const base = '/storage/v1/object/sign/usdt-receipts/';
    if (url.origin !== new URL(origin).origin || !url.pathname.startsWith(base)) return null;
    const name = url.pathname.slice(base.length);
    return name.startsWith(String(chatId) + '_') && /^\d+_[a-z0-9-]+\.(?:jpe?g|png|webp)$/i.test(name)
      ? name : null;
  } catch {
    return null;
  }
}
