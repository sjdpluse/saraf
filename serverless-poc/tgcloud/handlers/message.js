// READ-ONLY pilot for a SEPARATE TEST BOT. Financial actions deliberately disabled.
import { api, db } from 'sdk';
import { sql } from 'sdk/db';
import { smokeCounters } from '../schema.js';
import { CURRENCIES, VALID_CODES, label, money, currencyKeyboard, mainKeyboard } from '../lib/currencies.js';
import { getReferenceRates, convertUsingAfnRates } from '../lib/reference_rates.js';
import { getMetalPrice, metalBreakdown } from '../lib/metals.js';
import { getCryptoPrices, cryptoLabel } from '../lib/cryptos.js';
import { getLocalMarketRates } from '../lib/local_market_service.js';
import { acceptMedia } from '../lib/native_media.js';
import { adminCommand } from '../lib/native_admin.js';
import { getProfile,hasBasicProfile } from '../lib/native_auth.js';
import { getOwnOrders } from '../lib/native_orders.js';
import { getOwnRemittances } from '../lib/native_remittances.js';

const reply = (chatId, text, reply_markup) => api.sendMessage({ chat_id: chatId, text, ...(reply_markup ? { reply_markup } : {}) });
export const currencyText = (rates, codes = VALID_CODES) =>
  codes.filter(c => rates[c]).map(c => `${label(c)}: ${money(rates[c], 4)} افغانی`).join('\n');
export const goldText = (rows, labelText) =>
  `${labelText}\n` + rows.map(r =>
    `عیار ${r.karat}: هر گرم ${money(r.afnGram, 1)} و هر مثقال ${money(r.afnMethqal, 1)} افغانی`).join('\n');

async function onReadOnlyMessage(chatId, input) {
  switch (input) {
    case '🏛 نرخ بازار کابل': {
      const result = await getLocalMarketRates();
      const prices = result.markets.sarai_shahzada || {};
      const lines = Object.entries(prices).map(([code, quote]) =>
        code.toUpperCase() + ': خرید ' + money(quote.buy, 4) + ' | فروش ' + money(quote.sell, 4) + ' افغانی');
      return reply(chatId, '🏛 نرخ سرای شهزاده (اطلاعات عمومی)\n' +
        (lines.join('\n') || 'نرخی دریافت نشد.') + '\n⚠️ نرخ قطعی معاملات Saraf نیست.');
    }

    case '👤 پروفایل':
    case '/profile': {
      const profile=await getProfile(chatId);
      return reply(chatId,'👤 معلومات پروفایل شما\n'+
        (hasBasicProfile(profile)?'نام: '+profile.firstName+' '+profile.lastName+'\nشماره: '+profile.phone:
        'معلومات پایه هنوز ثبت نشده است.')+
        '\nوضعیت هویت: '+(profile?.kycStatus || 'pending')+
        '\nبرای ثبت معلومات و مدارک، Mini App همین ربات را باز کنید.');
    }
    case '📦 سفارش‌های من':
    case '/orders': {
      const orders=await getOwnOrders(chatId);
      return reply(chatId,'📦 سفارش‌های شما (دیتابیس Serverless)\n'+
        (orders.map(o=>o.order_code+' | '+o.order_type+' '+o.usdt_amount+' '+o.asset+' | '+o.status).join('\n')||
        'در دیتابیس جدید سفارشی ثبت نشده است. سوابق Supabase هنوز انتقال داده نشده‌اند.'));
    }
    case '💸 حواله‌های من':
    case '/remittances': {
      const orders=await getOwnRemittances(chatId);
      return reply(chatId,'💸 حواله‌های شما (دیتابیس Serverless)\n'+
        (orders.map(o=>o.order_code+' | '+o.crypto_amount+' '+o.asset+' | '+o.status).join('\n')||
        'در دیتابیس جدید حواله‌ای ثبت نشده است. سوابق قدیمی هنوز انتقال داده نشده‌اند.'));
    }
    case '💵 نرخ ارزها': return reply(chatId, 'ارز مورد نظر را انتخاب کنید (نرخ جهانی؛ نه قیمت خرید/فروش صرافی).', currencyKeyboard());
    case '🥇 نرخ طلا':
    case '🥈 نرخ نقره': {
      const symbol = input.includes('طلا') ? 'XAU' : 'XAG';
      const [{ rates }, metal] = await Promise.all([getReferenceRates(), getMetalPrice(symbol)]);
      const rows = metalBreakdown(symbol, metal.price, rates.usd);
      return reply(chatId, goldText(rows, symbol === 'XAU' ? '🥇 نرخ مرجع جهانی طلا' : '🥈 نرخ مرجع جهانی نقره') +
        '\n⚠️ صرفاً اطلاعات مرجع؛ نرخ قطعی معامله نیست.');
    }
    case '🪙 نرخ رمزارزها': {
      const { prices, source } = await getCryptoPrices();
      return reply(chatId, '🪙 نرخ رمزارزها (USD) — منبع: ' + source + '\n' +
        Object.entries(prices).map(([symbol, price]) => `${cryptoLabel(symbol)} (${symbol.toUpperCase()}): $${price < 0.001 ? price.toFixed(8) : money(price, price < 1 ? 4 : 2)}`).join('\n'));
    }
    case '🔄 مبدل ارز جهانی': return reply(chatId,
      '🔄 برای تبدیل ارز بنویسید:\n/convert USD AFN 100\n/convert EUR USD 250\nنرخ صرفاً مرجع جهانی است.');
    case 'ℹ️ درباره ربات': return reply(chatId,
      '🏦 صراف | Saraf\nخدمات بازار، پروفایل، سفارش و حواله در مسیر انتقال به Telegram Serverless هستند. عملیات مالی تا انجام تطبیق اطلاعات و تأیید مدیر غیرفعال است.');
    default: {
      const m = /^\/convert(?:@[a-zA-Z0-9_]+)?\s+([a-zA-Z]{3})\s+([a-zA-Z]{3})\s+(\d+(?:\.\d+)?)$/i.exec(input);
      if (!m) return reply(chatId, 'لطفاً از منو استفاده کنید یا دستور /convert USD AFN 100 را امتحان نمایید.');
      const [, fromRaw, toRaw, amountRaw] = m;
      const from = fromRaw.toLowerCase(), to = toRaw.toLowerCase(), amount = Number(amountRaw);
      const { rates } = await getReferenceRates();
      const { result, unit } = convertUsingAfnRates(rates, from, to, amount);
      return reply(chatId, `🔄 ${money(amount)} ${from.toUpperCase()} = ${money(result, 4)} ${to.toUpperCase()}\nنرخ واحد: ${money(unit, 6)}\n⚠️ نرخ مرجع جهانی، نه نرخ معامله.`);
    }
  }
}

export default async function (message) {
  const chatId = message?.chat?.id;
  if (!Number.isSafeInteger(chatId) || message.chat?.type !== 'private') return;
  // Message ownership is the canonical Telegram identity for media and admin actions.
  if (!Number.isSafeInteger(message?.from?.id) || message.from.id !== chatId) return;
  if (await acceptMedia(message)) return;
  if (await adminCommand(message)) return;
  const input = String(message.text ?? '').trim();
  if (!input) return;
  if (/^\/(?:start|ping)(?:@[a-zA-Z0-9_]+)?(?:\s|$)/i.test(input)) {
    const [row] = await db.insert(smokeCounters)
      .values({ chatId, seen: 1 })
      .onConflictDoUpdate({
        target: smokeCounters.chatId,
        set: { seen: sql`${smokeCounters.seen} + 1` },
      }).returning().run();
    return reply(chatId, '🏦 به صراف خوش آمدید.\nبازدیدهای شما: ' + row.seen +
      '\n⚠️ معاملات، حواله‌ها و پرداخت‌ها در این نسخه غیرفعال اند.', mainKeyboard());
  }
  // Do not expose trading or KYC controls in the pilot.
  try {
    await onReadOnlyMessage(chatId, input);
  } catch (error) {
    console.warn('Saraf read-only pilot handler failed', String(error));
    await reply(chatId, '⚠️ دریافت اطلاعات ممکن نشد. چند لحظه دیگر دوباره امتحان کنید.');
  }
}
