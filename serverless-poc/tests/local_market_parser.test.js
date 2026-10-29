import test from "node:test";
import assert from "node:assert/strict";
import { parseLocalMarketHtml } from "../tgcloud/lib/local_market_parser.js";
const sample = '<table><tr><td><a href="/exchange-rates/sarai-shahzada/USD-AFN">USD</a></td><td>65.90</td><td>66.20</td></tr></table>';
test("parse local market USD rates", () => {
 const output = parseLocalMarketHtml(sample);
 assert.deepEqual(output.sarai_shahzada.usd, {buy:65.9,sell:66.2});
});
test("no data is not a valid quote", () => {
 const output = parseLocalMarketHtml("<p>empty</p>");
 assert.deepEqual(output.sarai_shahzada, {});
});