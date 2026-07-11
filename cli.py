#!/usr/bin/env python3
"""
CLI entry point for the Simplified Trading Bot (Binance Futures Testnet).

Usage examples:

  # Market order
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

  # Limit order
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

Credentials are read from environment variables (or a .env file, see README):
  BINANCE_TESTNET_API_KEY
  BINANCE_TESTNET_API_SECRET
"""

import argparse
import os
import sys

from bot.client import FuturesTestnetClient, DEFAULT_BASE_URL
from bot.logging_config import get_logger
from bot.orders import place_order

logger = get_logger()

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars can be set directly instead.
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET or LIMIT orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "market", "limit"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, type=float, help="Order quantity")
    parser.add_argument(
        "--price",
        required=False,
        type=float,
        default=None,
        help="Limit price (required for LIMIT orders)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
    api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")

    if not api_key or not api_secret:
        print(
            "[FAILED] Missing credentials. Set BINANCE_TESTNET_API_KEY and "
            "BINANCE_TESTNET_API_SECRET as environment variables (or in a .env file).",
            file=sys.stderr,
        )
        logger.error("Startup failed: missing API credentials in environment.")
        return 1

    try:
        client = FuturesTestnetClient(
            api_key=api_key, api_secret=api_secret, base_url=args.base_url
        )
    except ValueError as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        logger.error("Failed to initialize client: %s", exc)
        return 1

    result = place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
    )

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
