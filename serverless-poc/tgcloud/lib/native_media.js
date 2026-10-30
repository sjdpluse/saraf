import { db, api } from 'sdk';
import { and, desc, eq, isNull } from 'sdk/db';
import { nativeMedia } from '../schema.js';
import { invalid } from './native_auth.js';

const LABELS = {
  KYC_ID: 'تذکره/مدرک هویتی',
  KYC_SELFIE: 'عکس سلفی',
  RECEIPT: 'رسید پرداخت',
  BENEFICIARY_ID: 'تذکره گیرنده حواله',
};
export const MEDIA_KINDS=Object.freeze(Object.keys(LABELS));

// Legacy user documents live in private Supabase Storage. Until the owner
// approves a secure canonical upload flow, never save Telegram file IDs in a
// parallel SQLite media table; this guard does not depend on a feature flag.
export async function acceptMedia(message) {
  const user=message?.from, chat=message?.chat;
  if (chat?.type!=='private' || !Number.isSafeInteger(user?.id) ||
      chat?.id!==user.id) return false;
  const kind=String(message?.caption || '').trim().toUpperCase();
  if (!MEDIA_KINDS.includes(kind)) return false;
  await api.sendMessage({chat_id:user.id,text:
    '⚠️ ارسال عکس مدارک و رسیدها در ربات فعلاً فعال نیست. لطفاً عکس شخصی، تذکره یا رسید پرداخت را نفرستید. سوابق قبلی شما در Supabase محفوظ است.'});
  return true;
}
export async function latestMedia(userId, kind) {
  if (!MEDIA_KINDS.includes(kind)) invalid('نوع فایل معتبر نیست.');
  return await db.select().from(nativeMedia)
    .where(and(eq(nativeMedia.userId,userId),eq(nativeMedia.kind,kind)))
    .orderBy(desc(nativeMedia.id)).limit(1).get();
}
export async function checkMediaOwnership(userId, id, kind) {
  const media=await db.select().from(nativeMedia)
    .where(and(eq(nativeMedia.userId,userId),eq(nativeMedia.id,id),
      eq(nativeMedia.kind,kind))).get();
  if (!media) invalid('مدرک متعلق به کاربر نیست.', 'MEDIA_NOT_FOUND');
  return media;
}
