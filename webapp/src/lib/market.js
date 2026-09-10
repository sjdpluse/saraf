// Display-only market data. Missing values must never become a fabricated 0% quote.
// Keep the last verified CoinGecko value usable for up to 15 minutes so brief
// upstream/network interruptions do not make every map percentage disappear.
export function marketChange(snapshot, symbol, now = Date.now()) {
  const item = snapshot?.assets?.find((coin) => coin.symbol === symbol);
  const age = now / 1000 - Number(item?.updated_at);
  if (typeof item?.change_24h !== "number" || !Number.isFinite(item.change_24h) || !Number.isFinite(age) || age < -60 || age > 900) return null;
  return item.change_24h;
}
