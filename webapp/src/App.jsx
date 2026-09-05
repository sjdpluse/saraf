import { useEffect, useState } from "react";
import Home from "./pages/Home";
import Buy from "./pages/Buy";
import Sell from "./pages/Sell";
import Orders from "./pages/Orders";
import Reviews from "./pages/Reviews";
import Terms from "./pages/Terms";
import Kyc from "./pages/Kyc";
import Toast from "./components/Toast";
import { initTelegram, isInsideTelegram } from "./lib/telegram";
import { SARAF_LOGO_URL, normalizeAsset } from "./lib/brand";

export default function App() {
  const [page, setPage] = useState("home");
  const [asset, setAsset] = useState("USDT");
  const [error, setError] = useState(null);
  const [kycMode, setKycMode] = useState("profile");
  const [threshold, setThreshold] = useState(250);
  const [resume, setResume] = useState(null);

  useEffect(() => {
    initTelegram();
    const params = new URLSearchParams(window.location.search);
    const action = params.get("action");
    const requestedAsset = normalizeAsset(params.get("asset"));
    setAsset(requestedAsset);
    if (action === "buy" || action === "sell") setPage(action);
  }, []);

  function navigate(p) {
    setPage(p);
    window.scrollTo(0, 0);
  }

  function showError(message) {
    setError(message);
  }

  function selectAsset(nextAsset) {
    setAsset(normalizeAsset(nextAsset));
  }

  function startTransaction(action, nextAsset = asset) {
    setAsset(normalizeAsset(nextAsset));
    navigate(action);
  }

  function requestBasicProfile(target, resumeData) {
    const selectedAsset = normalizeAsset(resumeData?.asset || asset);
    setAsset(selectedAsset);
    setResume({ target, asset: selectedAsset, ...resumeData });
    setKycMode("profile");
    navigate("kyc");
  }

  function requestIdentityVerification(target, resumeData, thresholdUsd) {
    const selectedAsset = normalizeAsset(resumeData?.asset || asset);
    setAsset(selectedAsset);
    setResume({ target, asset: selectedAsset, ...resumeData });
    setKycMode("verify");
    if (thresholdUsd) setThreshold(thresholdUsd);
    navigate("kyc");
  }

  function handleKycComplete() {
    if (resume?.asset) setAsset(normalizeAsset(resume.asset));
    navigate(resume?.target || "home");
  }

  function handleKycCancel() {
    if (resume?.asset) setAsset(normalizeAsset(resume.asset));
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
            <img src={SARAF_LOGO_URL} alt="صراف" />
          </div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>این صفحه فقط داخل تلگرام کار می‌کند</div>
          <div className="notice" style={{ justifyContent: "center" }}>
            لطفاً از طریق ربات صراف دکمهٔ «خرید و فروش | USDT / USDC» را بزنید تا مینی‌اپ به‌درستی باز شود.
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div key={`${page}-${asset}`} className="page-transition">
        {page === "home" && (
          <Home
            navigate={navigate}
            startTransaction={startTransaction}
            selectedAsset={asset}
            onSelectAsset={selectAsset}
          />
        )}
        {page === "buy" && (
          <Buy
            asset={asset}
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
            asset={asset}
            navigate={navigate}
            showError={showError}
            resumeState={resume?.target === "sell" ? resume : null}
            onResumeConsumed={clearResume}
            onNeedProfile={(state) => requestBasicProfile("sell", state)}
            onNeedVerification={(state, thresholdUsd) => requestIdentityVerification("sell", state, thresholdUsd)}
          />
        )}
        {page === "orders" && <Orders navigate={navigate} showError={showError} />}
        {page === "reviews" && <Reviews navigate={navigate} showError={showError} />}
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
