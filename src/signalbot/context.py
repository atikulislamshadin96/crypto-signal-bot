from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

LOGGER = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _float(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "NaN"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_json(url: str, params: dict[str, Any] | None = None, timeout: int = 8) -> Any:
    response = requests.get(
        url,
        params=params,
        timeout=timeout,
        headers={"User-Agent": "crypto-signal-bot/2.0"},
    )
    response.raise_for_status()
    return response.json()


def _futures_symbol(symbol: str) -> str:
    return symbol.replace("/", "").replace(":USDT", "").upper()


def fetch_derivatives_context(symbol: str, config: dict[str, Any]) -> dict[str, Any]:
    """Fetch public Binance Futures positioning context.

    These endpoints are current/short-history context, not a substitute for a
    point-in-time historical derivatives database. Missing fields are explicit.
    """
    cfg = config.get("context", {}).get("derivatives", {})
    base = str(cfg.get("base_url", "https://fapi.binance.com"))
    if not bool(cfg.get("enabled", True)):
        return {"available": False, "source": "binance_futures_public", "reason": "disabled"}

    futures_symbol = _futures_symbol(symbol)
    result: dict[str, Any] = {
        "available": False,
        "source": "binance_futures_public",
        "timestamp": _now(),
        "symbol": futures_symbol,
        "funding_rate": None,
        "open_interest": None,
        "open_interest_change_pct": None,
        "long_short_ratio": None,
        "errors": [],
    }
    try:
        premium = _get_json(f"{base}/fapi/v1/premiumIndex", {"symbol": futures_symbol})
        result["funding_rate"] = _float(premium.get("lastFundingRate"))
    except Exception as exc:  # public endpoint can be geo/rate restricted
        result["errors"].append(f"funding:{type(exc).__name__}")
    try:
        oi = _get_json(f"{base}/fapi/v1/openInterest", {"symbol": futures_symbol})
        result["open_interest"] = _float(oi.get("openInterest"))
    except Exception as exc:
        result["errors"].append(f"open_interest:{type(exc).__name__}")
    try:
        history = _get_json(
            f"{base}/futures/data/openInterestHist",
            {"symbol": futures_symbol, "period": cfg.get("history_period", "15m"), "limit": 2},
        )
        if isinstance(history, list) and len(history) >= 2:
            previous = _float(history[-2].get("sumOpenInterest"))
            latest = _float(history[-1].get("sumOpenInterest"))
            if previous and latest:
                result["open_interest_change_pct"] = (latest / previous - 1.0) * 100.0
    except Exception as exc:
        result["errors"].append(f"open_interest_history:{type(exc).__name__}")
    try:
        ratio = _get_json(
            "https://futures.binance.com/futures/data/globalLongShortAccountRatio",
            {"symbol": futures_symbol, "period": cfg.get("history_period", "15m"), "limit": 1},
        )
        if isinstance(ratio, list) and ratio:
            result["long_short_ratio"] = _float(ratio[-1].get("longShortRatio"))
    except Exception as exc:
        result["errors"].append(f"long_short:{type(exc).__name__}")

    result["available"] = any(
        result.get(key) is not None for key in ("funding_rate", "open_interest", "long_short_ratio")
    )
    return result


def _depth_features(order_book: dict[str, Any], levels: int) -> dict[str, Any]:
    bids = order_book.get("bids") or []
    asks = order_book.get("asks") or []
    bids = [(float(price), float(size)) for price, size in bids[:levels] if float(size) > 0]
    asks = [(float(price), float(size)) for price, size in asks[:levels] if float(size) > 0]
    if not bids or not asks:
        return {"available": False, "reason": "empty_order_book"}
    best_bid, best_bid_size = bids[0]
    best_ask, best_ask_size = asks[0]
    mid = (best_bid + best_ask) / 2
    bid_depth = sum(size for _, size in bids)
    ask_depth = sum(size for _, size in asks)
    total_depth = bid_depth + ask_depth
    avg_bid = bid_depth / len(bids)
    avg_ask = ask_depth / len(asks)
    max_bid = max(bids, key=lambda row: row[1])
    max_ask = max(asks, key=lambda row: row[1])
    return {
        "available": True,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread_bps": (best_ask - best_bid) / mid * 10_000 if mid else None,
        "imbalance": (bid_depth - ask_depth) / total_depth if total_depth else 0.0,
        "bid_depth": bid_depth,
        "ask_depth": ask_depth,
        "bid_wall_ratio": max_bid[1] / avg_bid if avg_bid else None,
        "ask_wall_ratio": max_ask[1] / avg_ask if avg_ask else None,
        "bid_wall_distance_bps": (mid - max_bid[0]) / mid * 10_000 if mid else None,
        "ask_wall_distance_bps": (max_ask[0] - mid) / mid * 10_000 if mid else None,
        "levels": levels,
    }


def fetch_order_book_context(exchange: Any, symbol: str, config: dict[str, Any]) -> dict[str, Any]:
    cfg = config.get("context", {}).get("order_book", {})
    if not bool(cfg.get("enabled", True)):
        return {"available": False, "source": "exchange_order_book", "reason": "disabled"}
    try:
        order_book = exchange.fetch_order_book(symbol, limit=int(cfg.get("levels", 50)))
        features = _depth_features(order_book, int(cfg.get("levels", 50)))
        features.update({"source": "exchange_order_book", "timestamp": _now()})
        return features
    except Exception as exc:
        LOGGER.warning("Order-book context failed for %s: %s", symbol, exc)
        return {
            "available": False,
            "source": "exchange_order_book",
            "reason": f"{type(exc).__name__}",
            "timestamp": _now(),
        }


def _fred_daily_change(cfg: dict[str, Any]) -> dict[str, Any]:
    series_id = str(cfg.get("series_id", "DTWEXBGS"))
    url = str(cfg.get("csv_url", "https://fred.stlouisfed.org/graph/fredgraph.csv"))
    try:
        raw = requests.get(url, params={"id": series_id}, timeout=8, headers={"User-Agent": "crypto-signal-bot/2.0"})
        raw.raise_for_status()
        from io import StringIO

        frame = pd.read_csv(StringIO(raw.text))
        value_col = series_id if series_id in frame.columns else frame.columns[-1]
        values = pd.to_numeric(frame[value_col], errors="coerce").dropna()
        if len(values) < 2:
            return {"available": False, "source": "fred", "reason": "insufficient_observations"}
        latest, previous = float(values.iloc[-1]), float(values.iloc[-2])
        return {
            "available": True,
            "source": "fred",
            "series_id": series_id,
            "value": latest,
            "change_pct": (latest / previous - 1.0) * 100.0 if previous else None,
            "timestamp": _now(),
        }
    except Exception as exc:
        return {"available": False, "source": "fred", "series_id": series_id, "reason": f"{type(exc).__name__}"}


def fetch_macro_context(config: dict[str, Any]) -> dict[str, Any]:
    cfg = config.get("context", {}).get("macro", {})
    if not bool(cfg.get("enabled", True)):
        return {"available": False, "source": "macro_bundle", "reason": "disabled"}
    result: dict[str, Any] = {"available": False, "source": "macro_bundle", "timestamp": _now(), "errors": []}
    try:
        global_data = _get_json(str(cfg.get("coingecko_url", "https://api.coingecko.com/api/v3/global")))
        data = global_data.get("data", {})
        result["btc_dominance"] = _float((data.get("market_cap_percentage") or {}).get("btc"))
        result["market_cap_change_24h_pct"] = _float(data.get("market_cap_change_percentage_24h_usd"))
        result["coingecko_available"] = result.get("btc_dominance") is not None
    except Exception as exc:
        result["errors"].append(f"coingecko:{type(exc).__name__}")
        result["coingecko_available"] = False
    try:
        stable = _get_json(str(cfg.get("defillama_stablecoin_url", "https://stablecoins.llama.fi/stablecoincharts/all")))
        points = [row for row in stable if row.get("totalCirculatingUSD", {}).get("peggedUSD") is not None]
        if len(points) >= 8:
            latest = _float(points[-1]["totalCirculatingUSD"]["peggedUSD"])
            prior = _float(points[-8]["totalCirculatingUSD"]["peggedUSD"])
            result["stablecoin_supply_usd"] = latest
            result["stablecoin_supply_change_7d_pct"] = (latest / prior - 1.0) * 100.0 if latest and prior else None
        result["defillama_available"] = bool(points)
    except Exception as exc:
        result["errors"].append(f"defillama:{type(exc).__name__}")
        result["defillama_available"] = False
    fred_cfg = cfg.get("fred", {})
    result["dxy"] = _fred_daily_change(fred_cfg) if bool(fred_cfg.get("enabled", False)) else {"available": False, "source": "fred", "reason": "disabled"}
    result["available"] = bool(result.get("coingecko_available") or result.get("defillama_available") or result["dxy"].get("available"))
    return result


def collect_market_context(exchange: Any, symbol: str, config: dict[str, Any], macro: dict[str, Any] | None = None) -> dict[str, Any]:
    """Collect optional orthogonal context without making fabricated values."""
    return {
        "collected_at": _now(),
        "symbol": symbol,
        "derivatives": fetch_derivatives_context(symbol, config),
        "order_book": fetch_order_book_context(exchange, symbol, config),
        "macro": macro if macro is not None else fetch_macro_context(config),
    }


def context_feature_snapshot(context: dict[str, Any]) -> dict[str, float | None]:
    derivatives = context.get("derivatives", {})
    order_book = context.get("order_book", {})
    macro = context.get("macro", {})
    dxy = macro.get("dxy", {}) if isinstance(macro.get("dxy"), dict) else {}
    return {
        "funding_rate": _float(derivatives.get("funding_rate")),
        "open_interest_change_pct": _float(derivatives.get("open_interest_change_pct")),
        "long_short_ratio": _float(derivatives.get("long_short_ratio")),
        "order_book_imbalance": _float(order_book.get("imbalance")),
        "spread_bps": _float(order_book.get("spread_bps")),
        "bid_wall_ratio": _float(order_book.get("bid_wall_ratio")),
        "ask_wall_ratio": _float(order_book.get("ask_wall_ratio")),
        "btc_dominance": _float(macro.get("btc_dominance")),
        "market_cap_change_24h_pct": _float(macro.get("market_cap_change_24h_pct")),
        "stablecoin_supply_change_7d_pct": _float(macro.get("stablecoin_supply_change_7d_pct")),
        "dxy_change_pct": _float(dxy.get("change_pct")),
    }


def context_coverage(context: dict[str, Any]) -> float:
    features = context_feature_snapshot(context)
    return sum(value is not None for value in features.values()) / len(features)
