// Read-only Telegram callback router for test bot, with safe untrusted input checks.
import { api } from 'sdk';
import { VALID_CODES, CURRENCIES, label, money, currencyKeyboard, GOLD_KARATS } from '../lib/currencies.js';
import { getReferenceRates } from '../lib/reference_rates.js';
import { getMetalPrice, metalBreakdown } from '../lib/metals.js';

const DIV = '━━━━━━━━━━━━';
function rateText(rates, codes) {
  return codes.filter(c => Number.isFinite(rates[c])).map(code =>
    `${label(code)}: ${money(rates[code], 4)} افغانی`).join('\n');
}
export default async function (query) {
  const data = String(query?.data ?? '');
  if (!Number.isSafeInteger(query?.message?.chat?.id)) return;
  if (!data.startsWith('ref:') && !data.startsWith('goldref:')) return;
  const chatId = query.message.chat.id;
  const callbackId = query.id;
  try {
    if (data.startsWith('ref:')) {
      const code = data.slice(4);
      if (code !== 'all' && !VALID_CODES.includes(code)) return;
      const { rates, source, fetchedAt } = await getReferenceRates();
      const codes = code === 'all' ? VALID_CODES : [code];
      await api.sendMessage({
        chat_id: chatId,
        text: `💵 نرخ مرجع جهانی ارزها\n${DIV}\n${rateText(rates, codes)}\n${DIV}\nمنبع: ${source}\nزمان دریافت: ${fetchedAt}\n⚠️ قیمت معامله صرافی نیست.`,
      });
    } else {
      const raw = data.slice(8);
      if (raw !== 'all' && !GOLD_KARATS.includes(Number(raw))) return;
      const [{ rates }, { price }] = await Promise.all([getReferenceRates(), getMetalPrice('XAU')]);
      const rows = metalBreakdown('XAU', price, rates.usd)
        .filter(r => raw === 'all' || r.karat === Number(raw));
      await api.sendMessage({
        chat_id: chatId,
        text: '🥇 طلای جهانی (مرجع)\n' + rows.map(r =>
          `عیار ${r.karat} | هر گرم: ${money(r.afnGram, 1)} افغانی | هر مثقال: ${money(r.afnMethqal, 1)} افغانی`).join('\n') +
          '\n⚠️ برای معامله معتبر نیست.',
      });
    }
  } catch (error) {
    console.warn('Saraf callback error', String(error));
    await api.sendMessage({ chat_id: chatId, text: '⚠️ نرخ فعلاً در دسترس نیست؛ دوباره امتحان کنید.' });
  } finally {
    if (callbackId) {
      try { await api.answerCallbackQuery({ callback_query_id: callbackId }); }
      catch (error) { console.warn('callback acknowledgement failed', String(error)); }
    }
  }
}
