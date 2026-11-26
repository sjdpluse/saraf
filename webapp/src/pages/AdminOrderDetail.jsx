import {useEffect, useRef, useState} from 'react';
import {ArrowClockwise, ArrowRight, CheckCircle, FileArrowUp, Receipt} from '@phosphor-icons/react';
import {originalAdminCommand, uploadOriginalAdminCompletionProof} from '../lib/originalAdminBridge';
import {showConfirm} from '../lib/telegram';
import {amount, kabulTime, orderCode, riskLabels, statusLabels} from '../lib/adminOrders';

const methods = {in_person: 'حضوری', online: 'آنلاین', online_hesabpay: 'حساب‌پی', online_azizi: 'عزیزی بانک'};
const identities = {pending: 'در انتظار بررسی', verified: 'تأییدشده', restricted: 'محدود', trusted: 'معتمد', unverified: 'تأییدنشده'};
const deliveries = {sent: 'ارسال شد', failed: 'ناموفق', sending: 'در حال ارسال', uncertain: 'نیازمند بررسی'};
const outcomes = {'order.confirm': 'تأیید شد', 'order.reject': 'رد و لغو شد', 'order.complete': 'تکمیل شد'};

function Fields({title, rows}) {
  const values = rows.filter(([, value]) => value != null && value !== '');
  if (!values.length) return null;
  return <section className="desk-panel"><h3>{title}</h3><dl className="desk-fields">
    {values.map(([label, value]) => <div key={label}><dt>{label}</dt><dd dir="auto">{value}</dd></div>)}
  </dl></section>;
}

export default function AdminOrderDetail({id, onBack, onSuccess, setWorking}) {
  const [record, setRecord] = useState(null);
  const [readError, setReadError] = useState('');
  const [revision, setRevision] = useState(0);
  const [details, setDetails] = useState('');
  const [proof, setProof] = useState(null);
  const [activity, setActivity] = useState('');
  const [error, setError] = useState('');
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    originalAdminCommand('orders.detail', {order_id: id}).then(data => {
      if (!active) return;
      if (Number(data.order?.id) !== Number(id)) setReadError('جزئیات این سفارش در دسترس نیست.');
      else setRecord(data);
    }, err => {if (active) setReadError(err.message);});
    return () => {active = false;};
  }, [id, revision]);

  useEffect(() => {
    if (!proof) return;
    const timer = setTimeout(() => {
      setProof(null);
      setError('اعتبار مدرک پایان یافت. فایل را دوباره انتخاب کنید.');
    }, Math.max(0, proof.until - Date.now()));
    return () => clearTimeout(timer);
  }, [proof]);

  function reload() {
    setReadError(''); setError(''); setRecord(null); setNeedsRefresh(false);
    setRevision(value => value + 1);
  }
  function working(action) {
    lock.current = Boolean(action);
    setWorking(Boolean(action));
    setActivity(action);
  }
  async function upload(file) {
    if (!file || lock.current) return;
    working('upload'); setProof(null); setError('');
    try {
      const start = Date.now();
      const result = await uploadOriginalAdminCompletionProof(id, file);
      setProof({token: result.proof_token, name: file.name,
        until: start + Math.min(result.expires_in_seconds || 600, 600) * 1000});
    } catch (err) { setError(err.message); }
    finally { working(''); }
  }
  async function submit(action) {
    if (lock.current || needsRefresh) return;
    const order = record.order;
    const completing = action === 'order.complete';
    const text = details.trim();
    const prompt = {
      'order.confirm': 'پس از بررسی دریافت مبلغ یا رمزارز، سفارش زیر را تأیید می‌کنید؟',
      'order.reject': 'این سفارش رد و لغو شود؟',
      'order.complete': 'آیا مبلغ/رمزارز واقعاً به مشتری ارسال شده و مدرک این سفارش صحیح است؟',
    }[action];
    const summary = [orderCode(order), order.order_type === 'buy' ? 'خرید مشتری' : 'فروش مشتری',
      amount(order.usdt_amount) + ' ' + (order.asset || 'USDT'), amount(order.total_afn) + ' افغانی'].join(' · ');
    working(action); setError('');
    let submitted = false;
    try {
      if (!await showConfirm(prompt + '\n' + summary)) return;
      const input = {order_id: id};
      if (completing) {
        if ((text && text.length < 4) || text.length > 2000 || (!text && !(proof?.until > Date.now()))) {
          setError('جزئیات معتبر تراکنش یا مدرک دارای اعتبار لازم است.'); return;
        }
        input.completion_tx_details = text;
        if (proof?.until > Date.now()) input.proof_token = proof.token;
      }
      submitted = true;
      const {result} = await originalAdminCommand(action, input);
      if (Number(result?.order_id) !== Number(id)) throw new Error('پاسخ ثبت عملیات قابل تأیید نیست.');
      const notification = result.customer_notified === false ? ' ارسال پیام به مشتری ناموفق بود.' : '';
      onSuccess(orderCode(order) + ' ' + outcomes[action] + '.' + (result.duplicate ? ' این اقدام قبلاً ثبت شده بود.' : '') + notification);
    } catch (err) {
      setError(err.message); setNeedsRefresh(submitted);
    } finally { working(''); }
  }
  const order = record?.order;
  const profile = record?.profile;
  const buy = order?.order_type === 'buy';
  const method = order?.payment_method || order?.receive_method;
  const canComplete = details.trim().length >= 4 || (!details.trim() && proof?.until > Date.now());
  const blocked = Boolean(activity) || needsRefresh;
  const money = (value, unit) => value != null && value !== '' ? amount(value) + ' ' + unit : null;

  return <div className="desk-content" aria-label="جزئیات سفارش">
    <div className="desk-detail-nav">
      <button className="desk-button" disabled={Boolean(activity)} onClick={onBack}><ArrowRight/> بازگشت به صف</button>
      <button className="desk-button" disabled={Boolean(activity)} onClick={reload}><ArrowClockwise/> تازه‌سازی جزئیات</button>
    </div>
    {readError ? <p className="desk-feedback error" role="alert">{readError}</p> :
      !record ? <p className="desk-empty" role="status">در حال دریافت جزئیات سفارش…</p> : <>
      <section className="desk-ticket">
        <header><div><small>{buy ? 'سفارش خرید مشتری' : 'سفارش فروش مشتری'}</small>
          <h2><bdi>{orderCode(order)}</bdi></h2></div>
          <span className={'desk-status ' + order.status}>{statusLabels[order.status] || order.status}</span></header>
        <div className="desk-ticket-amounts"><div><small>مقدار سفارش</small>
          <strong><bdi>{amount(order.usdt_amount)} {order.asset || 'USDT'}</bdi></strong></div>
          <div><small>{buy ? 'مبلغ قابل پرداخت مشتری' : 'مبلغ قابل دریافت مشتری'}</small>
          <strong>{amount(order.total_afn)} <small>افغانی</small></strong></div></div>
      </section>
      <Fields title="مشتری" rows={[
        ['نام مشتری', [profile?.first_name, profile?.last_name].filter(Boolean).join(' ') || order.full_name],
        ['شناسهٔ تلگرام', order.chat_id], ['نام کاربری', order.username && '@' + order.username.replace(/^@/, '')],
        ['شمارهٔ تماس', profile?.phone || order.phone], ['احراز هویت', identities[profile?.kyc_status] || profile?.kyc_status],
        ['سطح ریسک', riskLabels[order.risk_level] || order.risk_level], ['دلیل ریسک', order.risk_reasons],
        ['امتیاز اعتماد', profile?.trust_score], ['معاملات موفق', profile?.successful_orders],
      ]}/>
      <Fields title={buy ? 'پرداخت مشتری و مقصد رمزارز' : 'انتقال مشتری و مقصد پرداخت'} rows={[
        ['دارایی', order.asset], ['شبکه', order.network], ['صرافی یا کیف پول', order.exchange_name],
        ['آدرس کیف پول مشتری', order.wallet_address], ['روش ' + (buy ? 'پرداخت' : 'دریافت'), methods[method] || method],
        ['معلومات دریافت وجه', order.bank_info], ['کد مراجعهٔ حضوری', order.in_person_code],
        ['مدرک تراکنش مشتری', record.tx_text], ['جزئیات تسویه', order.completion_tx_details],
      ]}/>
      {record.receipt_url ? <a className="desk-link" href={record.receipt_url} target="_blank" rel="noopener noreferrer"
        referrerPolicy="no-referrer"><Receipt/> مشاهدهٔ رسید مشتری</a> : (record.has_customer_proof || (record.has_customer_proof == null && (!buy || method === 'online'))) && !record.tx_text &&
        <p className="desk-feedback">برای بررسی رسید این سفارش، گزارش ربات مدیر را باز کنید.</p>}
      <Fields title="نرخ و تسویه‌حساب" rows={[
        ['نرخ هر دالر', money(order.usd_rate, 'افغانی')], ['مبلغ دالری سفارش', money(order.total_usd, 'دالر')],
        ['سود صراف', money(order.saraf_profit_afn, 'افغانی')], ['سهم تأمین‌کننده', money(order.supplier_profit_afn, 'افغانی')],
        ['مبلغ تسویه با تأمین‌کننده', money(order.supplier_payout_afn, 'افغانی')],
      ]}/>
      {(order.status === 'pending' || order.status === 'confirmed') && <section className="desk-panel desk-action-panel">
        <h3>{order.status === 'pending' ? 'تصمیم دربارهٔ سفارش' : 'ثبت تسویهٔ سفارش'}</h3>
        {order.status === 'pending' ? <p>{buy ? 'رسید پرداخت را با مبلغ واریزی مشتری تطبیق دهید.' :
          'دریافت رمزارز را در شبکه و به مقدار ثبت‌شده بررسی کنید.'}</p> : <>
          <label htmlFor="settlement-details">شناسه یا جزئیات تراکنش</label>
          <textarea id="settlement-details" dir="auto" rows={2} maxLength={2000} disabled={blocked}
            placeholder="Tx Hash یا شمارهٔ مرجع پرداخت" value={details} onChange={e => setDetails(e.target.value)}/>
          <label className="desk-upload"><FileArrowUp size={22}/>
            <span>{activity === 'upload' ? 'در حال ثبت فایل…' : proof ? proof.name : 'انتخاب تصویر یا PDF'}
              <small>{proof ? 'مدرک برای این سفارش ثبت شد' : 'به‌جای شناسه یا همراه آن، تا ۸ مگابایت'}</small></span>
            <input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" disabled={blocked}
              aria-label="مدرک تسویه" onChange={e => {
                const file = e.target.files?.[0]; e.target.value = ''; upload(file);
              }}/></label>
        </>}
        {error && <p role="alert" className="desk-feedback error">{error}</p>}
        {needsRefresh && <button className="desk-button" onClick={reload}>بررسی دوبارهٔ وضعیت سفارش</button>}
        <div className="desk-actions">{order.status === 'pending' ? <>
          <button className="primary" disabled={blocked} onClick={() => submit('order.confirm')}><CheckCircle/> تأیید سفارش</button>
          <button className="danger" disabled={blocked} onClick={() => submit('order.reject')}>رد سفارش</button></> :
          <button className="primary" disabled={blocked || !canComplete} onClick={() => submit('order.complete')}>
            <CheckCircle/> تکمیل با مدرک تراکنش</button>}</div>
      </section>}
      <section className="desk-panel"><h3>گزارش ارسال کارت دیجیتال مشتری و مدیر</h3>
        {record.card_delivery?.length ? <dl className="desk-fields">{record.card_delivery.map((row, index) =>
          <div key={index}><dt>{row.recipient === 'customer' ? 'کارت مشتری' : 'کارت مدیر'}</dt>
            <dd>{deliveries[row.state] || 'نامعلوم'} · {amount(row.attempt_count)} تلاش
              {row.sent_at && <small>{kabulTime(row.sent_at)} به وقت کابل</small>}</dd></div>)}</dl> :
          <p>برای این سفارش سابقهٔ ارسال کارت ثبت نشده است.</p>}
        {record.card_url && <a className="desk-link" href={record.card_url} target="_blank" rel="noopener noreferrer"
          referrerPolicy="no-referrer">مشاهدهٔ کارت سفارش</a>}
      </section>
      <Fields title="زمان‌های سفارش به وقت کابل" rows={[
        ['ثبت', kabulTime(order.created_at)], ['تأیید', kabulTime(order.confirmed_at)],
        ['تکمیل', kabulTime(order.completed_at)], ['لغو', kabulTime(order.cancelled_at)],
      ]}/>
    </>}
  </div>;
}
