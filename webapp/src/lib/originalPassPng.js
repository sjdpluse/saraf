// Railway-free PNG rendering of the ORIGINAL in-person Saraf pass.
// Mirrors main:services/in_person_pass_service.py dimensions, content,
// action labels and positioning. No customer data or pass code is uploaded.
// Used ONLY in native Telegram builds; legacy FastAPI remains unchanged.
import {SARAF_LOGO_URL,assetLogo} from './brand';
import {
 IN_PERSON_ADDRESS,IN_PERSON_REPRESENTATIVE_PHONE,SARAF_SUPPORT_PHONE,
} from './inPerson';
import {showConfirm} from './telegram';
import {originalPassInput} from './originalPassData.mjs';
export {originalPassInput} from './originalPassData.mjs';

const fill='#1d1d1f',muted='#6e6e73',blue='#0071e3';
function rr(ctx,x,y,w,h,r,color,stroke=null){
 ctx.beginPath();
 const rad=Math.min(r,w/2,h/2);
 ctx.moveTo(x+rad,y);ctx.arcTo(x+w,y,x+w,y+h,rad);
 ctx.arcTo(x+w,y+h,x,y+h,rad);ctx.arcTo(x,y+h,x,y,rad);
 ctx.arcTo(x,y,x+w,y,rad);ctx.closePath();
 ctx.fillStyle=color;ctx.fill();
 if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=2;ctx.stroke();}
}
function write(ctx,text,x,y,size=24,color=fill,options={}){
 ctx.fillStyle=color;ctx.font=`${options.bold?'700':'500'} ${size}px Vazirmatn, Tahoma, sans-serif`;
 ctx.direction=options.rtl===false?'ltr':'rtl';
 ctx.textAlign=options.align||'center';
 ctx.textBaseline='middle';
 ctx.fillText(String(text),x,y,options.maxWidth||1100);
}
function drawPill(ctx,x,y,w,h,text,opts={}){
 rr(ctx,x,y,w,h,Math.min(h/2,24),opts.bg||'#f8f8fa',opts.border||null);
 write(ctx,text,x+w/2,y+h/2,opts.size||20,opts.color||fill,{bold:opts.bold});
}
async function logo(url){
 // The originals are public logos. A failed or CORS-blocked logo MUST NOT
 // taint the private customer PNG; fall back to text rather than proxying it.
 return new Promise(resolve=>{
  if(typeof Image==='undefined')return resolve(null);
  const img=new Image();img.crossOrigin='anonymous';
  const timer=setTimeout(()=>{img.onload=null;img.onerror=null;resolve(null);},3500);
  img.onload=()=>{clearTimeout(timer);resolve(img);};
  img.onerror=()=>{clearTimeout(timer);resolve(null);};
  img.src=url;
 });
}
function pngBlob(canvas){
 return new Promise((resolve,reject)=>{
  if(typeof canvas.toBlob!=='function')return reject(Error('PNG_UNAVAILABLE'));
  canvas.toBlob(blob=>{
   if(blob?.size>1500&&blob.type==='image/png')resolve(blob);
   else reject(Error('PNG_ENCODING_FAILED'));
  },'image/png');
 });
}
export async function renderOriginalInPersonPass(fields){
 const p=originalPassInput(fields);
 if(typeof document==='undefined')throw Error('CANVAS_UNAVAILABLE');
 const canvas=document.createElement('canvas');
 canvas.width=1200;canvas.height=760;
 const ctx=canvas.getContext('2d');
 if(!ctx)throw Error('CANVAS_UNAVAILABLE');
 await Promise.race([
  document.fonts?.ready||Promise.resolve(),
  new Promise(resolve=>setTimeout(resolve,2000)),
 ]);
 ctx.fillStyle='#f5f5f7';ctx.fillRect(0,0,1200,760);
 rr(ctx,70,55,1060,650,48,'#ffffff','#e1e4ea');
 rr(ctx,70,55,1060,180,48,'#f2f8ff');
 ctx.fillStyle='#f2f8ff';ctx.fillRect(70,185,1060,50);
 const [saraf,coin]=await Promise.all([logo(SARAF_LOGO_URL),logo(assetLogo(p.asset))]);
 if(saraf)try{ctx.drawImage(saraf,112,102,82,82);}catch{}
 if(!saraf)write(ctx,'S',152,142,56,blue,{rtl:false,bold:true});
 if(coin){
  ctx.save();ctx.beginPath();ctx.arc(1040,142,38,0,2*Math.PI);ctx.clip();
  try{ctx.drawImage(coin,1002,104,76,76);}catch{}
  ctx.restore();
 }else{
  ctx.fillStyle=p.asset==='USDT'?'#26a17b':'#2775ca';
  ctx.beginPath();ctx.arc(1040,142,38,0,Math.PI*2);ctx.fill();
  write(ctx,p.asset.slice(0,1),1040,142,34,'#fff',{rtl:false,bold:true});
 }
 write(ctx,'SARAF',220,126,34,fill,{rtl:false,align:'left',bold:true});
 write(ctx,'کارت مراجعهٔ حضوری',220,168,21,muted,{align:'left'});
 write(ctx,p.asset,1040,205,21,fill,{rtl:false,bold:true});
 write(ctx,p.actionFa,600,300,34,fill,{bold:true});
 write(ctx,IN_PERSON_ADDRESS,600,354,21,muted);
 rr(ctx,380,395,440,150,28,'#f4f9ff','#d3e4fa');
 write(ctx,'کد مراجعه',600,430,18,muted);
 write(ctx,p.code,600,498,62,blue,{rtl:false,bold:true});
 drawPill(ctx,125,585,450,80,'',{bg:'#f8f8fa',border:'#e8e8eb'});
 drawPill(ctx,625,585,450,80,'',{bg:'#f8f8fa',border:'#e8e8eb'});
 write(ctx,'شماره نماینده صراف',350,608,18,muted);
 write(ctx,IN_PERSON_REPRESENTATIVE_PHONE,350,642,25,fill,{rtl:false,bold:true});
 write(ctx,'پشتیبانی صراف',850,608,18,muted);
 write(ctx,SARAF_SUPPORT_PHONE,850,642,25,fill,{rtl:false,bold:true});
 const blob=await pngBlob(canvas);
 return {blob,fileName:p.fileName};
}

export async function saveOriginalPassLocally(blob,fileName){
 if(!(blob instanceof Blob)||blob.type!=='image/png'||!blob.size)
  throw Error('PNG_INVALID');
 const safeName=String(fileName||'').match(/^saraf-(buy|sell)-(USDT|USDC)-[0-9]{4}\.png$/)?.[0];
 if(!safeName)throw Error('FILENAME_INVALID');
 // File System Access confirms a *real* write, not merely a click.
 if(typeof window!=='undefined'&&typeof window.showSaveFilePicker==='function'){
  try{
   const handle=await window.showSaveFilePicker({
    suggestedName:safeName,types:[{description:'PNG',accept:{'image/png':['.png']}}],
   });
   const writer=await handle.createWritable();
   await writer.write(blob);await writer.close();
   return true;
  }catch(e){if(e?.name==='AbortError')return false;throw e;}
 }
 // Telegram WebView and mobile browsers usually lack showSaveFilePicker:
 // initiate a local download, then require *explicit user confirmation*.
 // Never use Telegram.downloadFile(blob:) since that API requires HTTPS.
 const link=document.createElement('a');
 const objectUrl=URL.createObjectURL(blob);
 try{
  link.href=objectUrl;link.download=safeName;link.rel='noopener noreferrer';
  document.body.appendChild(link);link.click();link.remove();
  return await showConfirm('کارت مراجعه به‌صورت فایل PNG آماده شد. آیا دانلود و ذخیرهٔ فایل را تأیید می‌کنید؟');
 }finally{
  link.remove();
  setTimeout(()=>URL.revokeObjectURL(objectUrl),60000);
 }
}
