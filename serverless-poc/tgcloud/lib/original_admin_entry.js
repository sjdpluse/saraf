// Original /stats, /spreads, /setspread, /usdtpending, /usdtconfirm.
// Telegram Serverless has no documented server-side secrets store; do NOT
// forward an unsigned from.id to a privileged Supabase finance endpoint.
// Instead require Telegram's independently signed Mini App initData + server
// admin allowlist before any protected read or write.
import {api} from 'sdk';
const BASE='https://app8533795882.tgcloud.ai/';
import {parseOriginalAdminCommand} from './original_admin_parse.js';
export async function handleOriginalAdminCommand(message){
 const cmd=parseOriginalAdminCommand(message?.text);
 if(!cmd)return false;
 const chat=message.chat?.id;
 if(!Number.isSafeInteger(chat)||chat!==message.from?.id||
    message.chat?.type!=='private')return false;
 if(cmd.name==='broadcast'){
  await api.sendMessage({chat_id:chat,text:cmd.usage});
  return true;
 }
 // A URL alone gives no privilege. Original Supabase Edge checks HMAC
 // over initData and compares user ID against private SARAF_ADMIN_CHAT_IDS.
 const url=BASE+'?'+cmd.query.toString();
 await api.sendMessage({
  chat_id:chat,
  text:cmd.usage?cmd.usage+'\n\nمعلومات را در پنل مدیریت تکمیل کنید.':
    '🔐 برای اجرای دستور، هویت مدیر باید در Mini App اصلی تأیید شود.',
  reply_markup:{inline_keyboard:[[
   {text:'🔐 پنل مدیریت صراف',web_app:{url}},
  ]]},
 });
 return true;
}
