// Pure HTML parser for public sarafi.af local exchange-market price tables.
// Mirrors the extraction rules in services/local_market_service.py, without npm/DOM.
const MARKET = Object.freeze({
  'sarai-shahzada': 'sarai_shahzada',
  'khorasan-market': 'khorasan_market',
  'da-afg-bank': 'da_afg_bank',
});
export const MARKET_LABELS = Object.freeze({
  sarai_shahzada: 'سرای شهزاده (کابل)',
  khorasan_market: 'مارکیت خراسان (هرات)',
  da_afg_bank: 'د افغانستان بانک',
});

function normalizeDigits(value) {
  return String(value)
    .replace(/[۰-۹]/g, char => String(char.charCodeAt(0) - 1776))
    .replace(/[٠-٩]/g, char => String(char.charCodeAt(0) - 1632));
}
function plainText(html) {
  return normalizeDigits(String(html || '')
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;|&#160;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/\s+/g, ' ')).trim();
}
function parseNumeric(text) {
  const input = normalizeDigits(text).replace(/[,،\s]/g, '');
  const cleaned = input.replace(/[^0-9.]/g, '');
  const value = Number(cleaned);
  return Number.isFinite(value) && value > 0 ? value : null;
}
export function parseLocalMarketHtml(html) {
  if (typeof html !== 'string' || html.length > 2_000_000) {
    throw new Error('HTML بازار محلی نامعتبر است.');
  }
  const result = Object.fromEntries(Object.values(MARKET).map(key => [key, {}]));
  for (const [, rowHtml] of html.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr\s*>/gi)) {
    const links = [...rowHtml.matchAll(/<a\b([^>]*)>([\s\S]*?)<\/a\s*>/gi)];
    let code, market, unit = 1;
    for (const [, attrs, body] of links) {
      const hrefMatch = attrs.match(/href\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))/i);
      const href = hrefMatch?.[1] || hrefMatch?.[2] || hrefMatch?.[3] || '';
      const url = href.match(/\/exchange-rates\/(sarai-shahzada|khorasan-market|da-afg-bank)\/([a-z]{3})-AFN/i);
      if (!url) continue;
      market = MARKET[url[1].toLowerCase()];
      code = url[2].toLowerCase();
      if (/هزار/.test(plainText(body))) unit = 1000;
      break;
    }
    if (!market || !code || Object.hasOwn(result[market], code)) continue;
    const cells = [...rowHtml.matchAll(/<td\b[^>]*>([\s\S]*?)<\/td\s*>/gi)];
    if (cells.length < 3) continue;
    const buy = parseNumeric(plainText(cells[1][1]));
    const sell = parseNumeric(plainText(cells[2][1]));
    if (buy == null || sell == null) continue;
    result[market][code] = {
      buy: Math.round(buy / unit * 1e6) / 1e6,
      sell: Math.round(sell / unit * 1e6) / 1e6,
    };
  }
  return result;
}
