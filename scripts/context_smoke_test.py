#!/usr/bin/env python3
"""Probe live public context endpoints without fabricating historical data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from signalbot.config import load_config
from signalbot.context import fetch_derivatives_context, fetch_macro_context
from signalbot.market import make_exchange


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--output", default="data/context_smoke.json")
    args = parser.parse_args()
    config = load_config(args.config)
    exchange = make_exchange(config)
    exchange.load_markets()
    order_book = {"available": False, "source": "exchange_order_book"}
    try:
        from signalbot.context import fetch_order_book_context

        order_book = fetch_order_book_context(exchange, args.symbol, config)
    except Exception as exc:
        order_book["reason"] = type(exc).__name__
    output = {
        "symbol": args.symbol,
        "derivatives": fetch_derivatives_context(args.symbol, config),
        "order_book": order_book,
        "macro": fetch_macro_context(config),
        "historical_orthogonal_features": "not_available_in_repository",
        "status": "current_context_only",
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
