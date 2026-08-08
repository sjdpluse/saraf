export default function Home({ navigate }) {
  return (
    <div className="app-shell">
      <div className="header">
        <h1>🪙 Saraf — خرید و فروش تتر</h1>
      </div>

      <div className="menu-grid">
        <div className="menu-tile buy" onClick={() => navigate("buy")}>
          <div className="icon">🟢</div>
          <div className="title">خرید تتر</div>
          <div className="subtitle">افغانی → USDT</div>
        </div>
        <div className="menu-tile sell" onClick={() => navigate("sell")}>
          <div className="icon">🔴</div>
          <div className="title">فروش تتر</div>
          <div className="subtitle">USDT → افغانی</div>
        </div>
      </div>

      <div className="card" onClick={() => navigate("orders")} style={{ cursor: "pointer" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>📋 سفارش‌های من</div>
            <div className="notice">پیگیری وضعیت خرید/فروش‌های قبلی</div>
          </div>
          <div style={{ color: "var(--saraf-hint)", fontSize: 20 }}>‹</div>
        </div>
      </div>

      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 12 }}>چرا Saraf؟</div>
        <div className="trust-badges">
          <div className="trust-badge">
            <span className="dot" /> نرخ لحظه‌یی بر مبنای بازار واقعی صرافی‌های کابل
          </div>
          <div className="trust-badge">
            <span className="dot" /> هر سفارش پیش از پردازش، توسط تیم ما بررسی و تایید می‌شود
          </div>
          <div className="trust-badge">
            <span className="dot" /> پرداخت حضوری یا بانکی — هرچه برایتان راحت‌تر است
          </div>
          <div className="trust-badge">
            <span className="dot" /> پشتیبانی مستقیم: @SJDPLUS
          </div>
        </div>
      </div>
    </div>
  );
}
