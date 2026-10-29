// Saraf read-only Telegram-native bot. The existing Supabase database is the
// canonical financial store; do not read shadow Telegram SQLite order tables.
import { api } from 'sdk';
import { CURRENCIES, VALID_CODES, label, money, currencyKeyboard, mainKeyboard } from '../lib/currencies.js';
import { getReferenceRates, convertUsingAfnRates } from '../lib/reference_rates.js';
import { getMetalPrice, metalBreakdown } from '../lib/metals.js';
import { getCryptoPrices, cryptoLabel } from '../lib/cryptos.js';
import { getLocalMarketRates } from '../lib/local_market_service.js';
import { currencyList,goldList,silverCalcMode,compareTarget,converterFrom,originalBotMenu,aboutKeyboard } from '../lib/legacy_menus.js';
import { handleOriginalCalcReply } from '../lib/legacy_calc.js';

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
    case '/profile': return reply(chatId,
      '👤 معلومات حساب اصلی صراف در Supabase نگهداری می‌شود.\\n'+
      'برای مشاهده اطلاعات واقعی، Mini App همین ربات را باز کنید.\\n'+
      '⚠️ حساب آزمایشی دیتابیس جداگانه نیست.');
    case '📦 سفارش‌های من':
    case '/orders': return reply(chatId,
      '📦 سفارش‌های قبلی شما در Supabase حفظ شده‌اند.\\n'+
      'نمایش امن تاریخچه از طریق Mini App پس از فعال‌شدن اتصال Supabase در دسترس خواهد بود.');
    case '💸 حواله‌های من':
    case '/remittances': return reply(chatId,
      '💸 حواله‌های قبلی شما در Supabase حفظ شده‌اند.\\n'+
      'نمایش امن سوابق از طریق Mini App پس از فعال‌شدن اتصال Supabase در دسترس خواهد بود.');
    case '💵 نرخ ارزها': return reply(chatId, 'کدام ارز مدنظر شماست؟ یا «نمایش همهٔ نرخ‌ها» را بزنید.', currencyList());
    case '🥇 نرخ طلا':
      return reply(chatId, 'عیار مدنظر خود را انتخاب کنید، «نمایش همهٔ عیارها» را بزنید، یا از ماشین‌حساب خرید/فروش استفاده کنید.', goldList());
    case '🥈 نرخ نقره': {
      const symbol = 'XAG';
      const [{ rates }, metal] = await Promise.all([getReferenceRates(), getMetalPrice(symbol)]);
      const rows = metalBreakdown(symbol, metal.price, rates.usd);
      return reply(chatId, goldText(rows, '🥈 نرخ لحظه‌یی نقره (خالص)') +
        '\n⚠️ صرفاً اطلاعات مرجع؛ نرخ قطعی معامله نیست.', silverCalcMode());
    }
    case '🪙 نرخ رمزارزها': {
      const { prices, source } = await getCryptoPrices();
      return reply(chatId, '🪙 نرخ رمزارزها (USD) — منبع: ' + source + '\n' +
        Object.entries(prices).map(([symbol, price]) => `${cryptoLabel(symbol)} (${symbol.toUpperCase()}): $${price < 0.001 ? price.toFixed(8) : money(price, price < 1 ? 4 : 2)}`).join('\n'));
    }
    case '🔄 مبدل ارز جهانی': return reply(chatId,
      '🔄 مبدل ارز جهانی\n\nابتدا ارز مبدأ را انتخاب کنید:', converterFrom());
    case '📊 مقایسه با گذشته': return reply(chatId,
      '📊 چه چیزی را می‌خواهید با گذشته مقایسه کنید؟', compareTarget());
    case 'خرید و فروش | USDT/USDC': return reply(chatId,
      '🪙 خرید و فروش USDT / USDC\nنسخهٔ اصلی اپلیکیشن و API سفارش‌ها هنوز کامل منتقل نشده است؛ فعلاً سفارشی ثبت نمی‌شود.');
    case 'Saraf - JustMarkets': return reply(chatId,
      'Saraf - JustMarkets\nاین بخش همان Mini App اصلی است و بعد از انتقال کامل در دسترس خواهد بود.');
    case 'ℹ️ درباره ربات':
    case '/about': return reply(chatId,
      '🏦 صراف\n\nیک تجربهٔ مالی هوشمند، ساده و ساخته‌شده برای افغانستان\n\nنرخ را ببین. محاسبه کن. با آگاهی تصمیم بگیر.',
      aboutKeyboard());
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
  if (message?.photo || message?.document) {
    return reply(chatId,
      '⚠️ دریافت اسناد هویتی و رسیدهای مالی فعلاً فعال نیست. لطفاً مدارک شخصی یا رسیدها را ارسال نکنید.');
  }
  const input = String(message.text ?? '').trim();
  if (!input) return;
  if (await handleOriginalCalcReply(message)) return;
  if (/^\/(?:stop)(?:@[a-zA-Z0-9_]+)?(?:\s|$)/i.test(input)) return reply(chatId,'تنظیم دریافت پیام‌های همگانی پس از انتقال سرویس اصلی Supabase در دسترس خواهد بود.');
  if (/^\/(?:start|ping)(?:@[a-zA-Z0-9_]+)?(?:\s|$)/i.test(input)) {
    return reply(chatId,'سلام '+String(message.from?.first_name||'دوست عزیز')+' 👋\n\n'+
      'به صراف خوش آمدید.\nپلتفرم هوشمند بازار و خدمات مالی افغانستان.\n\n'+
      'از منوی زیر گزینهٔ مورد نظر خود را انتخاب کنید. 👇',originalBotMenu());
  }
  // Do not expose financial actions or ambiguous shadow records in the customer bot.
  try {
    await onReadOnlyMessage(chatId, input);
  } catch (error) {
    console.warn('Saraf read-only pilot handler failed', String(error));
    await reply(chatId, '⚠️ دریافت اطلاعات ممکن نشد. چند لحظه دیگر دوباره امتحان کنید.');
  }
}
