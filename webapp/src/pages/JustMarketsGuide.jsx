import { ChartLineUp, Coins, Desktop, ShieldCheck } from "@phosphor-icons/react";
import { JMHeader, JMNotice, JMPage, JMSectionTitle, JMServiceCard, JMStep } from "../components/JustMarketsUI";

export default function JustMarketsGuide({ navigate }) {
  return (
    <JMPage>
      <JMHeader title="راهنمای JustMarkets" onBack={() => navigate("justmarkets")} />

      <section className="jm-section jm-page-intro">
        <JMSectionTitle
          eyebrow="آشنایی عملی"
          title="JustMarkets دقیقاً چه نقشی دارد؟"
          description="JustMarkets یک بروکر آنلاین است که دسترسی به حساب‌های معاملاتی و پلتفرم‌هایی مانند MetaTrader 5 را فراهم می‌کند."
        />
      </section>

      <section className="jm-section">
        <div className="jm-service-grid">
          <JMServiceCard icon={<ChartLineUp size={22} weight="duotone" />} title="بروکر چیست؟">
            بروکر واسطه دسترسی شما به بازارهای مالی و اجرای سفارش‌هاست؛ خود بروکر بازار فارکس نیست.
          </JMServiceCard>
          <JMServiceCard icon={<Desktop size={22} weight="duotone" />} title="MT5 چه نقشی دارد؟">
            MetaTrader 5 نرم‌افزار معاملاتی است؛ حساب و سرور ورود را بروکر در اختیار شما قرار می‌دهد.
          </JMServiceCard>
          <JMServiceCard icon={<Coins size={22} weight="duotone" />} title="چه ابزارهایی دیده می‌شود؟">
            بسته به نوع حساب و دسترسی منطقه‌ای، جفت‌ارزها، طلا با نماد XAUUSD و سایر CFDها می‌توانند در دسترس باشند.
          </JMServiceCard>
          <JMServiceCard icon={<ShieldCheck size={22} weight="duotone" />} title="نقش Saraf IB">
            Saraf در معرفی، ثبت‌نام، فهم مراحل و راهنمایی عملی کاربران نقش دارد؛ نه در تضمین سود یا تایید حساب.
          </JMServiceCard>
        </div>
      </section>

      <JMNotice title="CFD با خرید خود دارایی فرق دارد" tone="warning">
        در CFD معمولاً روی تغییر قیمت معامله می‌کنید و لزوماً مالک دارایی پایه نمی‌شوید. استفاده از اهرم می‌تواند زیان را نیز بزرگ‌تر کند.
      </JMNotice>

      <section className="jm-section">
        <JMSectionTitle eyebrow="مسیر پیشنهادی" title="شروع کار در چهار مرحله" />
        <div className="jm-steps">
          <JMStep number="۱" title="ثبت‌نام از مسیر Saraf IB">از لینک معرفی یا Partner Code صراف برای ایجاد حساب استفاده کنید.</JMStep>
          <JMStep number="۲" title="تکمیل پروفایل و وریفیکیشن">معلومات واقعی خود را وارد کنید و دقیقاً درخواست‌های بخش Verification را دنبال کنید.</JMStep>
          <JMStep number="۳" title="شناخت حساب و MT5">نوع حساب، Login، Server و پلتفرم مناسب را قبل از شروع معامله بشناسید.</JMStep>
          <JMStep number="۴" title="دیپازیت طبق روش مجاز">روش‌های موجود در Personal Area خودتان را بررسی و سپس انتقال را انجام دهید.</JMStep>
        </div>
      </section>

      <section className="jm-faq-card">
        <JMSectionTitle eyebrow="پرسش‌های مهم" title="چند نکته که باید روشن باشد" />
        <details><summary>آیا Saraf خود JustMarkets است؟</summary><p>خیر. Saraf نقش IB/Introducing Broker و راهنمای کاربر را دارد.</p></details>
        <details><summary>آیا با ثبت‌نام از لینک Saraf سود تضمین می‌شود؟</summary><p>خیر. هیچ نتیجه معاملاتی تضمین نمی‌شود و بازارهای اهرمی می‌توانند باعث زیان شوند.</p></details>
        <details><summary>آیا MT5 همان بروکر است؟</summary><p>خیر. MT5 پلتفرم معاملاتی است و حساب معاملاتی شما توسط بروکر ایجاد می‌شود.</p></details>
      </section>
    </JMPage>
  );
}
