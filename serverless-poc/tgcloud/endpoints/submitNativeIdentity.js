import { db } from 'sdk';
import { eq } from 'sdk/db';
import { nativeProfiles } from '../schema.js';
import { actor, audit, getProfile, hasBasicProfile, invalid } from '../lib/native_auth.js';
import { latestMedia } from '../lib/native_media.js';
import { IDENTITY_UPLOADS_ENABLED } from '../lib/native_config.js';

export default async function (_input,ctx) {
  const user=actor(ctx);
  if (!IDENTITY_UPLOADS_ENABLED) invalid('ثبت اسناد هنوز فعال نیست.','KYC_UPLOAD_DISABLED');
  const profile=await getProfile(user.id);
  if (!hasBasicProfile(profile)) invalid('ابتدا پروفایل پایه را تکمیل کنید.');
  if (profile.kycStatus==='restricted') invalid('حساب شما محدود شده است.');
  const [id,selfie]=await Promise.all([
    latestMedia(user.id,'KYC_ID'), latestMedia(user.id,'KYC_SELFIE'),
  ]);
  if (!id || !selfie) invalid('ابتدا عکس مدرک و سلفی را در چت خصوصی ربات ارسال کنید.', 'MEDIA_MISSING');
  if (id.telegramMessageId===selfie.telegramMessageId) invalid('دو مدرک مستقل لازم است.');
  await db.update(nativeProfiles).set({
    idDocumentFileId:id.telegramFileId,selfieFileId:selfie.telegramFileId,
    kycStatus:'pending',verifiedBy:null,updatedAt:new Date().toISOString(),
  }).where(eq(nativeProfiles.userId,user.id)).run();
  await audit('identity_submitted','user_profile',user.id,user.id,null,{status:'pending'});
  return {ok:true,kyc_status:'pending'};
}
