// Original Saraf Telegram menus restored on Telegram Serverless.
// Original canonical Supabase remains the only financial ledger.
import { api } from 'sdk';
import { CURRENCIES, VALID_CODES, label, money, currencyKeyboard, mainKeyboard } from '../lib/currencies.js';
import { getReferenceRates, convertUsingAfnRates } from '../lib/reference_rates.js';
import { getMetalPrice, metalBreakdown } from '../lib/metals.js';
import { getCryptoPrices, cryptoLabel } from '../lib/cryptos.js';
import { getLocalMarketRates } from '../lib/local_market_service.js';
import { currencyList,goldList,silverCalcMode,compareTarget,converterFrom,originalBotMenu,aboutKeyboard,originalStablecoinMenu,originalMiniAppLink } from '../lib/legacy_menus.js';
import { handleOriginalCalcReply } from '../lib/legacy_calc.js';
import {handleOriginalAdminCommand} from '../lib/original_admin_entry.js';
const NOTIFICATION_URL='https://app8533795882.tgcloud.ai/?action=notifications';
const notificationsButton={inline_keyboard:[[{
  text:'🔔 مدیریت پیام‌های همگانی صراف',web_app:{url:NOTIFICATION_URL}
}]]};

const reply = (chatId, text, reply_markup) => api.sendMessage({ chat_id: chatId, text, ...(reply_markup ? { reply_markup } : {}) });
const welcome=(name='دوست عزیز')=>
  'سلام '+String(name||'دوست عزیز')+' 👋\n\n'+
  'به صراف خوش آمدید.\n'+
  'پلتفرم هوشمند بازار و خدمات مالی افغانستان.\n\n'+
  '💵 نرخ ارزها  |  🥇 طلا  |  🥈 نقره  |  🪙 رمزارزها\n'+
  '📊 مقایسه با گذشته  |  🔄 مبدل ارز  |  🪙 خرید و فروش USDT / USDC\n\n'+
  'از منوی زیر گزینهٔ مورد نظر خود را انتخاب کنید. 👇';
export const isMainMenuRequest=text=>{
  const s=String(text||'').trim();
  return /^(?:\/(?:start|menu|help|home|ping)(?:@[A-Za-z0-9_]+)?(?:\s.*)?|منو|منوی اصلی|خانه|بازگشت|🔙 بازگشت|🔙 منوی اصلی|🏠 منوی اصلی)$/iu.test(s);
};

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
      '👤 پروفایل اصلی صراف محفوظ است. برای مشاهده و ویرایش معلومات خود مینی‌اپ اصلی را باز کنید.',
      {inline_keyboard:[[{text:'👤 پروفایل و تایید هویت',web_app:{url:originalMiniAppLink()}}]]});
    case '📦 سفارش‌های من':
    case '/orders': return reply(chatId,
      '📦 سفارش‌های خرید و فروش شما در همان پایگاه دادهٔ اصلی صراف نگهداری می‌شوند.',
      {inline_keyboard:[[{text:'📦 مشاهده سفارش‌های من',web_app:{url:'https://app8533795882.tgcloud.ai/?action=orders'}}]]});
    case '💸 حواله‌های من':
    case '/remittances': return reply(chatId,
      '💸 سوابق حواله‌های شما در همان پایگاه دادهٔ اصلی صراف نگهداری می‌شوند.',
      {inline_keyboard:[[{text:'💸 مشاهده حواله‌های من',web_app:{url:'https://app8533795882.tgcloud.ai/?action=remittances'}}]]});
    case '💵 نرخ ارزها':
    case '/rates':
    case '/currency':
    case 'نرخ ارزها':
    case 'نرخ اسعار':
      return reply(chatId, 'کدام ارز مدنظر شماست؟ یا «نمایش همهٔ نرخ‌ها» را بزنید.', currencyList());
    case '🥇 نرخ طلا':
    case '/gold':
    case 'نرخ طلا':
      return reply(chatId, 'عیار مدنظر خود را انتخاب کنید، «نمایش همهٔ عیارها» را بزنید، یا از ماشین‌حساب خرید/فروش استفاده کنید.', goldList());
    case '🥈 نرخ نقره':
    case '/silver':
    case 'نرخ نقره': {
      const symbol = 'XAG';
      const [{ rates }, metal] = await Promise.all([getReferenceRates(), getMetalPrice(symbol)]);
      const rows = metalBreakdown(symbol, metal.price, rates.usd);
      return reply(chatId, goldText(rows, '🥈 نرخ لحظه‌یی نقره (خالص)') +
        '\n⚠️ صرفاً اطلاعات مرجع؛ نرخ قطعی معامله نیست.', silverCalcMode());
    }
    case '🪙 نرخ رمزارزها':
    case '/crypto': {
      const { prices, source } = await getCryptoPrices();
      return reply(chatId, '🪙 نرخ رمزارزها (USD) — منبع: ' + source + '\n' +
        Object.entries(prices).map(([symbol, price]) => `${cryptoLabel(symbol)} (${symbol.toUpperCase()}): $${price < 0.001 ? price.toFixed(8) : money(price, price < 1 ? 4 : 2)}`).join('\n'));
    }
    case '🔄 مبدل ارز جهانی':
    case '/converter':
      return reply(chatId,
      '🔄 مبدل ارز جهانی\n\nابتدا ارز مبدأ را انتخاب کنید:', converterFrom());
    case '📊 مقایسه با گذشته':
    case '/compare':
      return reply(chatId,
      '📊 چه چیزی را می‌خواهید با گذشته مقایسه کنید؟', compareTarget());
    case 'خرید و فروش | USDT/USDC':
    case '/usdt':
      return reply(chatId,
      '🪙 خرید و فروش USDT / USDC\nدارایی و نوع معامله را انتخاب کنید:',
      originalStablecoinMenu());
    case 'Saraf - JustMarkets': return reply(chatId,
      'Saraf - JustMarkets\\nراهنمای ثبت‌نام، وریفیکیشن و دیپازیت در مینی‌اپ اصلی صراف.',
      {inline_keyboard:[[{text:'🔗 باز کردن JustMarkets صراف',
        web_app:{url:originalMiniAppLink('justmarkets')}}]]});
    case 'ℹ️ درباره ربات':
    case '/about': return reply(chatId,
      '🏦 صراف\n\nیک تجربهٔ مالی هوشمند، ساده و ساخته‌شده برای افغانستان\n\nنرخ را ببین. محاسبه کن. با آگاهی تصمیم بگیر.',
      aboutKeyboard());
    default: {
      const m = /^\/convert(?:@[a-zA-Z0-9_]+)?\s+([a-zA-Z]{3})\s+([a-zA-Z]{3})\s+(\d+(?:\.\d+)?)$/i.exec(input);
      if (!m) return reply(chatId,
        '🏠 منوی اصلی صراف\nلطفاً یکی از گزینه‌های نرخ اسعار، طلا، نقره، رمزارز، مبدل یا خرید و فروش USDT/USDC را انتخاب کنید.',
        originalBotMenu());
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
  if (await handleOriginalAdminCommand(message)) return;
  if (await handleOriginalCalcReply(message)) return;
  // Always restore the ORIGINAL Saraf keyboard after WebApp use; never
  // leave customers stranded in an USDT-only menu.
  if (isMainMenuRequest(input)) {
    return reply(chatId,welcome(message.from?.first_name),originalBotMenu());
  }
  if (/^\/stop(?:@[A-Za-z0-9_]+)?(?:\s|$)/i.test(input)) {
    await reply(chatId,
      '🔕 مدیریت اشتراک پیام‌های همگانی از طریق مینی‌اپ صراف انجام می‌شود.',
      notificationsButton);
    return reply(chatId,'🏠 منوی اصلی صراف',originalBotMenu());
  }
  if (/^\/notifications(?:@[A-Za-z0-9_]+)?(?:\s|$)/i.test(input))
    return reply(chatId,
      '🔔 مدیریت پیام‌های همگانی در مینی‌اپ اصلی صراف:',notificationsButton);
  // Do not expose financial actions or ambiguous shadow records in the customer bot.
  try {
    await onReadOnlyMessage(chatId, input);
  } catch (error) {
    console.warn('Original Saraf menu handler failed', String(error));
    await reply(chatId, '⚠️ دریافت اطلاعات ممکن نشد. چند لحظه دیگر دوباره امتحان کنید.');
  }
}
