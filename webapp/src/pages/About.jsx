import { CaretRight, ShieldCheck, HandCoins, Headset, ClipboardText } from "@phosphor-icons/react";
import { openTelegramChat } from "../lib/telegram";

export default function About({ navigate }) {
  return <main className="app-shell">
    <header className="header"><button className="back-btn" aria-label="بازگشت" onClick={() => navigate("home")}><CaretRight size={20} /></button><h1>چرا صراف؟</h1><span className="header-spacer" /></header>
    <section className="card about-content">
      <h2>معامله با جزئیات روشن</h2>
      <p>خرید و فروش USDT و USDC و حواله از طریق کریپتو، با پرداخت و دریافت افغانی.</p>
      <div className="about-feature"><HandCoins size={24} /><div><h3>نرخ و کارمزد پیش از ثبت</h3><p>مبلغ نهایی را بررسی کنید و سپس سفارش را تایید کنید.</p></div></div>
      <div className="about-feature"><ShieldCheck size={24} /><div><h3>بررسی سفارش</h3><p>تیم صراف سفارش‌های خرید و فروش را پیش از تکمیل بررسی می‌کند.</p></div></div>
      <div className="about-feature"><ClipboardText size={24} /><div><h3>پیگیری در یک جای مشخص</h3><p>خرید و فروش‌ها در «سفارش‌های من» و حواله‌ها در «حواله‌های من» در دسترس‌اند.</p></div></div>
      <button className="btn btn-outline" onClick={() => openTelegramChat("SJDPLUS")}><Headset size={20} /> گفتگو با پشتیبانی</button>
    </section>
  </main>;
}
