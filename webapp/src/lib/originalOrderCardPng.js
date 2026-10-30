// Original Saraf Apple Wallet / bento customer-card preview in browser PNG.
// Port of main:services/card_service.py + stablecoin_card_service.py.
// All amounts, networks, deposit address and profile are VERIFIED by
// saraf-original-transactions action=card.preview (signed initData).
// QR is generated locally using vendored MIT Nayuki encoder: private wallet
// addresses are NEVER sent to a third-party QR provider.
// This file does not create an actual financial order or approval.
import {qrcodegen} from './vendor/qrcodegen.ts';
import {SARAF_LOGO_URL,assetLogo} from './brand';

const PAL={
 bg:'#f5f5f7',paper:'#ffffff',ink:'#1d1d1f',muted:'#6e6e73',
 light:'#aeaeb4',blue:'#0071e3',green:'#1ca64c',red:'#ff3b30',
 border:'#e8e8ed',cell:'#f7f7f9',gold:'#a87818',
};
const SIZE={width:1320,height:900};

export function validateOriginalPreview(source){
 const order=source?.order_preview;
 const profile=source?.profile;
 if(!order||!profile||!['buy','sell'].includes(order.order_type)
   ||!['USDT','USDC'].includes(order.asset)
   ||!Number.isFinite(Number(order.usdt_amount))
   ||Number(order.usdt_amount)<=0
   ||!Number.isFinite(Number(order.total_afn))
   ||Number(order.total_afn)<=0
   ||!Number.isFinite(Number(order.usd_rate))
   ||Number(order.usd_rate)<=0
   ||!order.exchange_name||!order.network
   ||!profile.first_name||!profile.last_name||!profile.phone)
   throw Error('ORIGINAL_CARD_DATA_INVALID');
 const wallet=String(order.wallet_address||order.deposit_address||'').trim();
 if(wallet.length<8||wallet.length>128||/\s/.test(wallet))
   throw Error('ORIGINAL_CARD_WALLET_INVALID');
 return {order,profile,wallet};
}
function rect(ctx,x,y,w,h,r,fill,border=''){
 ctx.beginPath();const t=Math.max(0,Math.min(r,w/2,h/2));
 ctx.moveTo(x+t,y);ctx.arcTo(x+w,y,x+w,y+h,t);
 ctx.arcTo(x+w,y+h,x,y+h,t);ctx.arcTo(x,y+h,x,y,t);
 ctx.arcTo(x,y,x+w,y,t);ctx.closePath();
 ctx.fillStyle=fill;ctx.fill();
 if(border){ctx.lineWidth=2;ctx.strokeStyle=border;ctx.stroke();}
}
function text(ctx,value,x,y,size=20,opt={}){
 ctx.font=`${opt.bold?'700':'500'} ${size}px Vazirmatn, Tahoma, Arial, sans-serif`;
 ctx.fillStyle=opt.color||PAL.ink;
 ctx.direction=opt.ltr?'ltr':'rtl';
 ctx.textAlign=opt.align||'right';
 ctx.textBaseline='middle';
 const raw=String(value??'');
 ctx.fillText(raw,x,y,opt.maxWidth||Infinity);
}
function money(x,digits=0){
 return Number(x||0).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
}
function renderQr(ctx,address,x,y,side=215){
 const qr=qrcodegen.QrCode.encodeText(address,qrcodegen.QrCode.Ecc.MEDIUM);
 const n=qr.size,quiet=2,cell=Math.floor(side/(n+quiet*2));
 if(cell<2)throw Error('ORIGINAL_CARD_QR_TOO_DENSE');
 const px=cell*(n+quiet*2);
 const left=x+(side-px)/2,top=y+(side-px)/2;
 ctx.fillStyle='#ffffff';ctx.fillRect(x,y,side,side);
 ctx.fillStyle='#161616';
 for(let row=0;row<n;row++){
  for(let col=0;col<n;col++){
   if(qr.getModule(col,row))
    ctx.fillRect(left+(col+quiet)*cell,top+(row+quiet)*cell,cell,cell);
  }
 }
}
function stat(ctx,x,y,w,h,label,value,opts={}){
 rect(ctx,x,y,w,h,26,PAL.cell,PAL.border);
 text(ctx,label,x+w-24,y+28,17,{color:PAL.muted,maxWidth:w-48});
 text(ctx,value,x+w-24,y+h-39,opts.size||28,{
  bold:true,color:opts.color||PAL.ink,maxWidth:w-48,
 });
}
async function publicLogo(src){
 return new Promise(resolve=>{
  const img=new Image();img.crossOrigin='anonymous';
  const timer=setTimeout(()=>{img.onload=null;img.onerror=null;resolve(null);},3000);
  img.onload=()=>{clearTimeout(timer);resolve(img)};
  img.onerror=()=>{clearTimeout(timer);resolve(null)};
  img.src=src;
 });
}
function blob(canvas){
 return new Promise((resolve,reject)=>canvas.toBlob(
  value=>value?.type==='image/png'&&value.size>2000
    ?resolve(value):reject(Error('ORIGINAL_CARD_PNG_UNAVAILABLE')),
  'image/png'
 ));
}
export async function renderOriginalOrderCardPreview(source){
 const {order,profile,wallet}=validateOriginalPreview(source);
 if(typeof document==='undefined')throw Error('CANVAS_UNAVAILABLE');
 const canvas=document.createElement('canvas');
 canvas.width=SIZE.width;canvas.height=SIZE.height;
 const ctx=canvas.getContext('2d');
 if(!ctx)throw Error('CANVAS_UNAVAILABLE');
 await Promise.race([document.fonts?.ready||Promise.resolve(),
  new Promise(resolve=>setTimeout(resolve,2000))]);
 const isBuy=order.order_type==='buy';
 const accent=isBuy?PAL.green:PAL.red;
 const asset=order.asset;
 ctx.fillStyle=PAL.bg;ctx.fillRect(0,0,1320,900);
 ctx.save();ctx.shadowColor='rgba(0,0,0,.10)';
 ctx.shadowBlur=32;ctx.shadowOffsetY=12;
 rect(ctx,46,46,1228,808,44,PAL.paper);ctx.restore();
 rect(ctx,46,46,1228,808,44,PAL.paper);
 const [saraf,coin]=await Promise.all([
  publicLogo(SARAF_LOGO_URL),publicLogo(assetLogo(asset))]);
 if(saraf)try{ctx.drawImage(saraf,96,92,64,64)}catch{}
 if(!saraf)text(ctx,'S',116,122,44,{color:PAL.blue,ltr:true,align:'left',bold:true});
 text(ctx,'صراف',172,105,30,{bold:true,align:'left'});
 text(ctx,'کارت دیجیتال مشتری',172,145,18,{color:PAL.muted,align:'left'});
 rect(ctx,1000,94,224,42,21,isBuy?'#e3f6ea':'#ffebea');
 text(ctx,isBuy? 'خرید '+asset:'فروش '+asset,1112,115,20,{bold:true,color:accent,align:'center'});
 ctx.strokeStyle=PAL.border;ctx.lineWidth=2;
 ctx.beginPath();ctx.moveTo(96,188);ctx.lineTo(1224,188);ctx.stroke();
 // The legacy renderer displays a private KYC selfie if present.
 // On native preview, verified personal metadata are shown instead; no
 // private selfie is downloaded into a public browser canvas.
 const displayName=[profile.first_name,profile.last_name].filter(Boolean).join(' ').trim();
 ctx.fillStyle='#edf5ff';ctx.beginPath();ctx.arc(165,287,69,0,Math.PI*2);ctx.fill();
 ctx.strokeStyle=accent;ctx.lineWidth=4;ctx.stroke();
 text(ctx,displayName.slice(0,1)||'ص',165,291,56,
  {bold:true,color:PAL.blue,align:'center'});
 text(ctx,displayName,265,239,32,{bold:true,align:'left',maxWidth:585});
 const kycs={pending:'در انتظار تایید',verified:'هویت تایید‌شده',
  trusted:'مشتری معتمد',restricted:'محدودشده'};
 rect(ctx,265,272,225,38,19,'#eef4ff');
 text(ctx,kycs[profile.kyc_status]||kycs.pending,377,291,17,
  {color:PAL.blue,bold:true,align:'center'});
 if(profile.trust_score!=null){
  rect(ctx,502,272,156,38,19,PAL.cell);
  text(ctx,'⭐ '+profile.trust_score+'/100',580,291,17,
   {color:PAL.muted,align:'center'});
 }
 text(ctx,profile.phone,265,328,18,{ltr:true,align:'left',color:PAL.light});
 text(ctx,'درخواست '+(isBuy?'خرید ':'فروش ')+money(order.usdt_amount,0)+
  ' '+asset+' از طریق '+order.exchange_name+' — شبکهٔ '+order.network,
  96,395,20,{color:PAL.muted,align:'left',maxWidth:785});
 const x=96,y=436,w=383,g=22,h=114;
 stat(ctx,x,y,w,h,'مقدار '+asset,money(order.usdt_amount,0)+' '+asset,
  {size:30,color:accent});
 stat(ctx,x+w+g,y,w,h,'مبلغ کل',money(order.total_afn,0)+' AFN');
 stat(ctx,x,y+h+g,w,h,'صرافی / شبکه',
  order.exchange_name+' / '+order.network,{size:19});
 stat(ctx,x+w+g,y+h+g,w,h,'نرخ هر دالر',
  money(order.usd_rate,2)+' AFN',{size:24});
 rect(ctx,96,712,598,62,31,'#0040c9');
 text(ctx,'پیگیری سفارش در ربات صراف',395,743,20,
  {color:'#fff',bold:true,align:'center'});
 rect(ctx,715,712,62,62,31,PAL.cell,PAL.border);
 text(ctx,'SOS',746,743,18,{color:PAL.blue,bold:true,align:'center',ltr:true});
 rect(ctx,793,712,62,62,31,PAL.cell,PAL.border);
 text(ctx,['verified','trusted'].includes(profile.kyc_status)?'✓':'…',
  824,743,26,{color:PAL.green,align:'center',bold:true});
 // ORIGINAL qr column: address is the verified user wallet for buy,
 // and the configured server-side Saraf deposit wallet for sell.
 rect(ctx,924,214,300,300,26,'#f5faff',PAL.border);
 rect(ctx,950,236,248,248,20,'#ffffff');
 renderQr(ctx,wallet,966,252,216);
 text(ctx,'آدرس واریز — اسکن کنید',1074,476,16,
  {align:'center',color:PAL.muted});
 const short=wallet.length>20?wallet.slice(0,8)+'…'+wallet.slice(-6):wallet;
 text(ctx,short,1074,496,14,{ltr:true,align:'center',color:PAL.light});
 rect(ctx,924,536,300,118,26,PAL.cell,PAL.border);
 text(ctx,'کد سفارش',1202,566,16,{color:PAL.muted});
 text(ctx,'PREVIEW',1202,610,28,{ltr:true,bold:true});
 rect(ctx,924,676,300,128,26,PAL.cell,PAL.border);
 text(ctx,'معاملات موفق',1202,702,16,{color:PAL.muted});
 text(ctx,String(profile.successful_orders??0),1202,732,22,{bold:true});
 text(ctx,'فقط پیش‌نمایش، نه رسید پرداخت',1202,772,16,{color:PAL.muted});
 if(coin)try{ctx.drawImage(coin,1126,89,58,58)}catch{}
 return await blob(canvas);
}
