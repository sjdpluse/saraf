import { useEffect, useState } from "react";
import Home from "./pages/Home";
import Buy from "./pages/Buy";
import Sell from "./pages/Sell";
import Orders from "./pages/Orders";
import Terms from "./pages/Terms";
import Kyc from "./pages/Kyc";
import Toast from "./components/Toast";
import { initTelegram, isInsideTelegram } from "./lib/telegram";
import { SARAF_LOGO_URL } from "./lib/brand";

export default function App() {
  const [page, setPage] = useState("home");
  const [error, setError] = useState(null);
  const [kycMode, setKycMode] = useState("profile"); // "profile" | "verify"
  const [threshold, setThreshold] = useState(250);
  // resume: { target: "buy"|"sell", amount, quote } — وقتی کاربر وسط خرید/فروش
  // به تکمیل پروفایل یا احراز هویت فرستاده می‌شود، این state نگه می‌دارد که
  // پس از برگشت دقیقاً به کجا و با چه مقدار/نرخی برگردد.
  const [resume, setResume] = useState(null);

  useEffect(() => {
    initTelegram();
  }, []);

  function navigate(p) {
    setPage(p);
    window.scrollTo(0, 0);
  }

  function showError(message) {
    setError(message);
  }

  /**
   * ورود به خرید/فروش دیگر پروفایل را از قبل چک نمی‌کند — کاربر همیشه مستقیم
   * به صفحهٔ خرید/فروش می‌رود و می‌تواند مبلغ و نرخ را بدون داشتن پروفایل
   * ببیند. فقط وقتی واقعاً روی «درخواست تتر» بزند، خود Buy/Sell وضعیت پروفایل
   * را چک و در صورت نیاز کاربر را به این‌جا (requestBasicProfile /
   * requestIdentityVerification) هدایت می‌کند.
   */
  function startTransaction(action) {
    navigate(action);
  }

  function requestBasicProfile(target, resumeData) {
    setResume({ target, ...resumeData });
    setKycMode("profile");
    navigate("kyc");
  }

  function requestIdentityVerification(target, resumeData, thresholdUsd) {
    setResume({ target, ...resumeData });
    setKycMode("verify");
    if (thresholdUsd) setThreshold(thresholdUsd);
    navigate("kyc");
  }

  function handleKycComplete() {
    navigate(resume?.target || "home");
  }

  function handleKycCancel() {
    navigate(resume?.target || "home");
  }

  function clearResume() {
    setResume(null);
  }

  if (!isInsideTelegram()) {
    return (
      <div className="app-shell">
        <div className="outside-telegram animate-in">
          <div className="logo-badge">
            <img src={SARAF_LOGO_URL} alt="Saraf" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>این صفحه فقط داخل تلگرام کار می‌کند</div>
          <div className="notice" style={{ justifyContent: "center" }}>
            لطفاً از طریق ربات Saraf در تلگرام دکمهٔ «خرید و فروش تتر» را بزنید تا این
            اپلیکیشن به‌درستی باز شود.
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* key={page} باعث می‌شود در هر تعویض صفحه، این wrapper دوباره mount شود
          و انیمیشن ورود (page-transition در index.css) از نو اجرا شود — یک
          transition سبک و ثابت بین همهٔ صفحات، بدون نیاز به کتابخانهٔ روتینگ. */}
      <div key={page} className="page-transition">
        {page === "home" && <Home navigate={navigate} startTransaction={startTransaction} />}
        {page === "buy" && (
          <Buy
            navigate={navigate}
            showError={showError}
            resumeState={resume?.target === "buy" ? resume : null}
            onResumeConsumed={clearResume}
            onNeedProfile={(state) => requestBasicProfile("buy", state)}
            onNeedVerification={(state, thresholdUsd) => requestIdentityVerification("buy", state, thresholdUsd)}
          />
        )}
        {page === "sell" && (
          <Sell
            navigate={navigate}
            showError={showError}
            resumeState={resume?.target === "sell" ? resume : null}
            onResumeConsumed={clearResume}
            onNeedProfile={(state) => requestBasicProfile("sell", state)}
            onNeedVerification={(state, thresholdUsd) => requestIdentityVerification("sell", state, thresholdUsd)}
          />
        )}
        {page === "orders" && <Orders navigate={navigate} showError={showError} />}
        {page === "terms" && <Terms navigate={navigate} />}
        {page === "kyc" && (
          <Kyc
            mode={kycMode}
            thresholdUsd={threshold}
            onComplete={handleKycComplete}
            onCancel={handleKycCancel}
            showError={showError}
          />
        )}
      </div>
      <Toast message={error} onClose={() => setError(null)} />
    </>
  );
}
