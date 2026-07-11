"""
Input validation for order requests.

Keeping validation separate from CLI parsing and API calls makes it
independently testable and reusable (e.g. from a future UI or API layer).
"""

import re
from dataclasses import dataclass
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}
# Basic sanity check for USDT-M perpetual futures symbols, e.g. BTCUSDT, ETHUSDT
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,17}USDT$")


class ValidationError(ValueError):
    """Raised when user-supplied order parameters are invalid."""


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None


def validate_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
) -> OrderRequest:
    """Validate raw CLI input and return a normalized OrderRequest.

    Raises ValidationError with a human-readable message on any problem.
    """
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected a USDT-M pair like 'BTCUSDT'."
        )

    if not side:
        raise ValidationError("Side is required (BUY or SELL).")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {VALID_SIDES}.")

    if not order_type:
        raise ValidationError("Order type is required (MARKET or LIMIT).")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {VALID_ORDER_TYPES}."
        )

    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0.")

    normalized_price: Optional[float] = None
    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            normalized_price = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Price must be a number, got '{price}'.")
        if normalized_price <= 0:
            raise ValidationError("Price must be greater than 0.")
    elif price is not None:
        # MARKET orders don't take a price; warn via exception only if
        # caller explicitly passed a nonsensical value rather than None.
        try:
            if float(price) <= 0:
                raise ValidationError("Price, if provided, must be greater than 0.")
        except (TypeError, ValueError):
            raise ValidationError(f"Price must be a number, got '{price}'.")

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=normalized_price,
    )
