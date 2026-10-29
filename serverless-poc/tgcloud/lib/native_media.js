import { db, api } from 'sdk';
import { and, desc, eq, isNull } from 'sdk/db';
import { nativeMedia } from '../schema.js';
import { invalid } from './native_auth.js';
import { IDENTITY_UPLOADS_ENABLED } from './native_config.js';

const LABELS = {
  KYC_ID: 'تذکره/مدرک هویتی',
  KYC_SELFIE: 'عکس سلفی',
  RECEIPT: 'رسید پرداخت',
  BENEFICIARY_ID: 'تذکره گیرنده حواله',
};
export const MEDIA_KINDS=Object.freeze(Object.keys(LABELS));

export async function acceptMedia(message) {
  const user=message?.from;
  const chat=message?.chat;
  // Never receive private identity media from a group or forwarded message.
  if (chat?.type !== 'private' || !Number.isSafeInteger(user?.id) ||
      chat.id !== user.id || message.forward_origin || message.forward_from) return false;
  const kind=String(message.caption || '').trim().toUpperCase();
  if (!MEDIA_KINDS.includes(kind)) return false;
  if (!IDENTITY_UPLOADS_ENABLED) {
    await api.sendMessage({chat_id:user.id,text:'ارسال مدارک و رسیدهای خصوصی تا تکمیل تنظیمات امنیتی غیرفعال است. لطفاً فعلاً سند نفرستید.'});
    return true;
  }
  const photos=message.photo;
  const best=Array.isArray(photos) && photos.length ? photos[photos.length - 1] : null;
  const doc=message.document;
  if (!best && !doc) {
    await api.sendMessage({chat_id:user.id,text:'فقط عکس یا فایل تصویری ارسال کنید.'});
    return true;
  }
  const mimeType=doc?.mime_type || 'image/jpeg';
  if (!['image/jpeg','image/png','image/webp'].includes(mimeType) ||
      (doc?.file_size || best?.file_size || 0)>8*1024*1024) {
    await api.sendMessage({chat_id:user.id,text:'فرمت یا حجم فایل معتبر نیست. حداکثر ۸ مگابایت.'});
    return true;
  }
  const fileId=best?.file_id || doc?.file_id;
  if (!fileId || !Number.isSafeInteger(message.message_id)) return true;
  await db.insert(nativeMedia).values({
    userId: user.id, kind, telegramFileId:fileId, mimeType,
    mediaCategory:doc?'document':'photo',
    telegramMessageId:message.message_id, receivedAt:new Date().toISOString(),
  }).onConflictDoNothing().run();
  await api.sendMessage({chat_id:user.id,
    text:'✅ '+LABELS[kind]+' دریافت شد. برای تکمیل، به Mini App صراف بازگردید.'});
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
