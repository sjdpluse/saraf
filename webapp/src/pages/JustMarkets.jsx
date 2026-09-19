import { BookOpen, IdentificationCard, ShieldCheck, Wallet } from "@phosphor-icons/react";
import {
  JMHeader,
  JMNavCard,
  JMNotice,
  JMPage,
  JMPartnershipBadge,
  JMReferralCard,
  JMSectionTitle,
  JMServiceCard,
} from "../components/JustMarketsUI";

export default function JustMarkets({ navigate }) {
  return (
    <JMPage>
      <JMHeader title="JustMarkets" onBack={() => navigate("home")} />

      <section className="jm-hero">
        <JMPartnershipBadge />
        <h1 dir="ltr">Saraf IB – JustMarkets</h1>
        <p>
          صراف به‌عنوان Introducing Broker (IB) در مسیر معرفی، ساخت حساب، آشنایی با پلتفرم،
          آماده‌سازی وریفیکیشن و راهنمایی دیپازیت و برداشت به کاربران کمک می‌کند.
        </p>
        <JMNotice title="شفافیت قبل از هر چیز">
          صراف خود JustMarkets نیست و تصمیم‌های مربوط به حساب، وریفیکیشن و خدمات معاملاتی توسط خود JustMarkets انجام می‌شود.
        </JMNotice>
      </section>

      <section className="jm-section">
        <JMSectionTitle
          eyebrow="خدمات Saraf IB"
          title="همراهی در مراحل مهم"
          description="هدف این بخش این است که مراحل کار با JustMarkets برای کاربر واضح، منظم و قابل پیگیری باشد."
        />
        <div className="jm-service-grid">
          <JMServiceCard icon={<BookOpen size={22} weight="duotone" />} title="راهنمای پلتفرم">
            توضیح بروکر، MT5، حساب معاملاتی و نحوه شروع کار.
          </JMServiceCard>
          <JMServiceCard icon={<IdentificationCard size={22} weight="duotone" />} title="راهنمای وریفیکیشن">
            چک‌لیست سند، کیفیت عکس و مطابقت معلومات ثبت‌نام.
          </JMServiceCard>
          <JMServiceCard icon={<Wallet size={22} weight="duotone" />} title="راهنمای دیپازیت">
            مسیر خرید رمز ارز در صراف و انتقال مطابق روش‌های مجاز حساب خود کاربر.
          </JMServiceCard>
          <JMServiceCard icon={<ShieldCheck size={22} weight="duotone" />} title="راهنمای ریسک و امنیت">
            هشدارهای مربوط به شبکه، آدرس، حساب و روش‌های انتقال.
          </JMServiceCard>
        </div>
      </section>

      <JMReferralCard />

      <section className="jm-section">
        <JMSectionTitle eyebrow="دسترسی سریع" title="از کجا شروع می‌کنید؟" />
        <div className="jm-nav-list">
          <JMNavCard icon={<BookOpen size={22} />} title="راهنمای JustMarkets" description="بروکر، MT5 و شیوه کار" onClick={() => navigate("justmarkets-guide")} />
          <JMNavCard icon={<IdentificationCard size={22} />} title="راهنمای وریفیکیشن" description="تذکره، پاسپورت و کیفیت عکس" onClick={() => navigate("justmarkets-verification")} />
          <JMNavCard icon={<Wallet size={22} />} title="دیپازیت حساب" description="خرید رمز ارز و انتقال امن" onClick={() => navigate("justmarkets-deposit")} />
        </div>
      </section>

      <p className="jm-risk-note">
        معامله فارکس و CFD با خطر زیان همراه است. اهرم می‌تواند زیان و سود احتمالی را افزایش دهد و هیچ سودی تضمین‌شده نیست.
      </p>
    </JMPage>
  );
}
