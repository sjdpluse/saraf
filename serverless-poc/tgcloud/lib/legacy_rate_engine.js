// Pure port of ORIGINAL main:services/spread_service.py, rate_engine.py,
// and jobs.py USD-only change trigger. No new rates or invented products.
export const DEFAULT_SPREADS=Object.freeze({
 usd:0.6,eur:0.8,gbp:1,aed:0.8,sar:0.8,pkr:1.5,irr:2,
 inr:1.5,try:1.5,cny:1.5,aud:1.2,cad:1.2,chf:1.2,sek:1.8,
});
const four=n=>Math.round(n*10000)/10000;
export function effectiveSpread(currency,storedSpreads={}){
 const name=String(currency||'').toLowerCase();
 const stored=storedSpreads[name],fallback=DEFAULT_SPREADS[name]??1.5;
 if(stored===null||stored===undefined)return fallback;
 const pct=Number(stored);
 if(!Number.isFinite(pct)||pct<0||pct>20)
  throw Error('INVALID_EXISTING_SPREAD');
 return pct;
}
export function applyOriginalSpread(basisRate,currency,storedSpreads={}){
 const rate=Number(basisRate);
 if(!Number.isFinite(rate)||rate<=0)throw Error('INVALID_BASIS_RATE');
 const pct=effectiveSpread(currency,storedSpreads);
 const half=pct/200;
 return {buy:four(rate*(1-half)),sell:four(rate*(1+half)),
  spread_percent:pct};
}
export function selectOriginalBasis(code,referenceRates,localMarkets,storedSpreads={}){
 const c=String(code||'').toLowerCase();
 const local=localMarkets?.sarai_shahzada?.[c];
 const ref=Number(referenceRates?.[c]);
 const validLocal=local&&Number.isFinite(Number(local.buy))&&
  Number.isFinite(Number(local.sell))&&local.buy>0&&local.sell>0;
 const basis=validLocal?'local':'reference';
 const rate=validLocal?(Number(local.buy)+Number(local.sell))/2:ref;
 if(!Number.isFinite(rate)||rate<=0)throw Error('NO_MARKET_RATE');
 const spread=applyOriginalSpread(rate,c,storedSpreads);
 return {code:c,reference_rate:ref>0?ref:null,
  local:validLocal?{market:'sarai_shahzada',
    market_label:'سرای شهزاده (کابل)',
    buy:Number(local.buy),sell:Number(local.sell)}:null,
  saraf_quote:{buy:spread.buy,sell:spread.sell,basis,
    basis_rate:four(rate)},
  spread_percent:spread.spread_percent};
}
export function historicalOriginalBasis(localRate,referenceRate){
 const local=localRate;
 if(local&&Number(local.buy)>0&&Number(local.sell)>0)
  return {rate:four((Number(local.buy)+Number(local.sell))/2),basis:'local'};
 if(Number(referenceRate)>0)
  return {rate:four(Number(referenceRate)),basis:'reference'};
 return {rate:null,basis:'none'};
}
export function shouldOriginalSocialPost(usdQuote,lastState,thresholdPct){
 // Matches original jobs.py: _usd_has_significant_change — only USD.
 const current=usdQuote?.local?.buy ?? usdQuote?.saraf_quote?.buy;
 const previous=Number(lastState?.usd);
 if(!(Number(current)>0))return false;
 if(!previous)return true;
 return Math.abs((Number(current)-previous)/previous*100)>=Number(thresholdPct);
}
