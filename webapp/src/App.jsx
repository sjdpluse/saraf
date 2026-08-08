import { useEffect, useState } from "react";
import Home from "./pages/Home";
import Buy from "./pages/Buy";
import Sell from "./pages/Sell";
import Orders from "./pages/Orders";
import Toast from "./components/Toast";
import { initTelegram, isInsideTelegram } from "./lib/telegram";

export default function App() {
  const [page, setPage] = useState("home");
  const [error, setError] = useState(null);

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

  if (!isInsideTelegram()) {
    return (
      <div className="app-shell">
        <div className="card" style={{ marginTop: 60, textAlign: "center" }}>
          <div style={{ fontSize: 30, marginBottom: 10 }}>🪙</div>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>این صفحه فقط داخل تلگرام کار می‌کند</div>
          <div className="notice">
            لطفاً از طریق ربات Saraf در تلگرام دکمهٔ «خرید و فروش تتر» را بزنید تا این
            اپلیکیشن به‌درستی باز شود.
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {page === "home" && <Home navigate={navigate} />}
      {page === "buy" && <Buy navigate={navigate} showError={showError} />}
      {page === "sell" && <Sell navigate={navigate} showError={showError} />}
      {page === "orders" && <Orders navigate={navigate} showError={showError} />}
      <Toast message={error} onClose={() => setError(null)} />
    </>
  );
}
