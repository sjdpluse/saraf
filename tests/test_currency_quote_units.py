"""Regression tests for source quote units versus user-visible quote units."""
import unittest
from unittest.mock import AsyncMock, patch

from config import CURRENCY_DISPLAY_UNITS
from handlers import currency
from services import (
    converter_service,
    currency_service,
    local_market_service,
    rate_engine,
    spread_service,
)


def _market_row(code: str, label: str, buy: str, sell: str) -> str:
    return (
        '<tr><td><a href="/exchange-rates/sarai-shahzada/'
        f'{code}-AFN">{code}/AFN <sup>{label}</sup></a></td>'
        f"<td>{buy}</td><td>{sell}</td></tr>"
    )


class CurrencyQuoteUnitTests(unittest.TestCase):
    def test_thousand_unit_rows_are_normalized_before_display(self):
        html = "<table>" + "".join([
            _market_row("PKR", "1K", "234", "235"),
            _market_row("INR", "1K", "708", "709"),
            _market_row("IRR", "1K", "0.25", "0.26"),
            _market_row("USD", "", "66.20", "66.25"),
        ]) + "</table>"
        rates = local_market_service._parse_html(html)["sarai_shahzada"]
        self.assertEqual(rates["pkr"]["buy"], 0.234)
        self.assertEqual(rates["inr"]["buy"], 0.708)
        self.assertEqual(rates["irr"]["buy"], 0.00025)
        self.assertEqual(rates["irr"]["sell"], 0.00026)
        self.assertEqual(rates["usd"]["buy"], 66.2)
        self.assertEqual(CURRENCY_DISPLAY_UNITS["irr"], 1_000_000)
        self.assertEqual(currency._scale("pkr", rates["pkr"]["buy"]), 234)
        self.assertEqual(currency._scale("inr", rates["inr"]["buy"]), 708)
        self.assertEqual(currency._scale("irr", rates["irr"]["buy"]), 250)

    def test_missing_thousand_unit_marker_fails_closed(self):
        html = "<table>" + _market_row("PKR", "", "234", "235") + "</table>"
        self.assertNotIn("pkr", local_market_service._parse_html(html)["sarai_shahzada"])

    def test_international_irr_is_rial_but_ui_irr_is_toman(self):
        self.assertEqual(currency_service._normalize_iso_rate("irr", 0.000025), 0.00025)
        self.assertEqual(currency_service._normalize_iso_rate("pkr", 0.234), 0.234)
        self.assertEqual(rate_engine._round_basis("irr", 0.000255), 0.000255)

    def test_spread_retains_sub_afghani_precision_for_toman(self):
        with patch.object(spread_service, "get_spread_percent", return_value=2):
            buy, sell = spread_service.apply_spread(0.000255, "irr")
        self.assertEqual((buy, sell), (0.00025245, 0.00025755))

    def test_telegram_and_facebook_quote_units(self):
        from services import facebook_service

        q = {
            "local": {"market_label": "سرای شهزاده (کابل)", "buy": 0.00025, "sell": 0.00026},
            "saraf_quote": {"buy": 0.00025245, "sell": 0.00025755},
            "reference_rate": 0.000255,
        }
        text = currency._format_quote_block_for_all("irr", "تومان ایرانی", q)
        caption = facebook_service._build_currency_block("irr", "تومان ایرانی", q)
        for display in (text, caption):
            self.assertIn("1,000,000", display)
            self.assertIn("250.00", display)
            self.assertIn("260.00", display)
            self.assertIn("252.45", display)
            self.assertIn("257.55", display)


class CurrencyConversionTests(unittest.IsolatedAsyncioTestCase):
    async def test_global_rial_rates_are_converted_into_toman(self):
        with patch.object(currency_service, "_fetch_json", new=AsyncMock(return_value={
            "afn": {"irr": 40_000, "pkr": 4.2735042735},
        })):
            rates = await currency_service._from_afn_base("test-url")
        self.assertEqual(rates["irr"], 0.00025)
        self.assertAlmostEqual(rates["pkr"], 0.234, places=4)

    async def test_converter_uses_toman_amounts_in_both_directions(self):
        with patch.object(converter_service, "_get_rates_for_base", new=AsyncMock(
            return_value={"usd": 1 / 2_700_000}
        )):
            dollars = await converter_service.convert("irr", "usd", 1_000_000)
        self.assertAlmostEqual(dollars, 3.703704, places=6)
        with patch.object(converter_service, "_get_rates_for_base", new=AsyncMock(
            return_value={"irr": 2_700_000}
        )):
            tomans = await converter_service.convert("usd", "irr", 1)
        self.assertEqual(tomans, 270_000)

    async def test_calculator_uses_one_million_toman_not_one_thousand(self):
        from unittest.mock import Mock

        context = Mock()
        context.user_data = {
            currency.AWAITING_CURRENCY_CALC: True,
            currency.CURRENCY_CALC_CODE: "irr",
        }
        update = Mock()
        update.message.text = "1000000"
        thinking = Mock()
        thinking.edit_text = AsyncMock()
        update.message.reply_text = AsyncMock(return_value=thinking)
        quote = {
            "local": {"market_label": "سرای شهزاده (کابل)", "buy": 0.00025, "sell": 0.00026},
            "saraf_quote": {"buy": 0.00025245, "sell": 0.00025755},
        }
        with patch.object(rate_engine, "get_full_quote", new=AsyncMock(return_value=quote)):
            handled = await currency.handle_currency_calc_input(update, context)
        self.assertTrue(handled)
        result = thinking.edit_text.call_args.args[0]
        self.assertIn("250.00 افغانی", result)
        self.assertIn("260.00 افغانی", result)
        self.assertIn("252.45 افغانی", result)
        self.assertIn("257.55 افغانی", result)


if __name__ == "__main__":
    unittest.main()
