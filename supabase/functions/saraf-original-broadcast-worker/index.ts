// Execute original /broadcast against existing active Telegram bot users.
// ONLY signed cron bearer may run this service. OFF by default.
// Claims are single-use; network timeouts are marked UNCERTAIN, not retried,
// because Telegram may have delivered a message before losing the response.
import {createClient} from 'npm:@supabase/supabase-js@2.57.0';
const SECRET=Deno.env.get('SARAF_ORIGINAL_BROADCAST_CRON_TOKEN')||'';
const BOT=Deno.env.get('SARAF_TELEGRAM_BOT_TOKEN')||'';
const KEY=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const URL=Deno.env.get('SUPABASE_URL')||'';
const ENABLED=Deno.env.get('SARAF_ORIGINAL_BROADCAST_ENABLED')==='true';
function eq(a:string,b:string){
 if(!a||!b||a.length!==b.length)return false;
 let mismatch=0;for(let i=0;i<a.length;i++)mismatch|=a.charCodeAt(i)^b.charCodeAt(i);
 return mismatch===0;
}
const response=(status:number,body:unknown)=>new Response(JSON.stringify(body),{
 status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'},
});
async function sendMessage(id:number,message:string):
 Promise<{state:'sent'|'failed'|'uncertain';error?:string}>{
 try{
  const r=await fetch('https://api.telegram.org/bot'+BOT+'/sendMessage',{
   method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({chat_id:id,text:message,parse_mode:'Markdown',
    disable_web_page_preview:true}),
   signal:AbortSignal.timeout(7000),
  });
  if(r.ok)return {state:'sent'};
  // 429 and 400/403 are definitive HTTP rejections (no delivery).
  // Server errors may have delivered: never blindly retry them.
  return r.status>=500?{state:'uncertain',error:'TG_SERVER_UNKNOWN'}:
   {state:'failed',error:'TG_HTTP_'+r.status};
 }catch{return {state:'uncertain',error:'TG_NETWORK_UNKNOWN'};}
}
Deno.serve(async request=>{
 if(request.method!=='POST')return response(405,{error:'METHOD_NOT_ALLOWED'});
 if(SECRET.length<32||!eq(request.headers.get('authorization')||'','Bearer '+SECRET))
  return response(401,{error:'UNAUTHORIZED'});
 if(!ENABLED)return response(503,{error:'ORIGINAL_BROADCAST_DISABLED'});
 if(!BOT||!KEY||!URL)return response(503,{error:'SERVICE_NOT_CONFIGURED'});
 const db=createClient(URL,KEY,{auth:{persistSession:false,autoRefreshToken:false}});
 let sent=0,failed=0,uncertain=0,skipped=0;
 const started=Date.now();
 try{
  // At most 40 deliveries / tick. Short claims keep the 90s lease safe.
  // A 22s claim budget + 5*7s HTTP timeouts stays under typical Edge limits.
  // Sequential deliberate 50ms minimum gap
  // matches original main:handlers/admin.py broadcast rate limiting.
  for(let page=0;page<8;page++){
   if(Date.now()-started>22000)break;
   const claim=await db.rpc('saraf_original_broadcast_claim',{p_limit:5});
   if(claim.error)throw claim.error;
   const messages=claim.data||[];
   if(!messages.length)break;
   for(const item of messages){
    const id=Number(item.chat_id),broadcastId=Number(item.broadcast_id);
    if(!Number.isSafeInteger(id)||id<=0||!Number.isSafeInteger(broadcastId))
      throw Error('INVALID_DELIVERY_FROM_DATABASE');
    const recipient=await db.from('users').select('is_active')
      .eq('chat_id',id).maybeSingle();
    let result:{state:'sent'|'failed'|'uncertain'|'skipped';error?:string};
    if(recipient.error)result={state:'uncertain',error:'SUBSCRIPTION_CHECK_UNAVAILABLE'};
    else if(!recipient.data?.is_active)
      result={state:'skipped',error:'RECIPIENT_OPTED_OUT'};
    else result=await sendMessage(id,String(item.message||''));
    const stored=await db.rpc('saraf_original_broadcast_finish',{
     p_broadcast_id:broadcastId,p_chat_id:id,
     p_result:result.state,p_error:result.error||null,
    });
    if(stored.error||stored.data!==true)
      console.error('Saraf notification state update failed');
    if(result.state==='sent')sent++;
    if(result.state==='failed')failed++;
    if(result.state==='uncertain')uncertain++;
    if(result.state==='skipped')skipped++;
    await new Promise(resolve=>setTimeout(resolve,50));
   }
  }
  return response(200,{ok:true,sent,failed,uncertain,skipped});
 }catch(error){
  console.warn('Original Saraf notifications batch unavailable',
   String((error as {code?:string}).code||'BATCH_FAILED'));
  return response(503,{error:'BROADCAST_QUEUE_UNAVAILABLE',
   sent,failed,uncertain,skipped});
 }
});
