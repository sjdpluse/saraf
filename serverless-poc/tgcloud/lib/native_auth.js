import { EndpointError, db } from 'sdk';
import { eq, desc } from 'sdk/db';
import { nativeAudit, nativeProfiles } from '../schema.js';
import { ADMIN_USER_IDS, FINANCIAL_WRITES_ENABLED, IDENTITY_THRESHOLD_USD, REQUIRE_VERIFIED_KYC } from './native_config.js';

export function actor(ctx) {
  const user = ctx?.initData?.user;
  if (!Number.isSafeInteger(user?.id) || user.id <= 0)
    throw new EndpointError('Telegram authorization required', {code:'UNAUTHORIZED'});
  return user;
}
export function isOperator(id) {
  return Number.isSafeInteger(id) && ADMIN_USER_IDS.includes(id);
}
export function requireOperator(ctx) {
  const user = actor(ctx);
  if (!isOperator(user.id)) throw new EndpointError('اجازهٔ مدیر لازم است.', {code:'FORBIDDEN'});
  return user;
}
// The EXISTING Supabase is the sole financial ledger. Do not allow creating
// a separate ledger in Telegram-native SQLite by changing one boolean flag.
export function requireFinancialWrites() {
  throw new EndpointError(
    'عملیات مالی باید فقط در Supabase اصلی صراف انجام شود؛ سیستم جدید هنوز برای معاملات فعال نشده است.',
    {code:'CANONICAL_SUPABASE_REQUIRED'},
  );
}

export function invalid(message, code='INVALID_INPUT') {
  throw new EndpointError(message, {code});
}
export function checkText(value, label, min=2, max=160) {
  const text = String(value ?? '').trim();
  if (text.length < min || text.length > max) invalid(label + ' معتبر نیست.');
  return text;
}
export function checkAsset(asset) {
  const value = String(asset || '').toUpperCase().trim();
  if (!['USDT','USDC'].includes(value)) invalid('دارایی انتخاب‌شده معتبر نیست.');
  return value;
}
export function checkAction(action) {
  const value = String(action || '').trim();
  if (!['buy', 'sell'].includes(value)) invalid('نوع معامله معتبر نیست.');
  return value;
}
export function checkId(value) {
  const result=Number(value);
  if (!Number.isSafeInteger(result) || result <= 0) invalid('شناسه معتبر نیست.');
  return result;
}
export function checkIdempotencyKey(key) {
  const value=String(key || '').trim();
  if (!/^[A-Za-z0-9_.:\-]{16,128}$/.test(value))
    invalid('شناسهٔ تکرارناپذیر درخواست معتبر نیست.', 'IDEMPOTENCY_KEY_REQUIRED');
  return value;
}
export function checkNetwork(asset, network, options={}) {
  const value=String(network || '').toUpperCase().trim();
  const supported=options.networks?.[asset] || [];
  if (!supported.includes(value)) invalid('شبکه برای این دارایی پشتیبانی نمی‌شود.');
  return value;
}
export async function getProfile(userId) {
  return await db.select().from(nativeProfiles)
    .where(eq(nativeProfiles.userId, userId)).get();
}
export function hasBasicProfile(profile) {
  return Boolean(profile?.firstName && profile?.lastName && profile?.phone);
}
export function hasApprovedIdentity(profile) {
  return profile?.kycStatus === 'verified' &&
    Boolean(profile?.idDocumentFileId && profile?.selfieFileId);
}
export async function audit(action, entityType, entityId, actorId, before=null, after=null) {
  await db.insert(nativeAudit).values({
    action, entityType, entityId, actorId,
    beforeJson: before == null ? null : JSON.stringify(before),
    afterJson: after == null ? null : JSON.stringify(after),
    at: new Date().toISOString(),
  }).run();
}
export async function checkProfileGate(userId, amountUsd) {
  const profile=await getProfile(userId);
  if (!hasBasicProfile(profile)) invalid('ابتدا پروفایل را تکمیل کنید.', 'PROFILE_REQUIRED');
  if (profile.kycStatus === 'restricted') invalid('حساب شما محدود شده است.', 'ACCOUNT_RESTRICTED');
  if (amountUsd > IDENTITY_THRESHOLD_USD &&
      !(REQUIRE_VERIFIED_KYC ? hasApprovedIdentity(profile) : Boolean(profile.idDocumentFileId && profile.selfieFileId))) {
    invalid('احراز هویت تأییدشده برای این مبلغ لازم است.', 'IDENTITY_VERIFICATION_REQUIRED');
  }
  return profile;
}
