// Admin-uploaded ORIGINAL transaction media: send to the CUSTOMER bot's
// private admin chat to obtain a real Telegram file_id reusable by that bot.
// No public Supabase media URL and no separate storage/finance ledger.
import {issueOriginalProof} from './proof.mjs';

const bad=(code,status=400)=>Object.assign(new Error(code),{status});
function imageType(file,head){
 const j=head[0]===255&&head[1]===216&&head[2]===255;
 const p=head.length>=8&&[137,80,78,71,13,10,26,10].every((v,i)=>head[i]===v);
 const w=head.length>=12&&[82,73,70,70].every((v,i)=>head[i]===v)&&
  [87,69,66,80].every((v,i)=>head[i+8]===v);
 const pdf=head.length>=5&&[37,80,68,70,45].every((v,i)=>head[i]===v);
 if(j&&file.type==='image/jpeg')return {type:'photo',name:'transaction-details.jpg'};
 if(p&&file.type==='image/png')return {type:'photo',name:'transaction-details.png'};
 if(w&&file.type==='image/webp')return {type:'photo',name:'transaction-details.webp'};
 if(pdf&&file.type==='application/pdf')return {type:'document',name:'transaction-details.pdf'};
 throw bad('UNSUPPORTED_PROOF_MEDIA');
}
export async function uploadOriginalAdminProof(req,actorId,bot,db){
 if(req.method!=='POST')throw bad('METHOD_NOT_ALLOWED',405);
 const length=Number(req.headers.get('content-length')||0);
 if(!Number.isFinite(length)||length>9*1024*1024)
  throw bad('COMPLETION_PROOF_TOO_LARGE',413);
 const form=await req.formData();
 const orderId=Number(form.get('order_id'));
 const file=form.get('file');
 if(!Number.isSafeInteger(orderId)||orderId<=0)throw bad('INVALID_ORDER_ID');
 if(!(file instanceof File)||file.size<12||file.size>8*1024*1024)
  throw bad('COMPLETION_PROOF_TOO_LARGE',413);
 const current=await db.from('usdt_orders').select('id,status,asset')
  .eq('id',orderId).maybeSingle();
 if(current.error)throw bad('ORIGINAL_ORDER_UNAVAILABLE',503);
 if(!current.data||current.data.status!=='confirmed')
  throw bad('INVALID_ORDER_TRANSITION',409);
 const raw=new Uint8Array(await file.arrayBuffer());
 const meta=imageType(file,raw.subarray(0,16));
 // Only administrator-initiated messages. The file is uploaded to Telegram
 // using the same ORIGINAL customer bot identity used for customer delivery.
 const multipart=new FormData();
 multipart.set('chat_id',String(actorId));
 multipart.set('caption','📎 Transaction Details — '+
  (current.data.asset==='USDC'?'USDC':'USDT')+'-'+String(orderId).padStart(5,'0'));
 const mime=meta.type==='document'?'application/pdf':file.type;
 multipart.set(meta.type==='photo'?'photo':'document',
  new File([raw],meta.name,{type:mime}),meta.name);
 let response;
 try{
  response=await fetch('https://api.telegram.org/bot'+bot+
    (meta.type==='photo'?'/sendPhoto':'/sendDocument'),{
    method:'POST',body:multipart,signal:AbortSignal.timeout(35000),
  });
 }catch{throw bad('TELEGRAM_PROOF_UPLOAD_UNAVAILABLE',503);}
 if(!response.ok)throw bad('TELEGRAM_PROOF_UPLOAD_UNAVAILABLE',503);
 let received;
 try{received=await response.json();}catch{throw bad('TELEGRAM_PROOF_UPLOAD_UNAVAILABLE',503);}
 const message=received?.result;
 const identifier=meta.type==='photo'
  ?message?.photo?.at(-1)?.file_id:message?.document?.file_id;
 if(!received?.ok||!identifier||message?.chat?.id!==actorId)
  throw bad('TELEGRAM_PROOF_UPLOAD_UNAVAILABLE',503);
 const proof_token=await issueOriginalProof(bot,{
  order_id:orderId,actor_id:actorId,file_id:identifier,
  file_type:meta.type,file_name:meta.name,
 });
 return {proof_token,order_id:orderId,file_type:meta.type,expires_in_seconds:600};
}
