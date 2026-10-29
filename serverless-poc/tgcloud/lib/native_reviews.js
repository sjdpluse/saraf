import { db } from 'sdk';
import { and,eq,desc,sql } from 'sdk/db';
import { nativeReviews,nativeVotes } from '../schema.js';
import { actor,audit,checkId,checkText,isOperator,invalid,requireOperator } from './native_auth.js';

export async function reviewDto(row,userId) {
  const votes=await db.select().from(nativeVotes)
    .where(eq(nativeVotes.reviewId,row.id)).all();
  return {
    id:row.id,display_name:row.displayName,body:row.body,
    admin_reply:row.adminReply,admin_replied_at:row.adminRepliedAt,
    created_at:row.createdAt,
    likes:votes.filter(v=>v.vote===1).length,
    dislikes:votes.filter(v=>v.vote===-1).length,
    user_vote:votes.find(v=>v.userId===userId)?.vote || 0,
  };
}
export async function listReviews(input,ctx) {
  const user=actor(ctx);
  const limit=Math.min(50,Math.max(1,Number(input?.limit)||20));
  const offset=Math.max(0,Number(input?.offset)||0);
  if (!Number.isSafeInteger(limit)||!Number.isSafeInteger(offset)||offset>2000)
    invalid('صفحه‌بندی معتبر نیست.');
  const rows=await db.select().from(nativeReviews)
    .where(eq(nativeReviews.visible,1))
    .orderBy(desc(nativeReviews.id)).limit(limit).offset(offset).all();
  const items=await Promise.all(rows.map(row=>reviewDto(row,user.id)));
  const total=await db.$count(nativeReviews,eq(nativeReviews.visible,1));
  return {items,total,is_admin:isOperator(user.id)};
}
export async function createReview(input,ctx) {
  const user=actor(ctx);
  const body=checkText(input?.body,'متن نظر',3,1000);
  const latest=await db.select().from(nativeReviews)
    .where(eq(nativeReviews.userId,user.id)).orderBy(desc(nativeReviews.id)).limit(1).get();
  if (latest && Date.now()-Date.parse(latest.createdAt)<60_000)
    invalid('لطفاً یک دقیقه بعد نظر دیگر ثبت کنید.','RATE_LIMIT');
  const displayName=String([user.first_name,user.last_name].filter(Boolean).join(' ')||'کاربر صراف').slice(0,100);
  const [row]=await db.insert(nativeReviews).values({
    userId:user.id,displayName,body,createdAt:new Date().toISOString(),visible:1,
  }).returning().run();
  await audit('review_created','review',row.id,user.id);
  return reviewDto(row,user.id);
}
export async function voteReview(input,ctx) {
  const user=actor(ctx),reviewId=checkId(input?.review_id);
  const vote=Number(input?.vote);
  if (!Number.isSafeInteger(vote)||![-1,0,1].includes(vote)) invalid('رأی معتبر نیست.');
  const review=await db.select().from(nativeReviews).where(and(
    eq(nativeReviews.id,reviewId),eq(nativeReviews.visible,1))).get();
  if(!review) invalid('نظر پیدا نشد.','NOT_FOUND');
  if(vote===0) {
    await db.delete(nativeVotes).where(and(eq(nativeVotes.reviewId,reviewId),
      eq(nativeVotes.userId,user.id))).run();
  } else {
    await db.insert(nativeVotes).values({
      reviewId,userId:user.id,vote,updatedAt:new Date().toISOString(),
    }).onConflictDoUpdate({target:[nativeVotes.reviewId,nativeVotes.userId],
      set:{vote,updatedAt:new Date().toISOString()}}).run();
  }
  const updated=await reviewDto(review,user.id);
  return {review_id:reviewId,likes:updated.likes,dislikes:updated.dislikes,user_vote:updated.user_vote};
}
export async function replyReview(input,ctx) {
  const admin=requireOperator(ctx),id=checkId(input?.review_id);
  const body=checkText(input?.body,'پاسخ مدیر',2,1000);
  const [row]=await db.update(nativeReviews).set({
    adminReply:body,adminRepliedAt:new Date().toISOString(),
  }).where(and(eq(nativeReviews.id,id),eq(nativeReviews.visible,1))).returning().run();
  if(!row) invalid('نظر پیدا نشد.','NOT_FOUND');
  await audit('review_replied','review',id,admin.id);
  return reviewDto(row,admin.id);
}
