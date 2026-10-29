import { useEffect, useState } from "react";
import Home from "./pages/Home";
import Markets from "./pages/Markets";
import NativeAccount from "./pages/NativeAccount";
import { IS_TELEGRAM_NATIVE, NATIVE_UNAVAILABLE_MESSAGE } from "./lib/runtime";
import Buy from "./pages/Buy";
import Sell from "./pages/Sell";
import Orders from "./pages/Orders";
import Reviews from "./pages/Reviews";
import Terms from "./pages/Terms";
import Kyc from "./pages/Kyc";
import Remittance from "./pages/Remittance";
import Remittances from "./pages/Remittances";
import About from "./pages/About";
import Menu from "./pages/Menu";
import JustMarkets from "./pages/JustMarkets";
import JustMarketsGuide from "./pages/JustMarketsGuide";
import JustMarketsVerification from "./pages/JustMarketsVerification";
import JustMarketsDeposit from "./pages/JustMarketsDeposit";
import Toast from "./components/Toast";
import BottomNav from "./components/BottomNav";
import { initTelegram, isInsideTelegram } from "./lib/telegram";
import { SARAF_LOGO_URL, normalizeAsset } from "./lib/brand";

export default function App() {
  const [page, setPage] = useState("home");
  const [asset, setAsset] = useState("USDT");
  const [error, setError] = useState(null);
  const [kycMode, setKycMode] = useState("profile");
  const [threshold, setThreshold] = useState(250);
  const [resume, setResume] = useState(null);
  const [remittanceOrder, setRemittanceOrder] = useState(null);

  useEffect(() => {
    initTelegram();
    const params = new URLSearchParams(window.location.search);
    const action = params.get("action");
    const requestedAsset = normalizeAsset(params.get("asset"));
    setAsset(requestedAsset);
    if (!IS_TELEGRAM_NATIVE && (action === "buy" || action === "sell")) setPage(action);
    if (!IS_TELEGRAM_NATIVE && action === "remittance") setPage("remittance");
    if (!IS_TELEGRAM_NATIVE && action === "remittances") setPage("remittances");
    if (action === "justmarkets") setPage("justmarkets");
  }, []);

  function navigate(p) {
    if (IS_TELEGRAM_NATIVE && ['buy', 'sell', 'orders', 'remittances', 'remittance', 'kyc'].includes(p)) {
      setError(NATIVE_UNAVAILABLE_MESSAGE);
      return;
    }
    if (p !== "remittance") setRemittanceOrder(null);
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
    if (IS_TELEGRAM_NATIVE) {
      setError(NATIVE_UNAVAILABLE_MESSAGE);
      return;
    }
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
            لطفاً از طریق ربات صراف مینی‌اپ را باز کنید.
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div key={`${page}-${asset}`} className="page-transition">
        {page === "home" && (
          <Home navigate={navigate} startTransaction={startTransaction} readOnly={IS_TELEGRAM_NATIVE} />
        )}
        {page === "markets" && IS_TELEGRAM_NATIVE && <Markets navigate={navigate} />}
        {page === "account" && IS_TELEGRAM_NATIVE && <NativeAccount navigate={navigate} />}
        {page === "buy" && !IS_TELEGRAM_NATIVE && (
          <Buy
            asset={asset}
            onSelectAsset={selectAsset}
            navigate={navigate}
            showError={showError}
            resumeState={resume?.target === "buy" ? resume : null}
            onResumeConsumed={clearResume}
            onNeedProfile={(state) => requestBasicProfile("buy", state)}
            onNeedVerification={(state, thresholdUsd) => requestIdentityVerification("buy", state, thresholdUsd)}
          />
        )}
        {page === "sell" && !IS_TELEGRAM_NATIVE && (
          <Sell
            asset={asset}
            onSelectAsset={selectAsset}
            navigate={navigate}
            showError={showError}
            resumeState={resume?.target === "sell" ? resume : null}
            onResumeConsumed={clearResume}
            onNeedProfile={(state) => requestBasicProfile("sell", state)}
            onNeedVerification={(state, thresholdUsd) => requestIdentityVerification("sell", state, thresholdUsd)}
          />
        )}
        {page === "remittance" && !IS_TELEGRAM_NATIVE && (
          <Remittance
            navigate={navigate}
            showError={showError}
            initialOrder={remittanceOrder}
            resumeState={resume?.target === "remittance" ? resume : null}
            onResumeConsumed={clearResume}
            onNeedProfile={(state) => requestBasicProfile("remittance", state)}
            onNeedVerification={(state, thresholdUsd) => requestIdentityVerification("remittance", state, thresholdUsd)}
          />
        )}
        {page === "orders" && !IS_TELEGRAM_NATIVE && <Orders navigate={navigate} showError={showError} />}
        {page === "remittances" && !IS_TELEGRAM_NATIVE && <Remittances navigate={navigate} onContinue={(order) => { setRemittanceOrder(order); navigate("remittance"); }} />}
        {page === "about" && <About navigate={navigate} />}
        {page === "reviews" && <Reviews navigate={navigate} showError={showError} />}
        {page === "terms" && <Terms navigate={navigate} />}
        {page === "menu" && <Menu navigate={navigate} readOnly={IS_TELEGRAM_NATIVE} />}
        {page === "justmarkets" && <JustMarkets navigate={navigate} />}
        {page === "justmarkets-guide" && <JustMarketsGuide navigate={navigate} />}
        {page === "justmarkets-verification" && <JustMarketsVerification navigate={navigate} />}
        {page === "justmarkets-deposit" && <JustMarketsDeposit navigate={navigate} startTransaction={startTransaction} />}
        {page === "kyc" && !IS_TELEGRAM_NATIVE && (
          <Kyc
            mode={kycMode}
            thresholdUsd={threshold}
            onComplete={handleKycComplete}
            onCancel={handleKycCancel}
            showError={showError}
          />
        )}
      </div>
      <BottomNav page={page} navigate={navigate} readOnly={IS_TELEGRAM_NATIVE} />
      <Toast message={error} onClose={() => setError(null)} />
    </>
  );
}
