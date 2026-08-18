from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

from .config import load_config
from .formatters import format_risk_alert, format_signal
from .market import fetch_ohlcv, make_exchange, select_symbols
from .models import Signal, utc_now_iso
from .news import fetch_news
from .notifier import notify
from .risk import calculate_risk_state, can_open_signal
from .storage import append_csv, append_jsonl, build_performance, read_json, write_json
from .strategy import generate_signal

LOGGER = logging.getLogger(__name__)


def _paths(config: dict[str, Any]) -> dict[str, Path]:
    storage = config.get("storage", {})
    return {key: Path(value) for key, value in {
        "signals": storage.get("signals_file", "data/signals.jsonl"),
        "trades": storage.get("trades_file", "data/trades.json"),
        "performance": storage.get("performance_file", "data/performance.json"),
        "signal_csv": storage.get("signals_file", "data/signals.jsonl").replace(".jsonl", ".csv"),
    }.items()}


def _record_signal(signal: Signal, paths: dict[str, Path], config: dict[str, Any]) -> None:
    row = signal.to_dict()
    append_jsonl(paths["signals"], row, int(config.get("storage", {}).get("max_log_rows", 5000)))
    append_csv(paths["signal_csv"], row)


def _update_open_trades(trades: list[dict[str, Any]], exchange, config: dict[str, Any]) -> bool:
    changed = False
    for trade in trades:
        if trade.get("status") != "OPEN":
            continue
        try:
            ticker = exchange.fetch_ticker(trade["symbol"])
            price = float(ticker["last"])
            side = trade["side"]
            stop = float(trade["stop_loss"])
            target = float(trade["take_profit"])
            hit = "TP_HIT" if (side == "LONG" and price >= target) or (side == "SHORT" and price <= target) else "SL_HIT" if (side == "LONG" and price <= stop) or (side == "SHORT" and price >= stop) else None
            if not hit:
                continue
            entry = float(trade["entry"])
            size = float(trade.get("position_size", 0))
            pnl_per_unit = (target - entry if hit == "TP_HIT" and side == "LONG" else entry - target if hit == "TP_HIT" else stop - entry if side == "LONG" else entry - stop)
            pnl_amount = pnl_per_unit * size
            risk_amount = float(trade.get("risk_amount", 0))
            trade.update({"status": hit, "exit_price": target if hit == "TP_HIT" else stop, "closed_at": utc_now_iso(), "pnl_amount": round(pnl_amount, 2), "result_r": round(pnl_amount / risk_amount, 3) if risk_amount else 0.0})
            changed = True
            LOGGER.info("Updated %s -> %s", trade.get("signal_id"), hit)
        except Exception as exc:  # one broken ticker must not stop the cycle
            LOGGER.warning("Could not update trade %s: %s", trade.get("signal_id"), exc)
    return changed


def scan(config_path: str = "config.yaml") -> int:
    config = load_config(config_path)
    paths = _paths(config)
    trades = read_json(paths["trades"], [])
    exchange = make_exchange(config)
    exchange.load_markets()

    if not exchange.has.get("fetchOHLCV"):
        raise RuntimeError("Configured exchange does not support OHLCV fetching")
    try:
        updated = _update_open_trades(trades, exchange, config)
        if updated:
            write_json(paths["trades"], trades)
    except Exception as exc:
        LOGGER.warning("Open-trade update phase failed: %s", exc)

    state = calculate_risk_state(trades, config)
    if state.paused:
        message = format_risk_alert(state.pause_reason, state.to_dict(), config["notifications"]["disclaimer"])
        notify(message, config)
        write_json(paths["performance"], build_performance(trades))
        return 0

    try:
        news = fetch_news(config)
    except Exception as exc:
        LOGGER.warning("News phase failed; continuing without news filter: %s", exc)
        news = []
    symbols = select_symbols(exchange, config)
    timeframes = config["exchange"]["timeframes"]
    limit = int(config["exchange"].get("candles", 250))
    seen: set[str] = set()
    generated = 0

    for symbol in symbols:
        try:
            frames = {tf: fetch_ohlcv(exchange, symbol, tf, limit) for tf in set(timeframes.values())}
            signal = generate_signal(symbol, frames, news, config)
            if not signal or signal.signal_id in seen:
                continue
            seen.add(signal.signal_id)
            allowed, reason = can_open_signal(signal, trades, state, config)
            if not allowed:
                LOGGER.info("Signal skipped for %s: %s", symbol, reason)
                continue
            trade = signal.to_dict()
            trade.update({"opened_at": signal.created_at, "pnl_amount": 0.0, "equity_after": state.current_balance})
            trades.append(trade)
            _record_signal(signal, paths, config)
            results = notify(format_signal(signal, config["notifications"]["disclaimer"]), config)
            LOGGER.info("Signal %s delivered: %s", signal.signal_id, results)
            generated += 1
        except Exception as exc:
            LOGGER.exception("Scan failed for %s; continuing: %s", symbol, exc)

    write_json(paths["trades"], trades[-int(config.get("storage", {}).get("max_log_rows", 5000)):])
    write_json(paths["performance"], build_performance(trades))
    LOGGER.info("Scan complete: symbols=%s generated=%s news=%s", len(symbols), generated, len(news))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated crypto signal scanner")
    parser.add_argument("command", choices=["scan", "summary"], nargs="?", default="scan")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    if args.command == "summary":
        paths = _paths(config)
        trades = read_json(paths["trades"], [])
        write_json(paths["performance"], build_performance(trades))
        print(build_performance(trades))
        return 0
    return scan(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
