from __future__ import annotations

import logging
import time
from typing import Any

import ccxt
import pandas as pd

LOGGER = logging.getLogger(__name__)


def make_exchange(config: dict[str, Any]):
    exchange_id = config.get("exchange", {}).get("id", "binance")
    exchange_cls = getattr(ccxt, exchange_id)
    options = {"enableRateLimit": True}
    market_type = config.get("exchange", {}).get("market_type", "spot")
    options["options"] = {"defaultType": market_type}
    api_key = __import__("os").getenv("EXCHANGE_API_KEY")
    secret = __import__("os").getenv("EXCHANGE_API_SECRET")
    if api_key and secret:
        options.update({"apiKey": api_key, "secret": secret})
    return exchange_cls(options)


def fetch_ohlcv(exchange, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """Fetch OHLCV and return a normalized UTC-indexed DataFrame."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            frame = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
            return frame.set_index("timestamp").astype(float)
        except (ccxt.BaseError, ValueError, TypeError) as exc:
            last_error = exc
            LOGGER.warning("OHLCV fetch failed %s %s attempt %s: %s", symbol, timeframe, attempt + 1, exc)
            time.sleep(2**attempt)
    raise RuntimeError(f"Unable to fetch {symbol} {timeframe}: {last_error}")


def select_symbols(exchange, config: dict[str, Any]) -> list[str]:
    exchange_cfg = config.get("exchange", {})
    configured = list(exchange_cfg.get("symbols", []))
    scan_limit = int(exchange_cfg.get("scan_limit", len(configured) or 10))
    if configured:
        return configured[:scan_limit]
    quote = exchange_cfg.get("quote", "USDT")
    tickers = exchange.fetch_tickers()
    candidates = []
    for symbol, ticker in tickers.items():
        if symbol.endswith(f"/{quote}") and ticker.get("quoteVolume"):
            candidates.append((float(ticker["quoteVolume"]), symbol))
    return [symbol for _, symbol in sorted(candidates, reverse=True)[:scan_limit]]
