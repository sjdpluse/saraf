// Owner-only operational interface on the SAME Telegram bot. Telegram native
// DBs are per-bot; a second admin bot cannot access this DB without a bridge.
import { db,api } from 'sdk';
import { and,eq,desc,isNotNull } from 'sdk/db';
import { nativeOrders,nativeRemittances,nativeProfiles } from '../schema.js';
import { ADMIN_USER_IDS } from './native_config.js';
import { audit, isOperator, invalid } from './native_auth.js';
import { canTransition } from './order_state_machine.js';
import { orderCode } from './native_orders.js';
import { remittanceCode } from './native_remittances.js';
import { latestMedia } from './native_media.js';

const cleanId=value => {
  const id=Number(value);
  if (!Number.isSafeInteger(id)||id<=0) invalid('شناسه معتبر نیست.');
  return id;
};
const toText=row=>JSON.stringify(row).slice(0,2000);
const quoteLine=row=>row.asset+' '+(row.amountCents/100)+' | '+row.status+' | '+row.network;

export async function adminCommand(message) {
  const adminId=message?.from?.id;
  if(message?.chat?.type!=='private' || message?.chat?.id!==adminId || !isOperator(adminId))return false;
  const text=String(message.text || '').trim();
  const send=msg=>api.sendMessage({chat_id:adminId,text:msg});
  if (text==='/admin' || text==='/admin_help') {
    await send('🔐 پنل مدیریت صراف\n/admin_orders\n/admin_remittances\n/admin_kyc\n/kyc_approve USER_ID\n/kyc_reject USER_ID\n/order_review ORDER_ID\n/order_cancel ORDER_ID\n/remit_review ORDER_ID\n⚠️ تکمیل پرداخت تا ایجاد تأیید قابل ممیزی غیرفعال است.');
    return true;
  }
  if(text==='/admin_orders') {
    const rows=await db.select().from(nativeOrders).orderBy(desc(nativeOrders.id)).limit(15).all();
    await send('📦 آخرین سفارش‌ها:\n'+(rows.map(x=>orderCode(x)+': '+quoteLine(x)).join('\n') || 'سفارشی نیست.'));
    return true;
  }
  if(text==='/admin_remittances') {
    const rows=await db.select().from(nativeRemittances).orderBy(desc(nativeRemittances.id)).limit(15).all();
    await send('🪙 آخرین حواله‌ها:\n'+(rows.map(x=>remittanceCode(x)+': '+quoteLine(x)+
      ' | blockchain='+x.verificationStatus).join('\n') || 'حواله‌ای نیست.'));
    return true;
  }
  if(text==='/admin_kyc') {
    const rows=await db.select().from(nativeProfiles).where(eq(nativeProfiles.kycStatus,'pending')).limit(15).all();
    const lines=rows.filter(p=>p.idDocumentFileId && p.selfieFileId)
      .map(p=>p.userId+' : '+p.firstName+' '+p.lastName).join('\n');
    await send('👤 احراز هویت‌های در انتظار:\n'+(lines || 'موردی نیست.'));
    return true;
  }
  let match=text.match(/^\/kyc_(approve|reject)\s+(\d+)$/);
  if(match) {
    const targetId=cleanId(match[2]);
    const status=match[1]==='approve'?'verified':'rejected';
    const current=await db.select().from(nativeProfiles)
      .where(eq(nativeProfiles.userId,targetId)).get();
    if(!current || !current.idDocumentFileId || !current.selfieFileId) {
      await send('⛔ دو سند احراز هویت ثبت نشده است.');return true;
    }
    if(current.kycStatus==='restricted') {await send('⛔ حساب محدود است.');return true;}
    // A human operator must review images before approval.
    if(status==='verified') {
      await send('⚠️ قبل از تأیید، اسناد را بررسی کنید. نمایش اسناد: /kyc_view '+targetId);
      return true;
    }
    await db.update(nativeProfiles).set({kycStatus:status,
      verifiedBy:adminId,updatedAt:new Date().toISOString()})
      .where(eq(nativeProfiles.userId,targetId)).run();
    await audit('kyc_rejected','user_profile',targetId,adminId);
    await send('✅ احراز هویت رد شد.');
    return true;
  }
  match=text.match(/^\/kyc_view\s+(\d+)$/);
  if(match){
    const id=cleanId(match[1]);
    const p=await db.select().from(nativeProfiles).where(eq(nativeProfiles.userId,id)).get();
    if(!p || !p.idDocumentFileId || !p.selfieFileId){await send('سند موجود نیست.');return true;}
    const docs=await Promise.all([latestMedia(id,'KYC_ID'),latestMedia(id,'KYC_SELFIE')]);
    for(let k=0;k<docs.length;k++){
      const item=docs[k];
      if(!item)continue;
      const caption=(k?'KYC Selfie ':'KYC Document ')+id;
      if(item.mediaCategory==='document')
        await api.sendDocument({chat_id:adminId,document:item.telegramFileId,caption});
      else
        await api.sendPhoto({chat_id:adminId,photo:item.telegramFileId,caption});
    }
    await send('پس از مشاهده دقیق دو سند، برای تأیید /kyc_confirm '+id+' را بفرستید.');
    return true;
  }
  match=text.match(/^\/kyc_confirm\s+(\d+)$/);
  if(match) {
    const id=cleanId(match[1]);
    const [p]=await db.update(nativeProfiles).set({kycStatus:'verified',
      verifiedBy:adminId,updatedAt:new Date().toISOString()})
      .where(and(eq(nativeProfiles.userId,id),eq(nativeProfiles.kycStatus,'pending'),
        isNotNull(nativeProfiles.idDocumentFileId),isNotNull(nativeProfiles.selfieFileId)))
      .returning().run();
    if(!p || !p.idDocumentFileId || !p.selfieFileId){await send('اسناد یا وضعیت صحیح نیست.');return true;}
    await audit('kyc_verified','user_profile',id,adminId);
    await send('✅ تأیید هویت ثبت شد.');
    return true;
  }
  match=text.match(/^\/order_(review|cancel)\s+(\d+)$/);
  if(match) {
    const status=match[1]==='review'?'under_review':'cancelled',id=cleanId(match[2]);
    const order=await db.select().from(nativeOrders).where(eq(nativeOrders.id,id)).get();
    if(!order || !canTransition(order.status,status)) {await send('تغییر وضعیت مجاز نیست.');return true;}
    const [changed]=await db.update(nativeOrders).set({status,updatedAt:new Date().toISOString()})
      .where(and(eq(nativeOrders.id,id),eq(nativeOrders.status,order.status)))
      .returning().run();
    if(!changed){await send('تغییر هم‌زمان انجام شده؛ دوباره بررسی کنید.');return true;}
    await audit('order_status_changed','order',id,adminId,{status:order.status},{status});
    await send('✅ '+orderCode(changed)+' -> '+status);
    return true;
  }
  match=text.match(/^\/remit_review\s+(\d+)$/);
  if(match) {
    const id=cleanId(match[1]);
    const [remit]=await db.update(nativeRemittances).set({status:'under_review',
      updatedAt:new Date().toISOString()}).where(and(
        eq(nativeRemittances.id,id),eq(nativeRemittances.status,'transfer_submitted')))
        .returning().run();
    if(!remit){await send('حواله در وضعیت انتقال ثبت‌شده نیست.');return true;}
    await audit('remittance_under_review','remittance',id,adminId);
    await send('✅ حواله تحت بررسی است؛ انتقال هنوز تأیید نشده است.');
    return true;
  }
  return false;
}
