import test from "node:test";
import assert from "node:assert/strict";
import { marketChange } from "../src/lib/market.js";

const now = 1800000000000;
const snapshot = (change, updated = now / 1000) => ({
  status: "fresh", assets: [{ symbol: "BTC", change_24h: change, updated_at: updated }],
});

test("real zero, positive and negative market changes remain numbers", () => {
  for (const change of [0, -1.2, 3.4]) assert.equal(marketChange(snapshot(change), "BTC", now), change);
});
test("missing or malformed market data never becomes a zero change", () => {
  for (const change of [null, undefined, false, "2.5", NaN, Infinity]) {
    assert.equal(marketChange(snapshot(change), "BTC", now), null);
  }
  assert.equal(marketChange(null, "BTC", now), null);
  assert.equal(marketChange(snapshot(1), "USDC", now), null);
});
test("expired and future-dated values are hidden", () => {
  assert.equal(marketChange(snapshot(1, now / 1000 - 300), "BTC", now), 1);
  assert.equal(marketChange(snapshot(1, now / 1000 - 301), "BTC", now), null);
  assert.equal(marketChange(snapshot(1, now / 1000 + 61), "BTC", now), null);
});
test("an unavailable response cannot display a previous change", () => {
  assert.equal(marketChange({ ...snapshot(1), status: "unavailable" }, "BTC", now), null);
});
