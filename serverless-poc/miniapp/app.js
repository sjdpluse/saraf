// Read-only Saraf Mini App pilot. No browser-side financial state and no private credentials.
(() => {
  'use strict';

  const tg = window.Telegram?.WebApp;
  const serverless = tg?.Serverless;
  const connection = document.getElementById('connection');
  const status = document.getElementById('status');
  const meta = document.getElementById('meta');
  const cards = document.getElementById('cards');
  const title = document.getElementById('result-title');
  const buttons = Array.from(document.querySelectorAll('[data-kind]'));
  const titles = {
    currencies: '💵 نرخ جهانی ارزها',
    gold: '🥇 نرخ جهانی طلا',
    silver: '🥈 نرخ جهانی نقره',
    crypto: '🪙 رمزارزها (USD)',
  };
  let current = 'currencies';
  let requestSeq = 0;

  const number = (n, digits = 2) => Number(n).toLocaleString('en-US', {
    maximumFractionDigits: digits,
  });

  function showStatus(message) {
    status.textContent = message;
  }
  function addCard(name, value) {
    const el = document.createElement('div');
    el.className = 'card';
    const label = document.createElement('span');
    label.className = 'name';
    label.textContent = name;
    const price = document.createElement('span');
    price.className = 'value';
    price.textContent = value;
    el.append(label, price);
    cards.append(el);
  }

  function render(data) {
    cards.replaceChildren();
    const items = Array.isArray(data?.items) ? data.items : [];
    for (const item of items) {
      if (data.kind === 'currencies') {
        addCard(`${item.flag} ${item.name}`,
          `${number(item.afnPerUnit, 4)} AFN`);
      } else if (data.kind === 'gold' || data.kind === 'silver') {
        addCard(data.kind === 'gold' ? `عیار ${item.karat}` : 'نقره خالص',
          `${number(item.afnGram, 1)} AFN / g`);
      } else if (data.kind === 'crypto') {
        addCard(item.code, `$${number(item.usd, item.usd < 0.001 ? 8 : 4)}`);
      }
    }
    showStatus(items.length ? `${items.length} نرخ دریافت شد.` : 'نرخی از منبع دریافت نشد.');
    meta.textContent = `منبع: ${data.source || 'نامشخص'} • زمان دریافت: ${data.fetchedAt || 'نامشخص'}`;
  }

  function load(kind) {
    if (!titles[kind]) return;
    current = kind;
    buttons.forEach(button => button.classList.toggle('active', button.dataset.kind === kind));
    title.textContent = titles[kind];
    cards.replaceChildren();
    meta.textContent = '';
    if (!serverless || typeof serverless.call !== 'function' || !tg.initData) {
      showStatus('این برنامه باید از داخل منوی Mini App ربات آزمایشی تلگرام باز شود.');
      return;
    }
    showStatus('در حال دریافت معلومات از Telegram Serverless...');
    const seq = ++requestSeq;
    serverless.call('getReadOnlyMarket', { kind }, (err, data) => {
      if (seq !== requestSeq) return;
      if (err) {
        showStatus('❌ دریافت نرخ ناموفق بود. لطفاً دوباره امتحان کنید.');
        console.warn('Mini App Serverless request failed', err.type || 'unknown');
        return;
      }
      if (!data || data.kind !== kind || data.isReferenceOnly !== true) {
        showStatus('❌ پاسخ سرور معتبر نیست.');
        return;
      }
      render(data);
    });
  }

  if (tg && tg.initData && serverless && typeof serverless.call === 'function') {
    tg.ready();
    tg.expand();
    connection.textContent = '✅ اتصال به Telegram Mini App برقرار است.';
  } else {
    connection.textContent = '⚠️ اتصال تأیید نشد: Mini App را از منوی ربات آزمایشی باز کنید.';
    connection.classList.add('error');
  }
  buttons.forEach(button => button.addEventListener('click', () => load(button.dataset.kind)));
  document.getElementById('refresh').addEventListener('click', () => load(current));
  load(current);
})();
