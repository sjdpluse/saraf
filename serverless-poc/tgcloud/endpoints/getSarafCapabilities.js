// Server-side feature flags: never claim financial services are live before orders,
// permissions, Supabase history, secure upload, and admin settlement are migrated.
// A client flag is NOT authorization; monetary endpoints do not exist in this stage.
export default async function (_input, ctx) {
  if (!Number.isSafeInteger(ctx?.initData?.user?.id)) throw new Error('Unauthorized');
  return {
    mode: 'telegram-serverless',
    publicMarkets: true,
    trading: false,
    remittances: false,
    kyc: false,
    orders: false,
    reviews: false,
    payments: false,
  };
}
