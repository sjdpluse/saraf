import { Camera, CheckCircle, IdentificationCard, Scan } from "@phosphor-icons/react";
import { JMHeader, JMNotice, JMPage, JMSectionTitle, JMStep } from "../components/JustMarketsUI";

const CHECKS = [
  "نام، تاریخ تولد و سایر معلومات ثبت‌نام با سند هویتی مطابقت داشته باشد.",
  "سند معتبر و منقضی‌نشده باشد، هرگاه JustMarkets چنین شرطی را نمایش دهد.",
  "عکس رنگی، واضح و بدون تاری باشد.",
  "تمام سند و چهار گوشه آن در تصویر دیده شود و چیزی بریده نشود.",
  "نور مستقیم، انعکاس، سایه یا فلش روی متن و عکس سند نیفتد.",
  "روی و پشت سند را هرگاه سیستم درخواست کند، جداگانه ارسال کنید.",
  "از اسکرین‌شات یا فوتوکاپی استفاده نکنید اگر سیستم آن را قبول نمی‌کند.",
  "اگر سند با حروف غیرلاتین است و سیستم ترجمه می‌خواهد، ترجمه رسمی انگلیسی را مطابق دستور ارائه کنید.",
];

export default function JustMarketsVerification({ navigate }) {
  return (
    <JMPage>
      <JMHeader title="راهنمای وریفیکیشن" onBack={() => navigate("justmarkets")} />

      <section className="jm-section jm-page-intro">
        <JMSectionTitle
          eyebrow="KYC / Verification"
          title="سند هویتی را طوری آماده کنید که خوانا و قابل بررسی باشد"
          description="JustMarkets می‌تواند بسته به کشور، نوع حساب و بررسی داخلی، سند یا معلومات تکمیلی درخواست کند. همیشه دستور داخل Personal Area را معیار اصلی قرار دهید."
        />
      </section>

      <div className="jm-steps jm-section">
        <JMStep number="۱" icon={<IdentificationCard size={22} />} title="نوع سند درخواستی را ببینید">
          اگر پاسپورت، National ID یا سند دیگری درخواست شده، همان گزینه نمایش‌داده‌شده در حساب را آماده کنید.
        </JMStep>
        <JMStep number="۲" icon={<Camera size={22} />} title="عکس باکیفیت بگیرید">
          سند را روی سطح صاف، در نور یکنواخت و بدون لرزش کمره عکس بگیرید.
        </JMStep>
        <JMStep number="۳" icon={<Scan size={22} />} title="قبل از Upload دوباره بررسی کنید">
          خوانایی متن، چهار گوشه سند، مطابقت معلومات و فایل درست را چک کنید.
        </JMStep>
      </div>

      <section className="jm-section">
        <JMSectionTitle eyebrow="چک‌لیست" title="قبل از ارسال این موارد را بررسی کنید" />
        <div className="jm-checklist">
          {CHECKS.map((item) => (
            <div key={item}><CheckCircle size={20} weight="fill" /><span>{item}</span></div>
          ))}
        </div>
      </section>

      <JMNotice title="تأیید سند تضمین‌شده نیست" tone="warning">
        Saraf می‌تواند برای آماده‌سازی بهتر سند راهنمایی کند، اما تصمیم نهایی Verification توسط سیستم و تیم مربوط JustMarkets گرفته می‌شود.
      </JMNotice>

      <JMNotice title="در مورد تذکره افغانستان">
        اگر گزینه National ID برای حساب شما نمایش داده می‌شود، می‌توانید سند هویتی خود را مطابق همان دستور امتحان کنید. پذیرش نوع مشخص تذکره را بدون نمایش آن در حساب شما نمی‌توان تضمین کرد.
      </JMNotice>
    </JMPage>
  );
}
