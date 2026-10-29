// Pure migration of main:services/currency_service.py, gold_service.py,
// silver_service.py and local_market_service.py data shapes. No new prices.
export const CODES=['usd','eur','gbp','pkr','irr','aed','inr','sar','try','cny','aud','cad','chf','sek'];
const urls=[
 'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/afn.json',
 'https://latest.currency-api.pages.dev/v1/currencies/afn.json',
 'https://api.exchangerate-api.com/v4/latest/USD',
];
const four=n=>Math.round(n*10000)/10000;
const one=n=>Math.round(n*10)/10;
async function jsonFetch(url,http){
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),10000);
 try{
  const res=await http(url,{signal:ctrl.signal,headers:{'Accept':'application/json'}});
  if(!res.ok)throw Error('UPSTREAM_UNAVAILABLE');
  return res.json();
 }finally{clearTimeout(timer);}
}
export async function fetchOriginalCurrencyRates(http=fetch){
 let lastError;
 for(let i=0;i<urls.length;i++){
  try{
   const data=await jsonFetch(urls[i],http),rates={};
   if(i!==2){
    const base=data?.afn;
    if(!base||typeof base!=='object')continue;
    for(const code of CODES){
      const unit=Number(base[code]);
      if(Number.isFinite(unit)&&unit>0)rates[code]=four(1/unit);
    }
   }else{
    const base=Number(data?.rates?.AFN);
    if(!Number.isFinite(base)||base<=0)continue;
    for(const code of CODES){
      const unit=Number(data.rates[code.toUpperCase()]);
      if(Number.isFinite(unit)&&unit>0)rates[code]=four(base/unit);
    }
   }
   if(rates.usd&&Object.keys(rates).length>=4)return rates;
  }catch(error){lastError=error;}
 }
 throw lastError||Error('NO_CURRENCY_REFERENCE_SOURCE');
}
export async function fetchOriginalMetal(symbol,http=fetch){
 if(!['XAU','XAG'].includes(symbol))throw Error('INVALID_METAL_SYMBOL');
 const response=await jsonFetch('https://api.gold-api.com/price/'+symbol,http);
 for(const field of ['price','rate','value']){
   const value=Number(response?.[field]);
   if(Number.isFinite(value)&&value>0)return value;
 }
 throw Error('NO_METAL_RATE');
}
export function goldSnapshot(priceUsd,afnUsd){
 if(!Number.isFinite(priceUsd)||priceUsd<=0||!Number.isFinite(afnUsd)||afnUsd<=0)
   throw Error('INVALID_SNAPSHOT_RATE');
 return {price_usd_per_oz:priceUsd,
  afn_per_gram_24k:one(priceUsd*afnUsd/31.1034768)};
}
export function silverSnapshot(priceUsd,afnUsd){
 if(!Number.isFinite(priceUsd)||priceUsd<=0||!Number.isFinite(afnUsd)||afnUsd<=0)
   throw Error('INVALID_SNAPSHOT_RATE');
 return {price_usd_per_oz:priceUsd,
  afn_per_gram:one(priceUsd*afnUsd/31.1034768)};
}
const MARKETS={'sarai-shahzada':'sarai_shahzada',
 'khorasan-market':'khorasan_market','da-afg-bank':'da_afg_bank'};
const digits=s=>String(s).replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-1776))
 .replace(/[٠-٩]/g,c=>String(c.charCodeAt(0)-1632));
const clean=s=>digits(s.replace(/<[^>]*>/g,' ').replace(/&nbsp;/g,' ')
 .replace(/\s+/g,' ').trim());
const number=s=>Number(clean(s).replace(/[^0-9.]/g,''));
export function parseOriginalLocalRates(html){
 if(typeof html!=='string'||html.length>2000000)throw Error('INVALID_MARKET_RESPONSE');
 const markets=Object.fromEntries(Object.values(MARKETS).map(x=>[x,{}]));
 for(const [,tr] of html.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr\s*>/gi)){
  const url=tr.match(/\/exchange-rates\/(sarai-shahzada|khorasan-market|da-afg-bank)\/([a-z]{3})-AFN/i);
  if(!url)continue;
  const market=MARKETS[url[1].toLowerCase()],code=url[2].toLowerCase();
  if(!CODES.includes(code)||markets[market][code])continue;
  const cells=[...tr.matchAll(/<td\b[^>]*>([\s\S]*?)<\/td\s*>/gi)];
  if(cells.length<3)continue;
  const buy=number(cells[1][1]),sell=number(cells[2][1]);
  if(!(buy>0&&sell>0))continue;
  const multiple=/هزار/.test(clean(cells[0][1]))?1000:1;
  markets[market][code]={buy:Math.round(buy/multiple*1e6)/1e6,
   sell:Math.round(sell/multiple*1e6)/1e6};
 }
 return markets;
}
export async function fetchOriginalLocalMarkets(http=fetch){
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),12000);
 try{
  const res=await http('https://sarafi.af/fa/exchange-rates/sarai-shahzada',{
   signal:ctrl.signal,headers:{'Accept-Language':'fa,en;q=0.8',
    'User-Agent':'Mozilla/5.0 Saraf/1.0'},
  });
  if(!res.ok)throw Error('LOCAL_MARKET_UNAVAILABLE');
  const markets=parseOriginalLocalRates(await res.text());
  if(!Object.values(markets).some(m=>Object.keys(m).length))
   throw Error('LOCAL_MARKET_EMPTY');
  return markets;
 }finally{clearTimeout(timer);}
}
