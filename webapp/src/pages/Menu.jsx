import {useEffect,useState} from "react";
import {originalAdminCommand} from "../lib/originalAdminBridge";
import {
  CaretLeft,
  ChatCircleText,
  ClipboardText,
  FileText,
  Headset,
  PaperPlaneTilt,
  ShieldCheck,
  ShieldStar,
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
  const [adminVisible,setAdminVisible]=useState(false);
  useEffect(()=>{
    // Original keyboards.main_menu only exposed admin actions to administrators.
    // Never rely on Telegram userInfo in the browser: this Edge call checks
    // signed original Telegram initData and the private admin allowlist.
    let mounted=true;
    originalAdminCommand('access')
      .then(result=>{if(mounted&&result?.is_admin===true)setAdminVisible(true);})
      .catch(()=>{if(mounted)setAdminVisible(false);});
    return ()=>{mounted=false;};
  },[]);
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
        {adminVisible&&<button className="menu-page-item" onClick={()=>navigate('admin')}>
          <span className="menu-page-item-icon"><ShieldStar size={22}/></span>
          <span className="menu-page-item-copy">
            <strong>🔐 مدیریت صراف</strong>
            <small>سفارش‌ها، احراز هویت، نرخ‌ها، نشر پست فیسبوک و اینستاگرام</small>
          </span>
          <CaretLeft size={17}/>
        </button>}
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
