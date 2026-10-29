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
import { SARAF_ORIGINAL_BOT_USERNAME } from "../lib/originalBot";

const ITEMS = [
  ["orders", "سفارش‌های من", "مشاهده و پیگیری سفارش‌های خرید و فروش", ClipboardText],
  ["remittances", "حواله‌های من", "مشاهده و پیگیری حواله‌های کریپتویی", PaperPlaneTilt],
  ["reviews", "نظرات کاربران", "مشاهده تجربه و امتیاز کاربران صراف", ChatCircleText],
  ["about", "چرا صراف؟", "آشنایی با خدمات و نحوه کار صراف", ShieldCheck],
  ["terms", "قوانین و شرایط استفاده", "مطالعه قوانین و شرایط استفاده از خدمات", FileText],
];

export default function Menu({ navigate, readOnly = false }) {
  return (
    <main className="app-shell menu-page-shell">
      <div className="header">
        <h1>منوی صراف</h1>
      </div>

      <section className="menu-page-list" aria-label="منوی صراف">
        {readOnly && <button className="menu-page-item" type="button" onClick={() => navigate("account")}>
          <span className="menu-page-item-copy"><strong>👤 پروفایل و احراز هویت</strong><small>ثبت معلومات پایه و ارسال اسناد از طریق ربات تلگرام</small></span>
          <CaretLeft size={17}/>
        </button>}
        {readOnly && <button className="menu-page-item" type="button" onClick={() => navigate("markets")}>
          <span className="menu-page-item-copy"><strong>💵 نرخ‌های بازار</strong><small>نمایش نرخ مرجع ارز، طلا، نقره و رمزارز</small></span>
          <CaretLeft size={17}/>
        </button>}
        {(readOnly ? ITEMS.filter(([page]) => ["orders", "remittances", "about", "terms", "reviews"].includes(page)) : ITEMS).map(([page, title, description, Icon]) => (
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

      {readOnly && <button className="menu-page-support" type="button"
        onClick={() => openTelegramChat(SARAF_ORIGINAL_BOT_USERNAME)}>
        <span className="menu-page-item-icon"><PaperPlaneTilt size={23} /></span>
        <span className="menu-page-item-copy">
          <strong>🤖 ربات اصلی صراف</strong>
          <small>@sarafiaf_bot — بازگشت به ربات اصلی تلگرام</small>
        </span>
        <CaretLeft size={17} />
      </button>}
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
