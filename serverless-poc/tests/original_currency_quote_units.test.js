import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseLocalMarketHtml} from '../tgcloud/lib/local_market_parser.js';
import {currencyUnit,originalCurrencyText} from '../tgcloud/lib/legacy_display.js';
import {applyOriginalSpread,selectOriginalBasis,historicalOriginalBasis}
 from '../tgcloud/lib/legacy_rate_engine.js';
import {originalCurrencyCalculation} from '../tgcloud/lib/legacy_calculators.js';
import {parseOriginalLocalRates as marketHistoryParse,
  fetchOriginalCurrencyRates as marketHistoryReference}
 from '../../supabase/functions/saraf-original-market-snapshots/markets.mjs';
import {parseOriginalLocalRates as txParse,
  fetchOriginalCurrencyRates as txReference}
 from '../../supabase/functions/saraf-original-transactions/markets.mjs';
import {parseOriginalLocalRates as legacyParse}
 from '../../supabase/functions/saraf-legacy-snapshots/markets.mjs';

const row=(code,label,buy,sell,market='sarai-shahzada')=>
  '<tr><td><a href="/exchange-rates/'+market+'/'+code.toUpperCase()+'-AFN">'+
  code.toUpperCase()+'/AFN</a> '+label+'</td><td>'+buy+'</td><td>'+sell+'</td></tr>';
const html='<table>'+[
  row('usd','','66.20','66.25'),
  row('pkr','<sup>1K</sup> روپیه پاکستان','234','235'),
  row('inr','<sup>1K</sup> روپیه هند','709','709'),
  row('irr','<sup>1K</sup> تومان ایران','0.25','0.26'),
].join('')+'</table>';

test('Telegram and Supabase parsers normalize Sarafi.af 1K once, including sup outside <a>',()=>{
  for(const parse of [parseLocalMarketHtml,marketHistoryParse,txParse,legacyParse]){
    const rates=parse(html).sarai_shahzada;
    assert.equal(rates.usd.buy,66.2);
    assert.deepEqual(rates.pkr,{buy:.234,sell:.235});
    assert.deepEqual(rates.inr,{buy:.709,sell:.709});
    assert.deepEqual(rates.irr,{buy:.00025,sell:.00026});
  }
});

test('missing 1K label is rejected rather than producing 1000-fold prices',()=>{
  const invalid='<table>'+row('pkr','روپیه پاکستان','234','235')+
   row('irr','تومان ایران','0.25','0.26')+'</table>';
  for(const parse of [parseLocalMarketHtml,marketHistoryParse,txParse,legacyParse]){
    const quote=parse(invalid).sarai_shahzada;
    assert.ok(!('pkr' in quote));
    assert.ok(!('irr' in quote));
  }
});

test('PKR / INR show 1K, but toman displays 1M based on exact source normalization',()=>{
  assert.equal(currencyUnit('pkr'),1000);
  assert.equal(currencyUnit('inr'),1000);
  assert.equal(currencyUnit('irr'),1000000);
  const local=parseLocalMarketHtml(html);
  const irr=selectOriginalBasis('irr',{irr:0.000254},local);
  const text=originalCurrencyText('irr',irr,{date:'۱ عقرب ۱۴۰۵'});
  assert.match(text,/\(1,000,000\) تومان ایرانی/);
  assert.match(text,/خرید: 250\.00   \|   فروش: 260\.00/);
  assert.match(text,/خرید: 252\.45   \|   فروش: 257\.55/);
  assert.match(text,/254\.00 افغانی/);
  assert.equal(irr.saraf_quote.basis_rate,0.000255);
  assert.equal(irr.saraf_quote.buy,0.00025245);
  assert.equal(irr.saraf_quote.sell,0.00025755);
  for(const code of ['pkr','inr']){
    const q=selectOriginalBasis(code,{[code]:.2},local);
    const actual=originalCurrencyText(code,q);
    assert.match(actual,/\(1000\)/);
    assert.match(actual,/خرید: (234|709)\.00/);
  }
});

test('calculator uses unscaled per-toman rates and keeps its two-decimal AFN amount',()=>{
  const quote=selectOriginalBasis('irr',{irr:0.000254},parseLocalMarketHtml(html));
  const c=originalCurrencyCalculation(1_000_000,quote,'irr');
  assert.deepEqual(c.local,{sell_afn:250,buy_afn:260});
  assert.deepEqual(c.saraf,{sell_afn:252.45,buy_afn:257.55});
  assert.deepEqual(historicalOriginalBasis({buy:0.00025,sell:0.00026},null,'irr'),
    {rate:.000255,basis:'local'});
  assert.deepEqual(applyOriginalSpread(.000255,'irr'),
    {buy:.00025245,sell:.00025755,spread_percent:2});
});

test('international ISO IRR (rial) is changed into toman in both Serverless and Edge decoders',async()=>{
  // reference_rates.js has SDK-only import. Replace just its import bindings
  // in a data URL so the PURE decode functions can run under Node.
  const raw=readFileSync(new URL('../tgcloud/lib/reference_rates.js',import.meta.url),'utf8');
  const isolated=raw.replace("import { fetch } from 'sdk';",
    'const fetch = globalThis.fetch;')
    .replace("import { VALID_CODES, isPositive } from './currencies.js';",
      "const VALID_CODES=['usd','irr','pkr'];"+
      "const isPositive=n=>typeof n==='number'&&Number.isFinite(n)&&n>0;");
  const {decodeAfnBase,decodeUsdBase,convertUsingAfnRates}=
    await import('data:text/javascript;base64,'+Buffer.from(isolated).toString('base64'));
  const afn={afn:{usd:1/66,eur:1/73,pkr:1/.234,irr:1/.000025}};
  assert.equal(decodeAfnBase(afn).irr,.00025);
  const usd={rates:{AFN:66,IRR:2_640_000,PKR:66/.234}};
  assert.equal(decodeUsdBase(usd).irr,.00025);
  const r=convertUsingAfnRates(decodeAfnBase(afn),'irr','usd',1_000_000);
  assert.ok(Math.abs(r.result-(250/66))<1e-6);
  const mock=async()=>({ok:true,json:async()=>afn});
  for(const decoder of [marketHistoryReference,txReference]){
    const rates=await decoder(mock);
    assert.equal(rates.irr,.00025);
    assert.equal(rates.pkr,.234);
  }
});

test('read-only original release manifest already includes modified Telegram runtime modules',()=>{
  const manifest=readFileSync(new URL('../../scripts/prepare_saraf_original_release.mjs',
    import.meta.url),'utf8');
  for(const path of ['legacy_display.js','legacy_live_rates.js','local_market_parser.js',
    'legacy_rate_engine.js','legacy_calculators.js','legacy_calc.js',
    'legacy_compare.js','reference_rates.js']){
    assert.ok(manifest.includes("'lib/"+path+"'"),path+' not in release allowlist');
  }
});
