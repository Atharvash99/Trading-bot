"""
Offline unit tests for input validation.

Run with:  python -m unittest discover -s tests
No API credentials or network access required.
"""

import unittest

from bot.validators import ValidationError, validate_order_request


class TestValidateOrderRequest(unittest.TestCase):
    def test_valid_market_order(self):
        order = validate_order_request("btcusdt", "buy", "market", 0.01, None)
        self.assertEqual(order.symbol, "BTCUSDT")
        self.assertEqual(order.side, "BUY")
        self.assertEqual(order.order_type, "MARKET")
        self.assertEqual(order.quantity, 0.01)
        self.assertIsNone(order.price)

    def test_valid_limit_order(self):
        order = validate_order_request("ETHUSDT", "SELL", "LIMIT", 0.5, 3200.5)
        self.assertEqual(order.order_type, "LIMIT")
        self.assertEqual(order.price, 3200.5)

    def test_missing_symbol(self):
        with self.assertRaises(ValidationError):
            validate_order_request("", "BUY", "MARKET", 1, None)

    def test_invalid_symbol_format(self):
        with self.assertRaises(ValidationError):
            validate_order_request("BTC", "BUY", "MARKET", 1, None)

    def test_invalid_side(self):
        with self.assertRaises(ValidationError):
            validate_order_request("BTCUSDT", "HOLD", "MARKET", 1, None)

    def test_invalid_order_type(self):
        with self.assertRaises(ValidationError):
            validate_order_request("BTCUSDT", "BUY", "STOP", 1, None)

    def test_non_numeric_quantity(self):
        with self.assertRaises(ValidationError):
            validate_order_request("BTCUSDT", "BUY", "MARKET", "abc", None)

    def test_zero_or_negative_quantity(self):
        with self.assertRaises(ValidationError):
            validate_order_request("BTCUSDT", "BUY", "MARKET", 0, None)
        with self.assertRaises(ValidationError):
            validate_order_request("BTCUSDT", "BUY", "MARKET", -1, None)

    def test_limit_order_missing_price(self):
        with self.assertRaises(ValidationError):
            validate_order_request("BTCUSDT", "BUY", "LIMIT", 1, None)

    def test_limit_order_negative_price(self):
        with self.assertRaises(ValidationError):
            validate_order_request("BTCUSDT", "BUY", "LIMIT", 1, -5)


if __name__ == "__main__":
    unittest.main()
