import { actor, getProfile, hasApprovedIdentity, hasBasicProfile } from '../lib/native_auth.js';
import { IDENTITY_THRESHOLD_USD } from '../lib/native_config.js';
import { latestMedia } from '../lib/native_media.js';
export default async function (_input,ctx) {
  const user=actor(ctx);
  const [profile,id, selfie,receipt,beneficiary]=await Promise.all([
    getProfile(user.id), latestMedia(user.id,'KYC_ID'),
    latestMedia(user.id,'KYC_SELFIE'), latestMedia(user.id,'RECEIPT'),
    latestMedia(user.id,'BENEFICIARY_ID'),
  ]);
  return {
    has_basic_profile:hasBasicProfile(profile),
    has_identity_verification:hasApprovedIdentity(profile),
    has_identity_documents:Boolean(profile?.idDocumentFileId && profile?.selfieFileId),
    identity_verification_threshold_usd:IDENTITY_THRESHOLD_USD,
    kyc_status:profile?.kycStatus || 'pending',
    profile:profile?{
      first_name:profile.firstName, last_name:profile.lastName,
      phone:profile.phone, kyc_status:profile.kycStatus,
    }:null,
    uploaded:{kyc_id:!!id,selfie:!!selfie,receipt:!!receipt,beneficiary_id:!!beneficiary},
  };
}
