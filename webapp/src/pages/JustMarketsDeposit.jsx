import { CheckCircle, Copy, Network, ShoppingCart, Wallet } from "@phosphor-icons/react";
import { JMHeader, JMNotice, JMPage, JMSectionTitle, JMStep } from "../components/JustMarketsUI";

export default function JustMarketsDeposit({ navigate, startTransaction }) {
  return (
    <JMPage>
      <JMHeader title="دیپازیت JustMarkets" onBack={() => navigate("justmarkets")} />

      <section className="jm-section jm-page-intro">
        <JMSectionTitle
          eyebrow="Deposit Guide"
          title="رمز ارز را از Saraf تهیه کنید، سپس مطابق روش مجاز حساب خودتان انتقال دهید"
          description="ابتدا داخل Personal Area خود JustMarkets روش‌های فعال دیپازیت، دارایی و شبکه را ببینید. بعد همان دارایی را از Saraf خریداری کنید."
        />
      </section>

      <section className="jm-deposit-cta-card">
        <span className="jm-deposit-cta-icon"><Wallet size={28} weight="duotone" /></span>
        <h2>برای دیپازیت به رمز ارز نیاز دارید؟</h2>
        <p>از جریان فعلی خرید رمز ارز در Saraf استفاده کنید و سپس انتقال را از حساب/کیف پول متعلق به خودتان انجام دهید.</p>
        <button type="button" className="jm-deposit-primary" onClick={() => startTransaction("buy")}> 
          <ShoppingCart size={20} weight="bold" />
          خرید رمز ارز برای دیپازیت
        </button>
        <button type="button" className="jm-deposit-secondary" onClick={() => startTransaction("sell")}>فروش رمز ارز</button>
      </section>

      <section className="jm-section">
        <JMSectionTitle eyebrow="چهار مرحله" title="مسیر درست انتقال" />
        <div className="jm-steps">
          <JMStep number="۱" icon={<Copy size={22} />} title="روش و آدرس را داخل حساب خود ببینید">
            از Personal Area خود JustMarkets دارایی، شبکه و در صورت وجود Address/Memo/Tag را دریافت کنید.
          </JMStep>
          <JMStep number="۲" icon={<Network size={22} />} title="دارایی و شبکه را دقیق تطبیق دهید">
            شبکه مبدأ و مقصد باید یکسان باشد. یک حرف اشتباه در آدرس یا شبکه می‌تواند باعث از دست‌رفتن دارایی شود.
          </JMStep>
          <JMStep number="۳" icon={<ShoppingCart size={22} />} title="رمز ارز را از Saraf بخرید">
            خرید را در جریان فعلی Saraf انجام دهید و دارایی را به کیف پول/حساب متعلق به خودتان دریافت کنید.
          </JMStep>
          <JMStep number="۴" icon={<CheckCircle size={22} />} title="از حساب خودتان به JustMarkets انتقال دهید">
            انتقال نهایی را مطابق روش‌های مجاز همان حساب انجام دهید و وضعیت ثبت موجودی را بررسی کنید.
          </JMStep>
        </div>
      </section>

      <JMNotice title="سپرده شخص ثالث" tone="warning">
        طبق راهنمای رسمی JustMarkets، سپرده شخص ثالث پذیرفته نمی‌شود. از حساب یا کیف پول شخص دیگری مستقیماً برای دیپازیت حساب معاملاتی خود استفاده نکنید.
      </JMNotice>

      <JMNotice title="شبکه و آدرس را چند بار بررسی کنید">
        پیش از ارسال، دارایی، شبکه، آدرس و در صورت نیاز Memo/Tag را با اطلاعات داخل JustMarkets تطبیق دهید.
      </JMNotice>
    </JMPage>
  );
}
