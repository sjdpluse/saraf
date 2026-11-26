import {useEffect, useState} from 'react';
import {
  ArrowClockwise, ArrowDownLeft, ArrowUpRight, CalendarBlank, CaretLeft,
  CaretRight, CheckCircle, Clock, CurrencyCircleDollar, MagnifyingGlass, Tray,
} from '@phosphor-icons/react';
import {originalAdminCommand} from '../lib/originalAdminBridge';
import AdminOrderDetail from './AdminOrderDetail';
import {amount, orderCode, orderNumber, kabulTime, statusLabels, riskLabels} from '../lib/adminOrders';

const queues = {pending: 'در انتظار بررسی', confirmed: 'آمادهٔ تسویه', recent: 'آخرین سفارش‌ها'};
const sides = {all: 'همه', buy: 'خرید مشتری', sell: 'فروش مشتری'};

function useAdminRead(action, side, cursor, revision) {
  const key = [action, side, cursor, revision].join('/');
  const [state, setState] = useState(null);
  useEffect(() => {
    if (!action) return;
    let active = true;
    const input = action === 'dashboard' ? {} : {view: 'desk', side, after: cursor};
    originalAdminCommand(action, input).then(
      data => { if (active) setState({key, data}); },
      error => { if (active) setState({key, error: error.message}); },
    );
    return () => { active = false; };
  }, [key, action, side, cursor]);
  return state?.key === key ? state : {};
}

function OrderRow({order, openOrder}) {
  const buy = order.order_type === 'buy';
  const Icon = buy ? ArrowDownLeft : ArrowUpRight;
  return <button type="button" className="desk-order-row" onClick={() => openOrder(order.id)}>
    <span className={'desk-direction ' + (buy ? 'buy' : 'sell')}><Icon size={20}/></span>
    <span className="desk-order-label">
      <span><bdi className="desk-code">{orderCode(order)}</bdi></span>
      <small>{sides[order.order_type] || 'سفارش'}{order.network && <> · <bdi>{order.network}</bdi></>}</small>
      {order.risk_level === 'high' && <small className="desk-risk">{riskLabels.high}</small>}
    </span>
    <span className="desk-order-value">
      <strong><bdi>{amount(order.usdt_amount)} {order.asset || 'USDT'}</bdi></strong>
      <small>{amount(order.total_afn)} افغانی</small>
    </span>
    <CaretLeft size={16} className="desk-chevron"/>
    <span className="desk-order-meta">
      <span className={'desk-status ' + order.status}>{statusLabels[order.status] || order.status}</span>
      <time dateTime={order.created_at}>{kabulTime(order.created_at)}</time>
    </span>
  </button>;
}

export default function AdminOrderDesk({initialQueue, orderId, openOrder, setWorking}) {
  const [queue, setQueue] = useState(initialQueue);
  const [side, setSide] = useState('all');
  const [pages, setPages] = useState([0]);
  const [query, setQuery] = useState('');
  const [searchError, setSearchError] = useState('');
  const [notice, setNotice] = useState('');
  const [revision, setRevision] = useState(0);
  const summary = useAdminRead(orderId ? null : 'dashboard', 'all', 0, revision);
  const page = useAdminRead(!orderId && queue !== 'recent' ? 'orders.' + queue : null,
    side, pages[pages.length - 1], revision);
  const source = queue === 'recent' ? summary : page;
  const rows = queue === 'recent' ? source.data?.recent_orders : source.data?.orders;
  const visible = (rows || []).filter(row => side === 'all' || row.order_type === side);
  const next = page.data?.next_cursor;
  const kpis = [
    ['در انتظار بررسی', 'pending_orders', Clock, 'pending'],
    ['آمادهٔ تسویه', 'confirmed_orders', CurrencyCircleDollar, 'confirmed'],
    ['ثبت در ۲۴ ساعت', 'new_orders_24h', CalendarBlank],
  ];

  function refresh() {
    setPages([0]);
    setRevision(value => value + 1);
  }
  function chooseQueue(value) {
    setQueue(value);
    setPages([0]);
  }
  function search(event) {
    event.preventDefault();
    const id = orderNumber(query);
    if (!id) { setSearchError('شماره یا کد کامل سفارش را وارد کنید.'); return; }
    setSearchError('');
    setNotice('');
    openOrder(id);
  }
  if (orderId) return <AdminOrderDetail key={orderId} id={orderId} setWorking={setWorking}
    onBack={() => openOrder(null)} onSuccess={message => {
      setNotice(message);
      refresh();
      openOrder(null);
    }}/>;

  return <div className="desk-content">
    {notice && <p role="status" className="desk-feedback success"><CheckCircle size={20}/>{notice}</p>}
    <section className="desk-summary" aria-label="نمای کلی سفارش‌ها">
      <div className="desk-section-heading"><h2>نمای کلی سفارش‌ها</h2>
        <button type="button" className="desk-refresh" onClick={refresh}><ArrowClockwise/> تازه‌سازی</button>
      </div>
      <div className="desk-metrics">{kpis.map(([label, key, Icon, target]) => {
        const content = <><Icon size={20}/><strong>{amount(summary.data?.[key])}</strong><span>{label}</span></>;
        return target ? <button key={key} type="button" onClick={() => chooseQueue(target)}>{content}</button>
          : <div key={key}>{content}</div>;
      })}</div>
      {summary.error && queue !== 'recent' && <p role="alert">{summary.error}</p>}
      {summary.data && <details className="desk-more"><summary>آمار بیشتر</summary>
        <dl>{[['کاربران فعال', 'active_users'], ['سفارش‌های تکمیل‌شده', 'completed_orders'],
          ['اسناد در انتظار بررسی', 'pending_kyc'], ['حواله‌های در جریان', 'pending_remittances']]
          .map(([label, key]) => <div key={key}><dt>{label}</dt><dd>{amount(summary.data[key])}</dd></div>)}</dl>
      </details>}
    </section>
    <section className="desk-panel">
      <div className="desk-section-heading"><h2>میز سفارش‌ها</h2><Tray size={23}/></div>
      <form className="desk-search" onSubmit={search}>
        <MagnifyingGlass size={19}/><input type="search" dir="auto" aria-label="شماره یا کد سفارش"
          placeholder="شماره یا کد سفارش" value={query}
          onChange={event => {setQuery(event.target.value); setSearchError('');}}/>
        <button type="submit" disabled={!query.trim()}>جستجو</button>
      </form>
      {searchError && <p role="alert" className="desk-feedback error">{searchError}</p>}
      <div className="desk-queue-tabs" aria-label="صف سفارش">{Object.entries(queues).map(([key, label]) =>
        <button key={key} type="button" aria-pressed={queue === key}
          onClick={() => chooseQueue(key)}>{label}</button>)}</div>
      <div className="desk-filters">
        <div aria-label="نوع سفارش">{Object.entries(sides).map(([key, label]) =>
          <button key={key} type="button" aria-pressed={side === key}
            onClick={() => {setSide(key); setPages([0]);}}>{label}</button>)}</div>
        <small>{queue === 'recent' ? 'تا ۸ سفارش اخیر' : 'قدیمی‌ترین نخست'}</small>
      </div>
      {source.error ? <div className="desk-empty" role="alert"><p>{source.error}</p>
        <button className="desk-button" onClick={refresh}>تلاش دوباره</button></div> :
        !source.data ? <p className="desk-empty" role="status">در حال دریافت سفارش‌ها…</p> :
        <>
          {queue !== 'recent' && rows?.length === 20 && !('next_cursor' in source.data) &&
            <small>فیلتر روی ۲۰ سفارش نخست اعمال می‌شود. برای سفارش‌های دیگر، کد سفارش را جستجو کنید.</small>}
          {visible.length ? <div className="desk-rows">{visible.map(order =>
            <OrderRow key={order.id} order={order} openOrder={id => {setNotice(''); openOrder(id);}}/>)}</div> :
            <div className="desk-empty"><Tray size={32}/><p>سفارشی در این فهرست پیدا نشد.</p></div>}
          {queue !== 'recent' && (pages.length > 1 || next) && <div className="desk-pagination">
            <button disabled={pages.length === 1} onClick={() => setPages(pages.slice(0, -1))}><CaretRight/> قبلی</button>
            <small>صفحهٔ {amount(pages.length)}</small>
            <button disabled={!next} onClick={() => setPages([...pages, next])}>بعدی <CaretLeft/></button>
          </div>}
        </>}
    </section>
  </div>;
}
