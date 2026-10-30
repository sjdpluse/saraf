import { db,api } from 'sdk';
import { and,eq,desc } from 'sdk/db';
import { nativeRemittances } from '../schema.js';
import {
  actor,audit,checkAsset,checkId,checkIdempotencyKey,checkNetwork,
  checkProfileGate,checkText,invalid,requireFinancialWrites,
} from './native_auth.js';
import { PUBLIC_DEPOSIT_WALLETS,SUPPORTED_NETWORKS,REMITTANCE_FEE_PERCENT,
  MIN_STABLECOIN_USD,MAX_STABLECOIN_USD,ADMIN_USER_IDS } from './native_config.js';
import { localUsdQuote } from './native_pricing.js';
import { toMoneyCents,roundHalfUp } from './native_money.js';
import { checkMediaOwnership } from './native_media.js';

const now=()=>new Date().toISOString();
export const remittanceCode=row=>'RM-'+String(row.id).padStart(6,'0');
export function publicRemittance(row) {
  return {
    id:row.id,order_code:remittanceCode(row),asset:row.asset,network:row.network,
    crypto_amount:row.amountCents/100,payout_afn:row.payoutAfnTenth/10,
    usd_rate:row.rateBasisPoints/10000,deposit_wallet:row.depositWallet,
    sender_name:row.senderName,beneficiary_full_name:row.beneficiaryName,
    beneficiary_phone:row.beneficiaryPhone,beneficiary_province:'',
    beneficiary_city:'',beneficiary_address:row.beneficiaryLocation,
    status:row.status,tx_hash:row.txHash,verification_status:row.verificationStatus,
    created_at:row.createdAt,updated_at:row.updatedAt,
  };
}
export async function remittanceQuote(input) {
  requireFinancialWrites();
  const asset=checkAsset(input?.asset);
  const network=checkNetwork(asset,input?.network,{networks:SUPPORTED_NETWORKS});
  const wallet=PUBLIC_DEPOSIT_WALLETS[asset+'_'+network];
  if (!wallet) invalid('کیف پول دریافت برای شبکه تنظیم نشده است.','NETWORK_UNAVAILABLE');
  const quote=await localUsdQuote('sell',asset,input?.amount);
  const fee=Number(roundHalfUp(
    BigInt(quote.totalAfnTenth)*BigInt(Math.round(REMITTANCE_FEE_PERCENT*100)),10000n));
  const payout=quote.totalAfnTenth-fee;
  return {
    asset,network,crypto_amount:quote.amountCents/100,
    usd_value:quote.amountCents/100,asset_price_usd:1,
    usd_rate:quote.ratePoints/10000,gross_afn:quote.totalAfnTenth/10,
    fee_percent:REMITTANCE_FEE_PERCENT,fee_afn:fee/10,
    payout_afn:payout/10,deposit_wallet:wallet,
    basis:'local',pricing_source:quote.source,
    _privateAmountCents:quote.amountCents,_privateRatePoints:quote.ratePoints,
    _privatePayoutTenth:payout,
  };
}
export async function createRemittance(input,ctx) {
  const user=actor(ctx);requireFinancialWrites();
  const idem=checkIdempotencyKey(input?.idempotency_key);
  const duplicate=await db.select().from(nativeRemittances).where(and(
    eq(nativeRemittances.userId,user.id),eq(nativeRemittances.idempotencyKey,idem))).get();
  const asset=checkAsset(input?.asset);
  const network=checkNetwork(asset,input?.network,{networks:SUPPORTED_NETWORKS});
  const sender=checkText(input?.sender_full_name,'نام فرستنده',3,160);
  const country=checkText(input?.sender_country,'کشور',2,120);
  const beneficiary=checkText(input?.beneficiary_full_name,'نام گیرنده',3,160);
  const phone=checkText(input?.beneficiary_phone,'شماره گیرنده',7,40);
  const location=[
    checkText(input?.beneficiary_province,'ولایت',2,120),
    checkText(input?.beneficiary_city,'شهر',2,120),
    checkText(input?.beneficiary_address,'آدرس',3,300),
  ].join(' / ');
  const documentId=checkId(input?.beneficiary_media_id);
  await checkMediaOwnership(user.id,documentId,'BENEFICIARY_ID');
  const amountCents=toMoneyCents(input?.amount);
  const payloadFingerprint=JSON.stringify({
    idem,asset,network,sender,country,beneficiary,phone,location,documentId,amountCents,
  });
  if(duplicate) {
    if(duplicate.requestHash!==payloadFingerprint) invalid('درخواست تکراری با محتوای متفاوت است.','IDEMPOTENCY_CONFLICT');
    return {...publicRemittance(duplicate),duplicate:true};
  }
  await checkProfileGate(user.id,amountCents/100);
  const quote=await remittanceQuote({asset,network,amount:input.amount});
  const [order]=await db.insert(nativeRemittances).values({
    userId:user.id,idempotencyKey:idem,requestHash:payloadFingerprint,
    asset,network,amountCents,rateBasisPoints:quote._privateRatePoints,
    payoutAfnTenth:quote._privatePayoutTenth,depositWallet:quote.deposit_wallet,
    senderName:sender,senderCountry:country,beneficiaryName:beneficiary,
    beneficiaryPhone:phone,beneficiaryLocation:location,
    beneficiaryDocumentFileId:(await checkMediaOwnership(user.id,documentId,'BENEFICIARY_ID')).telegramFileId,
    status:'awaiting_transfer',createdAt:now(),updatedAt:now(),
  }).onConflictDoNothing().returning().run();
  if(!order) {
    const replay=await db.select().from(nativeRemittances).where(and(
      eq(nativeRemittances.userId,user.id),eq(nativeRemittances.idempotencyKey,idem))).get();
    if(replay?.requestHash===payloadFingerprint) return {...publicRemittance(replay),duplicate:true};
    invalid('این حواله قبلاً ثبت شده است.','IDEMPOTENCY_CONFLICT');
  }
  await audit('remittance_created','remittance',order.id,user.id,null,
    {asset,network,amountCents,status:'awaiting_transfer'});
  return {...publicRemittance(order),duplicate:false};
}
export async function submitRemittanceTx(input,ctx) {
  const user=actor(ctx);requireFinancialWrites();
  const id=checkId(input?.order_id);
  const hash=String(input?.tx_hash || '').trim();
  if(!/^[A-Za-z0-9:_-]{12,160}$/.test(hash)) invalid('شناسه تراکنش معتبر نیست.');
  const remittance=await db.select().from(nativeRemittances)
    .where(and(eq(nativeRemittances.id,id),eq(nativeRemittances.userId,user.id))).get();
  if(!remittance) invalid('حواله یافت نشد.','NOT_FOUND');
  if(remittance.status==='transfer_submitted' && remittance.txHash===hash)
    return publicRemittance(remittance);
  if(remittance.status!=='awaiting_transfer') invalid('حواله در مرحله ارسال تراکنش نیست.','INVALID_STATE');
  // Never count a submitted tx hash as a confirmed blockchain transfer.
  const [changed]=await db.update(nativeRemittances).set({
    txHash:hash,status:'transfer_submitted',verificationStatus:'unverified',
    updatedAt:now(),
  }).where(and(eq(nativeRemittances.id,id),eq(nativeRemittances.userId,user.id),
    eq(nativeRemittances.status,'awaiting_transfer'))).returning().run();
  if(!changed) invalid('وضعیت حواله تغییر کرده؛ دوباره بررسی کنید.','INVALID_STATE');
  await audit('remittance_tx_submitted','remittance',id,user.id,null,
    {status:'transfer_submitted',verified:false});
  for(const adminId of ADMIN_USER_IDS) {
    try {
      await api.sendMessage({chat_id:adminId,
        text:'🔔 ثبت TxID برای حواله '+remittanceCode(changed)+
        '\n⚠️ هنوز در بلاکچین تأیید نشده است.\n/admin_remittances'});
    }catch(e){ console.warn('Admin notification unavailable',String(e));}
  }
  return publicRemittance(changed);
}
export async function getOwnRemittances(userId) {
  const rows=await db.select().from(nativeRemittances)
    .where(eq(nativeRemittances.userId,userId))
    .orderBy(desc(nativeRemittances.id)).limit(50).all();
  return rows.map(publicRemittance);
}
