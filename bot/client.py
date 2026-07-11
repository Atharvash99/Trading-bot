"""
Thin, well-logged wrapper around the Binance Futures Testnet (USDT-M) REST API.

Implemented with plain `requests` + HMAC-SHA256 signing so the bot has no
hard dependency on python-binance and it's obvious exactly what is sent
over the wire (useful for the logging requirement). Swapping this out for
python-binance's Client/UMFuturesClient later would be a drop-in change
behind the same public methods.
"""

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger()

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW_MS = 5000
REQUEST_TIMEOUT_S = 10


class BinanceAPIError(Exception):
    """Raised when Binance returns an error response (non-2xx or error payload)."""

    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class BinanceNetworkError(Exception):
    """Raised on connection/timeout failures talking to Binance."""


class FuturesTestnetClient:
    """Minimal client for the endpoints this bot needs.

    Only the order-placement and connectivity endpoints used by this
    application are implemented; extend as needed.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
    ):
        if not api_key or not api_secret:
            raise ValueError("API key and API secret are required.")
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # -- internal helpers ---------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", RECV_WINDOW_MS)
        query = urlencode(params, doseq=True)
        signature = hmac.new(self.api_secret, query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self, method: str, path: str, params: Dict[str, Any], signed: bool = True
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        request_params = self._sign(params) if signed else params

        # Log outgoing request (redact secret material)
        logger.debug(
            "REQUEST %s %s | params=%s",
            method,
            url,
            {k: v for k, v in request_params.items() if k != "signature"},
        )

        try:
            response = self.session.request(
                method, url, params=request_params, timeout=REQUEST_TIMEOUT_S
            )
        except requests.exceptions.RequestException as exc:
            logger.error("NETWORK ERROR calling %s %s: %s", method, url, exc)
            raise BinanceNetworkError(f"Network error calling {path}: {exc}") from exc

        logger.debug(
            "RESPONSE %s %s | status=%s body=%s",
            method,
            url,
            response.status_code,
            response.text,
        )

        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}

        if not response.ok:
            error_msg = body.get("msg", str(body)) if isinstance(body, dict) else str(body)
            logger.error(
                "API ERROR %s %s | status=%s code=%s msg=%s",
                method,
                url,
                response.status_code,
                body.get("code") if isinstance(body, dict) else None,
                error_msg,
            )
            raise BinanceAPIError(
                f"Binance API error ({response.status_code}): {error_msg}",
                status_code=response.status_code,
                payload=body,
            )

        return body

    # -- public API -----------------------------------------------------

    def ping(self) -> Dict[str, Any]:
        """Test connectivity to the REST API."""
        return self._request("GET", "/fapi/v1/ping", {}, signed=False)

    def get_account(self) -> Dict[str, Any]:
        """Fetch current account information (balances, positions, etc.)."""
        return self._request("GET", "/fapi/v2/account", {})

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Place a new order on the USDT-M Futures Testnet.

        For MARKET orders `price` is ignored. For LIMIT orders `price`
        is required and `time_in_force` is sent (defaults to GTC).
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders")
            params["price"] = price
            params["timeInForce"] = time_in_force
        if extra_params:
            params.update(extra_params)

        return self._request("POST", "/fapi/v1/order", params)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query the status of a previously placed order."""
        return self._request(
            "GET", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}
        )
