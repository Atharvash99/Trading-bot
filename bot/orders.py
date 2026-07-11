"""
Order placement orchestration: ties validation + client together,
formats a human-readable summary, and logs the full lifecycle of
each order attempt.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import BinanceAPIError, BinanceNetworkError, FuturesTestnetClient
from .logging_config import get_logger
from .validators import OrderRequest, ValidationError, validate_order_request

logger = get_logger()


@dataclass
class OrderResult:
    success: bool
    message: str
    raw_response: Optional[Dict[str, Any]] = None


def build_order_summary(order: OrderRequest) -> str:
    lines = [
        "Order Request Summary",
        "----------------------",
        f"Symbol:   {order.symbol}",
        f"Side:     {order.side}",
        f"Type:     {order.order_type}",
        f"Quantity: {order.quantity}",
    ]
    if order.order_type == "LIMIT":
        lines.append(f"Price:    {order.price}")
    return "\n".join(lines)


def build_response_summary(response: Dict[str, Any]) -> str:
    order_id = response.get("orderId", "N/A")
    status = response.get("status", "N/A")
    executed_qty = response.get("executedQty", "N/A")
    avg_price = response.get("avgPrice", "N/A")
    return (
        "Order Response\n"
        "--------------\n"
        f"Order ID:      {order_id}\n"
        f"Status:        {status}\n"
        f"Executed Qty:  {executed_qty}\n"
        f"Avg Price:     {avg_price}"
    )


def place_order(
    client: FuturesTestnetClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
) -> OrderResult:
    """Validate input, place the order, print/log a summary, and return the result.

    Never raises: all expected failure modes (validation, API, network)
    are caught and returned as a failed OrderResult so the CLI layer can
    print a clean success/failure message.
    """
    # 1. Validate input
    try:
        order = validate_order_request(symbol, side, order_type, quantity, price)
    except ValidationError as exc:
        logger.warning("Validation failed for input: %s", exc)
        print(f"\n[FAILED] Invalid input: {exc}")
        return OrderResult(success=False, message=str(exc))

    summary = build_order_summary(order)
    print(f"\n{summary}")
    logger.info(
        "Placing order: symbol=%s side=%s type=%s qty=%s price=%s",
        order.symbol,
        order.side,
        order.order_type,
        order.quantity,
        order.price,
    )

    # 2. Call the API
    try:
        response = client.place_order(
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
        )
    except BinanceAPIError as exc:
        logger.error("Order failed (API error): %s", exc)
        print(f"\n[FAILED] Binance API rejected the order: {exc}")
        return OrderResult(success=False, message=str(exc))
    except BinanceNetworkError as exc:
        logger.error("Order failed (network error): %s", exc)
        print(f"\n[FAILED] Network error while placing order: {exc}")
        return OrderResult(success=False, message=str(exc))
    except Exception as exc:  # noqa: BLE001 - final safety net, logged with context
        logger.exception("Unexpected error while placing order")
        print(f"\n[FAILED] Unexpected error: {exc}")
        return OrderResult(success=False, message=str(exc))

    # 3. Report success
    response_summary = build_response_summary(response)
    print(f"\n{response_summary}")
    logger.info(
        "Order placed successfully: orderId=%s status=%s",
        response.get("orderId"),
        response.get("status"),
    )
    print("\n[SUCCESS] Order placed successfully.")
    return OrderResult(success=True, message="Order placed successfully.", raw_response=response)
