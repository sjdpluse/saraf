// Part of the ORIGINAL Saraf React Mini App. Runs in Telegram native serverless mode.
// Informational markets only: never show these as executable USDT/USDC quotes.
import { useEffect, useState } from 'react';
import { CaretRight, ArrowClockwise } from '@phosphor-icons/react';
import { getMarket } from '../telegram-pilot/market';
import './Markets.css';

const tabs = [
  ['currencies', '💵 ارزها'], ['gold', '🥇 طلا'],
  ['silver', '🥈 نقره'], ['crypto', '🪙 رمزارز'], ['local', '🏛 کابل'],
];
const format = (value, digits = 2) => Number(value).toLocaleString('en-US', {
  minimumFractionDigits: digits, maximumFractionDigits: digits,
});
function displayRow(kind, row) {
  if (kind === 'local') return [
    row.marketLabel + ' – ' + row.code,
    'خرید: ' + format(row.buy, 4) + ' | فروش: ' + format(row.sell, 4) + ' افغانی',
  ];
  if (kind === 'currencies') return [
    `${row.flag} ${row.name}`, `${format(row.afnPerUnit, 4)} افغانی`,
  ];
  if (kind === 'gold' || kind === 'silver') return [
    kind === 'gold' ? `عیار ${row.karat}` : 'نقره خالص',
    `${format(row.afnGram, 1)} افغانی / گرم`,
  ];
  const digits = Number(row.usd) < 0.001 ? 8 : 4;
  return [row.code, `$${format(row.usd, digits)}`];
}

export default function Markets({ navigate }) {
  const [kind, setKind] = useState('currencies');
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState({ loading: true, error: '', data: null });

  useEffect(() => {
    let active = true;
    setState({ loading: true, error: '', data: null });
    getMarket(kind).then(data => {
      if (active) setState({ loading: false, error: '', data });
    }).catch(error => {
      if (active) setState({ loading: false, error: error.message, data: null });
    });
    return () => { active = false; };
  }, [kind, attempt]);

  return <main className="app-shell">
    <div className="header">
      <button type="button" className="back-btn" onClick={() => navigate('home')} aria-label="بازگشت">
        <CaretRight size={20}/>
      </button>
      <h1>نرخ‌های بازار</h1><span className="header-spacer"/>
    </div>
    <div className="pilot-market">
      <div className="pilot-heading">
        <div><small>اطلاعات بین‌المللی، بدون نرخ معامله</small><h2>نرخ‌های مرجع</h2></div>
        <button type="button" className="pilot-refresh" disabled={state.loading}
          onClick={() => setAttempt(v => v + 1)} aria-label="بروزرسانی نرخ‌ها">
          <ArrowClockwise size={20}/>
        </button>
      </div>
      <nav className="pilot-tabs" aria-label="انتخاب بازار">
        {tabs.map(([key, name]) =>
          <button type="button" key={key} className={kind === key ? 'selected' : ''}
            aria-pressed={kind === key} onClick={() => setKind(key)}>{name}</button>)}
      </nav>
      {state.loading && <p className="pilot-info" role="status">در حال دریافت نرخ‌ها...</p>}
      {state.error && <p className="pilot-alert pilot-alert-error" role="alert">{state.error}</p>}
      <div className="pilot-items">
        {(state.data?.items || []).map(row => {
          const [name, price] = displayRow(kind, row);
          return <div className="pilot-market-card" key={row.code || row.karat}>
            <span className="pilot-market-copy"><strong>{name}</strong></span>
            <span className="pilot-market-value" dir="ltr">{price}</span>
          </div>;
        })}
      </div>
      {state.data && <p className="pilot-source">
        منبع: {state.data.source} · بروزرسانی: {state.data.fetchedAt || 'نامشخص'}
      </p>}
      <p className="pilot-source">⚠️ نرخ‌ها برای اطلاع‌رسانی است؛ پیشنهاد قطعی خرید یا فروش نیستند.</p>
    </div>
  </main>;
}
