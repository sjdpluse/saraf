// Exact arithmetic port of original main:services/money.py and
// services/usdt_service.py. PURE computations only; no order creation,
// wallet writes, prices, payment endpoints or server secrets.
const SCALE=100000000n;
const Q={afn:10000000n,usd:1000000n,rate:10000n,percent:1000000n};
const pow10=n=>10n**BigInt(n);
function dec(raw) {
 const s=String(raw);
 const match=/^(0|[1-9][0-9]*)(?:\.([0-9]{1,8}))?$/.exec(s);
 if(!match)throw Error('INVALID_FINANCIAL_NUMBER');
 const fractional=match[2]||'';
 return BigInt(match[1])*SCALE+BigInt(fractional.padEnd(8,'0'));
}
function mul(a,b){return (a*b+SCALE/2n)/SCALE;}
function div(a,b){if(!b)throw Error('ZERO_DENOMINATOR');return (a*SCALE+b/2n)/b;}
function quant(a,quantum){return (a+quantum/2n)/quantum*quantum;}
function num(a){return Number(a)/Number(SCALE);}
const pr=(a,q)=>num(quant(a,Q[q]));
const percentage=n=>div(n,dec('100'));
const max=(a,b)=>a>b?a:b;
export const exactMoney={parse:dec,multiply:mul,divide:div,round:quant,
 toNumber:num,scale:SCALE};
export function originalBuyPricing(amount,usdRate){
 const a=dec(amount),rate=dec(usdRate);
 if(a<=0||rate<=0)throw Error('INVALID_TRADE_VALUE');
 const margin=max(dec('2'),mul(a,dec('0.025')));
 const supplier=mul(margin,dec('0.5'));
 const saraf=mul(margin,dec('0.3'));
 const discount=mul(margin,dec('0.2'));
 const supplierPayout=a+supplier;
 const customerPayable=supplierPayout+saraf;
 const marketPrice=a+margin;
 return {
  market_margin_usd:pr(margin,'usd'),
  market_margin_percent:pr(mul(div(margin,a),dec('100')),'percent'),
  supplier_share_percent:50,saraf_share_percent:30,
  customer_discount_share_percent:20,
  supplier_profit_usd:pr(supplier,'usd'),
  saraf_profit_usd:pr(saraf,'usd'),
  customer_discount_usd:pr(discount,'usd'),
  supplier_payout_usd:pr(supplierPayout,'usd'),
  market_price_usd:pr(marketPrice,'usd'),
  customer_payable_usd:pr(customerPayable,'usd'),
  effective_premium_percent:pr(mul(div(customerPayable-a,a),dec('100')),'percent'),
  base_afn:pr(mul(a,rate),'afn'),
  supplier_profit_afn:pr(mul(supplier,rate),'afn'),
  saraf_profit_afn:pr(mul(saraf,rate),'afn'),
  customer_discount_afn:pr(mul(discount,rate),'afn'),
  supplier_payout_afn:pr(mul(supplierPayout,rate),'afn'),
  market_price_afn:pr(mul(marketPrice,rate),'afn'),
  total_afn:pr(mul(customerPayable,rate),'afn'),
 };
}
export function originalSellPricing(amount,usdRate){
 const a=dec(amount),rate=dec(usdRate);
 if(a<=0||rate<=0)throw Error('INVALID_TRADE_VALUE');
 return {asset:null,amount:num(a),usd_rate:pr(rate,'rate'),
  total_afn:pr(mul(a,rate),'afn'),total_usd:pr(a,'usd'),
  receivable_usd:pr(a,'usd')};
}
export function originalRemittancePricing(amount,usdRate,feePercent=0){
 const a=dec(amount),r=dec(usdRate),fee=dec(feePercent);
 if(a<=0||r<=0||fee>dec('100'))throw Error('INVALID_REMITTANCE_INPUT');
 const gross=mul(a,r),feeAfn=mul(gross,percentage(fee));
 const payout=max(0n,gross-feeAfn);
 return {crypto_amount:num(a),usd_rate:pr(r,'rate'),
  gross_afn:pr(gross,'afn'),
  fee_percent:pr(fee,'percent'),fee_afn:pr(feeAfn,'afn'),
  payout_afn:pr(payout,'afn')};
}
