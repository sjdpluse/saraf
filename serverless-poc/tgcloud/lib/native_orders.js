import { db,api } from 'sdk';
import { and,eq,desc,isNull } from 'sdk/db';
import { nativeOrders,nativeQuotes } from '../schema.js';
import {
  actor,audit,checkAction,checkAsset,checkId,checkIdempotencyKey,
  checkNetwork,checkProfileGate,checkText,invalid,requireFinancialWrites,
} from './native_auth.js';
import { toMoneyCents } from './native_money.js';
import { SUPPORTED_NETWORKS,PUBLIC_DEPOSIT_WALLETS,ADMIN_USER_IDS } from './native_config.js';
import { checkMediaOwnership } from './native_media.js';

const now=()=>new Date().toISOString();
const validAddress = (network,address) => {
  const val=String(address || '').trim();
  if (network==='TRC20' && !/^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(val))
    invalid('آدرس ترون معتبر نیست.');
  if (network==='SOLANA' && !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(val))
    invalid('آدرس سولانا معتبر نیست.');
  if (network!=='TRC20' && network!=='SOLANA' &&
      !/^0x[a-fA-F0-9]{40}$/.test(val))
    invalid('آدرس EVM معتبر نیست.');
  return val;
};
export const orderCode=row=>row.asset+'-'+String(row.id).padStart(5,'0');
export function publicOrder(row) {
  if (!row) return null;
  return { id:row.id,order_code:orderCode(row),
    asset:row.asset,order_type:row.action,usdt_amount:row.amountCents/100,
    total_afn:row.afnTenth/10,usd_rate:row.usdRateBasisPoints/10000,
    network:row.network,status:row.status,
    rating:row.rating,created_at:row.createdAt,updated_at:row.updatedAt,
  };
}
export async function getOwnOrders(userId) {
  const rows=await db.select().from(nativeOrders)
    .where(eq(nativeOrders.userId,userId))
    .orderBy(desc(nativeOrders.id)).limit(50).all();
  return rows.map(publicOrder);
}
export async function rateOrder(userId,id,rating,comment) {
  const score=Number(rating);
  if (!Number.isSafeInteger(score) || score<1 || score>5) invalid('امتیاز معتبر نیست.');
  const orderId=checkId(id);
  const rows=await db.update(nativeOrders).set({
    rating:score,ratingComment:String(comment || '').slice(0,800),updatedAt:now(),
  }).where(and(eq(nativeOrders.id,orderId),eq(nativeOrders.userId,userId),
    eq(nativeOrders.status,'completed'),isNull(nativeOrders.rating))).returning().run();
  if (!rows.length) invalid('امتیاز قبلاً ثبت شده یا سفارش تکمیل نشده است.', 'INVALID_STATE');
  await audit('order_rated','order',orderId,userId);
  return {ok:true};
}
export async function createOrder(input,ctx) {
  const user=actor(ctx); requireFinancialWrites();
  const action=checkAction(input?.action), asset=checkAsset(input?.asset);
  const quoteId=checkId(input?.quote_id);
  const amountCents=toMoneyCents(input?.amount);
  const idem=checkIdempotencyKey(input?.idempotency_key);
  const network=checkNetwork(asset,input?.network,{networks:SUPPORTED_NETWORKS});
  const method=String(action==='buy' ? input?.payment_method : input?.receive_method).trim();
  if (!['in_person','online'].includes(method))
    invalid('روش پرداخت یا دریافت معتبر نیست.');
  const exchange=checkText(input?.exchange_name || (action==='buy'?'حضوری':'نام صرافی'), 'نام صرافی',2,120);
  const inPersonCode=method==='in_person'?
    checkText(input?.in_person_code,'کد مراجعه',4,4):null;
  if (inPersonCode && !/^\d{4}$/.test(inPersonCode)) invalid('کد ۴ رقمی معتبر نیست.');

  const wallet=action==='buy' ? validAddress(network,input?.wallet_address) : null;
  const bankInfo=action==='sell' && method==='online'
    ?checkText(input?.bank_info,'اطلاعات بانکی',4,300):null;
  const txProof=action==='sell'
    ?checkText(input?.tx_proof,'اثبات انتقال',12,300):null;
  const mediaId=action==='buy' && method==='online'?
    checkId(input?.receipt_media_id):null;
  const receipt=mediaId ? await checkMediaOwnership(user.id,mediaId,'RECEIPT'):null;

  // For sell, require an operator-verified deposit wallet for the asset/network.
  if (action==='sell' && !PUBLIC_DEPOSIT_WALLETS[asset+'_'+network])
    invalid('کیف پول دریافت برای این شبکه تنظیم نشده است.','DEPOSIT_UNAVAILABLE');

  const fingerprint=JSON.stringify({
    quoteId,action,asset,amountCents,network,method,exchange,wallet,bankInfo,
    txProof,mediaId,inPersonCode,
  });
  const existing=await db.select().from(nativeOrders).where(and(
    eq(nativeOrders.userId,user.id),eq(nativeOrders.idempotencyKey,idem))).get();
  if(existing) {
    if(existing.requestHash!==fingerprint)
      invalid('شناسهٔ درخواست قبلاً برای سفارش متفاوت استفاده شده.', 'IDEMPOTENCY_CONFLICT');
    return {order_id:existing.id,order_code:orderCode(existing),duplicate:true};
  }
  const quote=await db.select().from(nativeQuotes).where(and(
    eq(nativeQuotes.id,quoteId),eq(nativeQuotes.userId,user.id))).get();
  if (!quote || quote.action!==action || quote.asset!==asset ||
      quote.amountCents!==amountCents || quote.status!=='active' ||
      quote.expiresAt<=Math.floor(Date.now()/1000)) {
    invalid('نرخ معتبر یا فعال نیست؛ نرخ جدید دریافت کنید.','QUOTE_INVALID');
  }
  await checkProfileGate(user.id,amountCents/100);
  let inserted;
  try {
    const [row]=await db.insert(nativeOrders).values({
      userId:user.id,idempotencyKey:idem,requestHash:fingerprint,quoteId,
      action,asset,amountCents,afnTenth:quote.totalAfnTenth,
      usdRateBasisPoints:quote.usdRateBasisPoints,network,
      exchangeName:exchange,walletAddress:wallet,paymentMethod:action==='buy'?method:null,
      receiveMethod:action==='sell'?method:null,bankInfo,
      inPersonCode,receiptFileId:receipt?.telegramFileId || null,
      transactionProof:txProof,status:'pending',createdAt:now(),updatedAt:now(),
    }).onConflictDoNothing().returning().run();
    inserted=row;
  } catch (error) {
    console.warn('Order create error',String(error));
    invalid('ثبت سفارش ناموفق بود؛ درخواست را با همان شناسه تکرار کنید.','ORDER_FAILED');
  }
  if (!inserted) {
    const replay=await db.select().from(nativeOrders).where(and(
      eq(nativeOrders.userId,user.id),eq(nativeOrders.idempotencyKey,idem))).get();
    if (replay && replay.requestHash===fingerprint)
      return {order_id:replay.id,order_code:orderCode(replay),duplicate:true};
    invalid('نرخ قبلاً برای سفارش دیگری استفاده شده است.','QUOTE_CONSUMED');
  }
  await db.update(nativeQuotes).set({status:'consumed',orderId:inserted.id})
    .where(and(eq(nativeQuotes.id,quoteId),eq(nativeQuotes.status,'active'))).run();
  await audit('order_created','order',inserted.id,user.id,null,
    {action,asset,amountCents,network,status:'pending'});
  for(const adminId of ADMIN_USER_IDS) {
    try {
      await api.sendMessage({chat_id:adminId,text:
        '🏦 سفارش جدید صراف\n'+orderCode(inserted)+
        '\n'+action+' '+amountCents/100+' '+asset+'\n/admin_orders'});
    } catch (error) { console.warn('Admin notification failed',String(error)); }
  }
  return {order_id:inserted.id,order_code:orderCode(inserted),duplicate:false,
    quote:{quote_id:quoteId,total_afn:quote.totalAfnTenth/10}};
}
