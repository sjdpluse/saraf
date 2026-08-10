import { useEffect, useState } from "react";
import Home from "./pages/Home";
import Buy from "./pages/Buy";
import Sell from "./pages/Sell";
import Orders from "./pages/Orders";
import Terms from "./pages/Terms";
import Kyc from "./pages/Kyc";
import Toast from "./components/Toast";
import { initTelegram, isInsideTelegram } from "./lib/telegram";
import { api } from "./lib/api";

export default function App() {
  const [page, setPage] = useState("home");
  const [error, setError] = useState(null);
  const [pendingAction, setPendingAction] = useState(null); // "buy" | "sell" بعد از تکمیل KYC

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
   * نقطهٔ ورود مشترک برای خرید/فروش — قبل از رفتن به فرم معامله، وضعیت پروفایل
   * را چک می‌کند. اگر ناقص بود، اول کاربر را به KYC می‌فرستد و بعد از تکمیل،
   * خودکار به همان صفحه (خرید/فروش) برمی‌گرداند.
   */
  async function startTransaction(action) {
    try {
      const { kyc_complete } = await api.getProfile();
      if (kyc_complete) {
        navigate(action);
      } else {
        setPendingAction(action);
        navigate("kyc");
      }
    } catch (e) {
      // در صورت خطای شبکه/سرور، برای اطمینان کاربر را به KYC می‌فرستیم تا سفارش
      // بدون پروفایل ثبت نشود
      setPendingAction(action);
      navigate("kyc");
    }
  }

  function handleKycComplete() {
    const action = pendingAction || "home";
    setPendingAction(null);
    navigate(action);
  }

  if (!isInsideTelegram()) {
    return (
      <div className="app-shell">
        <div className="card" style={{ marginTop: 60, textAlign: "center" }}>
          <div style={{ fontSize: 30, marginBottom: 10 }}>🪙</div>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>این صفحه فقط داخل تلگرام کار می‌کند</div>
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
      {page === "home" && <Home navigate={navigate} startTransaction={startTransaction} />}
      {page === "buy" && <Buy navigate={navigate} showError={showError} />}
      {page === "sell" && <Sell navigate={navigate} showError={showError} />}
      {page === "orders" && <Orders navigate={navigate} showError={showError} />}
      {page === "terms" && <Terms navigate={navigate} />}
      {page === "kyc" && (
        <Kyc onComplete={handleKycComplete} onCancel={() => navigate("home")} showError={showError} />
      )}
      <Toast message={error} onClose={() => setError(null)} />
    </>
  );
}
