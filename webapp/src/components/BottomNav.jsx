import { ArrowRight, ClipboardText, House } from "@phosphor-icons/react";
import AppMenu from "./AppMenu";

export default function BottomNav({ page, navigate }) {
  function goBack() {
    const pageBack = Array.from(document.querySelectorAll(".back-btn"))
      .find((button) => !button.disabled);
    if (pageBack) {
      pageBack.click();
      return;
    }
    if (page !== "home") navigate("home");
  }

  return (
    <div className="bottom-nav-wrap" aria-label="ناوبری اصلی">
      <nav className="bottom-nav">
        <button
          className={`bottom-nav-item ${page === "home" ? "active" : ""}`}
          onClick={() => navigate("home")}
          aria-label="خانه"
        >
          <House size={25} weight={page === "home" ? "fill" : "regular"} />
        </button>
        <button
          className="bottom-nav-item"
          onClick={goBack}
          aria-label="بازگشت"
          disabled={page === "home"}
        >
          <ArrowRight size={25} />
        </button>
        <button
          className={`bottom-nav-item ${page === "orders" ? "active" : ""}`}
          onClick={() => navigate("orders")}
          aria-label="سفارش‌های من"
        >
          <ClipboardText size={25} weight={page === "orders" ? "fill" : "regular"} />
        </button>
        <AppMenu navigate={navigate} triggerClassName="bottom-nav-item" triggerIconSize={25} />
      </nav>
    </div>
  );
}
