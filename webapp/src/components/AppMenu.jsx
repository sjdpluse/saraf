import { useEffect, useRef, useState } from "react";
import { List, X, FileText, ShieldCheck, Headset, ChatCircleText, ClipboardText, PaperPlaneTilt, CaretLeft } from "@phosphor-icons/react";
import { openTelegramChat } from "../lib/telegram";

const LINKS = [
  ["orders", "سفارش‌های من", ClipboardText],
  ["remittances", "حواله‌های من", PaperPlaneTilt],
  ["reviews", "نظرات کاربران", ChatCircleText],
  ["about", "چرا صراف؟", ShieldCheck],
  ["terms", "قوانین و شرایط استفاده", FileText],
];

export default function AppMenu({ navigate }) {
  const [open, setOpen] = useState(false);
  const dialog = useRef(null);
  const trigger = useRef(null);
  useEffect(() => {
    if (!open) return;
    const element = dialog.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element?.showModal();
    return () => {
      document.body.style.overflow = previousOverflow;
      element?.close();
      trigger.current?.focus();
    };
  }, [open]);
  function go(page) { setOpen(false); navigate(page); }
  return <>
    <button ref={trigger} className="icon-button" aria-label="باز کردن منو" aria-expanded={open} aria-controls="app-menu" onClick={() => setOpen(true)}><List size={24} /></button>
    <dialog ref={dialog} id="app-menu" className="app-menu" aria-labelledby="menu-title" onCancel={() => setOpen(false)} onClose={() => setOpen(false)} onClick={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
      <div className="menu-panel">
        <header><h2 id="menu-title">منوی صراف</h2><button className="icon-button" aria-label="بستن منو" onClick={() => setOpen(false)}><X size={21} /></button></header>
        <nav aria-label="منوی صراف">{LINKS.map(([page, label, Icon]) => <button key={page} onClick={() => go(page)}><Icon size={21} /><span>{label}</span><CaretLeft size={17} /></button>)}</nav>
        <button className="menu-support" onClick={() => { setOpen(false); openTelegramChat("SJDPLUS"); }}><Headset size={23} /><span>پشتیبانی صراف<small>گفتگو در تلگرام</small></span><CaretLeft size={17} /></button>
      </div>
    </dialog>
  </>;
}
