// Display-only market data. Missing or old values must never become a 0% quote.
export function marketChange(snapshot, symbol, now = Date.now()) {
  const item = snapshot?.assets?.find((coin) => coin.symbol === symbol);
  const age = now / 1000 - Number(item?.updated_at);
  if (snapshot?.status !== "fresh" || typeof item?.change_24h !== "number" || !Number.isFinite(item.change_24h) || !Number.isFinite(age) || age < -60 || age > 300) return null;
  return item.change_24h;
}
