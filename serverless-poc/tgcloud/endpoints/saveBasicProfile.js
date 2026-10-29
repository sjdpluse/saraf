import { db } from 'sdk';
import { nativeProfiles } from '../schema.js';
import { actor, audit, checkText, invalid } from '../lib/native_auth.js';

export default async function (input,ctx) {
  const user=actor(ctx);
  const first=checkText(input?.first_name,'نام',2,80);
  const last=checkText(input?.last_name,'نام خانوادگی',2,80);
  const phone=String(input?.phone || '').trim();
  if (!/^\+?[0-9۰-۹٠-٩ ()\-]{7,24}$/.test(phone) || (phone.match(/[0-9۰-۹٠-٩]/g)||[]).length<7)
    invalid('شماره تماس معتبر نیست.');
  const now=new Date().toISOString();
  await db.insert(nativeProfiles).values({
    userId:user.id, username:String(user.username || '').slice(0,60),
    firstName:first,lastName:last,phone,updatedAt:now,
  }).onConflictDoUpdate({target:nativeProfiles.userId,set:{
    username:String(user.username || '').slice(0,60),
    firstName:first,lastName:last,phone,updatedAt:now,
  }}).run();
  await audit('basic_profile_saved','user_profile',user.id,user.id);
  return {ok:true};
}
