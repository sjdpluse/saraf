import {
  CaretLeft,
  ChatCircleText,
  ClipboardText,
  FileText,
  Headset,
  PaperPlaneTilt,
  ShieldCheck,
} from "@phosphor-icons/react";
import { openTelegramChat } from "../lib/telegram";

const ITEMS = [
  ["orders", "سفارش‌های من", "مشاهده و پیگیری سفارش‌های خرید و فروش", ClipboardText],
  ["remittances", "حواله‌های من", "مشاهده و پیگیری حواله‌های کریپتویی", PaperPlaneTilt],
  ["reviews", "نظرات کاربران", "مشاهده تجربه و امتیاز کاربران صراف", ChatCircleText],
  ["about", "چرا صراف؟", "آشنایی با خدمات و نحوه کار صراف", ShieldCheck],
  ["terms", "قوانین و شرایط استفاده", "مطالعه قوانین و شرایط استفاده از خدمات", FileText],
];

export default function Menu({ navigate }) {
  return (
    <main className="app-shell menu-page-shell">
      <div className="header">
        <h1>منوی صراف</h1>
      </div>

      <section className="menu-page-list" aria-label="منوی صراف">
        {ITEMS.map(([page, title, description, Icon]) => (
          <button key={page} className="menu-page-item" onClick={() => navigate(page)}>
            <span className="menu-page-item-icon"><Icon size={22} /></span>
            <span className="menu-page-item-copy">
              <strong>{title}</strong>
              <small>{description}</small>
            </span>
            <CaretLeft size={17} />
          </button>
        ))}
      </section>

      <button className="menu-page-support" onClick={() => openTelegramChat("SJDPLUS")}>
        <span className="menu-page-item-icon"><Headset size={23} /></span>
        <span className="menu-page-item-copy">
          <strong>پشتیبانی صراف</strong>
          <small>گفتگو مستقیم با پشتیبانی در تلگرام</small>
        </span>
        <CaretLeft size={17} />
      </button>
    </main>
  );
}
