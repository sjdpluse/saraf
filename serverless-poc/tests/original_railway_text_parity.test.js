import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 originalCurrencyText,allCurrencyText,afghanDateTime,gregorianToJalali,
 goldPriceText,silverPriceText,cryptoPriceText,conversionText,currencyUnit,
} from '../tgcloud/lib/legacy_display.js';
import {ABOUT} from '../tgcloud/lib/legacy_about.js';
const file=p=>readFileSync(new URL('../tgcloud/'+p,import.meta.url),'utf8');
const usd={
 local:{market_label:'سرای شهزاده (کابل)',buy:69.1,sell:69.25},
 saraf_quote:{buy:68.95,sell:69.4,basis:'local',basis_rate:69.175},
 reference_rate:70.2,
};
test('original 3 distinct sources shown in original order with accurate local vs spread vs international numbers',()=>{
 const text=originalCurrencyText('usd',usd,{date:'۱ عقرب ۱۴۰۵  —  ۱۰:۱۰ ق.ظ'});
 const labels=['🏛 *نرخ سرای شهزاده (کابل)*','💱 *نرخ صرافی‌های محلی*',
  '🌍 *نرخ بازار آزاد جهانی*'];
 for(const label of labels)assert.ok(text.includes(label),label);
 assert.ok(text.indexOf(labels[0])<text.indexOf(labels[1]));
 assert.ok(text.indexOf(labels[1])<text.indexOf(labels[2]));
 assert.match(text,/خرید: 69\.10   \|   فروش: 69\.25/);
 assert.match(text,/خرید: 68\.95   \|   فروش: 69\.40/);
 assert.match(text,/70\.20 افغانی/);
 assert.match(text,/آخرین بروزرسانی امروز؛/);
 assert.match(text,/🇺🇸 \*\(1\) دالر امریکایی\*/);
 assert.match(text,/━━━━━━━━━━/);
});
test('1000-unit currencies scale every original source exactly and missing data never invents values',()=>{
 const text=originalCurrencyText('pkr',usd);
 assert.match(text,/\(1000\) کلدار پاکستانی/);
 assert.match(text,/خرید: 69,100\.00/);
 assert.match(text,/70,200\.00 افغانی/);
 const missing=originalCurrencyText('usd',{
  ...usd,local:null,reference_rate:null,
 });
 assert.doesNotMatch(missing,/🏛 \*نرخ/);
 assert.doesNotMatch(missing,/🌍 \*نرخ/);
 assert.match(missing,/💱 \*نرخ صرافی‌های محلی\*/);
});
test('all currencies shows original title and per-currency dividers within Telegram message limit',()=>{
 const all=Object.fromEntries(['usd','pkr','eur'].map(code=>[code,usd]));
 const text=allCurrencyText(all,'۱۰ عقرب ۱۴۰۵  —  ۸:۳۰ ب.ظ');
 assert.match(text,/💵 \*\(Saraf\) نرخ ارزهای خارجی در برابر پول افغانی امروز — صراف\*/);
 assert.match(text,/🇺🇸 \*\(1\) دالر امریکایی\*/);
 assert.match(text,/🇵🇰 \*\(1000\) کلدار پاکستانی\*/);
 assert.ok(text.length<4000);
});
test('Afghan date and clock follow original persian_date.py without browser Intl/URL APIs',()=>{
 assert.deepEqual(gregorianToJalali(2025,3,21),[1404,1,1]);
 assert.equal(afghanDateTime(new Date('2025-03-21T05:40:00Z')),'۱ حمل ۱۴۰۴  —  ۱۰:۱۰ ق.ظ');
 assert.equal(afghanDateTime(new Date('2025-03-20T08:00:00Z')),'۳۰ حوت ۱۴۰۳  —  ۱۲:۳۰ ب.ظ');
});
test('gold 24/22/21/18 and silver restore original ounce, grams, USD and methqal sections',()=>{
 const rows=[
  {karat:24,afnGram:6000.5,usdGram:81.23,afnMethqal:27648.2,usdMethqal:374.3},
  {karat:22,afnGram:5500.5,usdGram:74.46,afnMethqal:25346.3,usdMethqal:343.12},
 ];
 const all=goldPriceText(rows,2500,'all');
 assert.match(all,/🥇 \*نرخ لحظه‌یی طلا\*/);
 assert.match(all,/قیمت جهانی: \*2,500\.00 دالر\*/);
 assert.match(all,/عیار 24.*هر گرم/);
 assert.match(all,/عیار 22/);
 const selected=goldPriceText(rows,2500,'24');
 assert.match(selected,/🥇 \*طلای عیار 24\*/);
 assert.match(selected,/هر گرم: \*6,001 افغانی\*/);
 assert.match(selected,/هر مثقال: \*27,648 افغانی\*/);
 const silver=silverPriceText([
  {karat:24,afnGram:80.1,usdGram:1.0023,afnMethqal:369.1,usdMethqal:4.62},
 ],32.2);
 assert.match(silver,/اونس تروی/);
 assert.match(silver,/1\.0023\$/);
 assert.match(silver,/هر مثقال: \*369\.1 افغانی\*/);
});
test('crypto exchange displays original Afghan date, dividers and AFN equivalent; no fabricated conversion if USD/AFN unavailable',()=>{
 const result=cryptoPriceText({btc:100,shib:0.00002},70);
 assert.match(result,/🪙 \*نرخ لحظه‌یی رمزارزها — صراف\*/);
 assert.match(result,/\*بیت‌کوین \(BTC\)\*/);
 assert.match(result,/7,000\.00 افغانی/);
 assert.match(result,/0\.00002000\$/);
 assert.match(result,/0\.0014 افغانی/);
 const unavailable=cryptoPriceText({btc:100},null);
 assert.doesNotMatch(unavailable,/افغانی/);
});
test('About pages and converter preserve original full paragraphs, not abbreviated placeholders',()=>{
 assert.match(ABOUT.home,/تمرکز صراف روی تجربهٔ سریع/);
 assert.match(ABOUT.markets,/ارزهای خارجی/);
 assert.match(ABOUT.tools,/ماشین‌حساب نقره/);
 assert.match(ABOUT.usdt,/پیگیری وضعیت سفارش/);
 assert.match(ABOUT.security,/بررسی دستی سفارش‌های مالی/);
 assert.match(ABOUT.developer,/سجاد محمدی/);
 assert.match(ABOUT.disclaimer,/سلب مسئولیت/);
 assert.match(conversionText('usd','eur',100,90,0.9),/نرخ واحد: ۱/);
});
test('currency, metal, crypto and about callback paths enable Telegram Markdown formatting',()=>{
 const callback=file('handlers/callback_query.js'),message=file('handlers/message.js');
 assert.match(callback,/originalCurrencyText\(a,quotes\[a\]\),currencyQuote\(a\),true/);
 assert.match(callback,/allCurrencyText\(quotes\),undefined,true/);
 assert.match(callback,/goldPriceText\(rows,m\.price,a\),undefined,true/);
 assert.match(callback,/edit\(chat,id,ABOUT\[a\],aboutKeyboard\(a\),true\)/);
 assert.match(message,/silverPriceText\(rows,metal\.price\),silverCalcMode\(\),true/);
 assert.match(message,/cryptoPriceText\(prices,reference\.rates\.usd/);
 assert.match(message,/ABOUT\.home,aboutKeyboard\(\),true/);
});
test('compare keeps original explanatory old/current basis note and warning when source differs',()=>{
 const source=file('lib/legacy_compare.js');
 assert.match(source,/🕰 \*/);
 assert.match(source,/⏱ \*اکنون/);
 assert.match(source,/⚠️ _توجه:/);
 assert.match(source,/بازار واقعی صرافی‌های کابل/);
 assert.match(file('handlers/callback_query.js'),/edit\(chat,id,report,undefined,true\)/);
});
