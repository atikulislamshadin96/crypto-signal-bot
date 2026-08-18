from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import load_config
from .context import collect_market_context, context_coverage, context_feature_snapshot, fetch_macro_context
from .formatters import format_risk_alert, format_signal
from .market import fetch_ohlcv, make_exchange, select_symbols
from .models import Signal, utc_now_iso
from .news import fetch_news
from .notifier import notify
from .risk import calculate_risk_state, can_open_signal
from .storage import (
    append_csv,
    append_jsonl,
    append_jsonl_unbounded,
    build_period_summary,
    build_performance,
    read_json,
    write_json,
)
from .strategy import generate_signal

LOGGER = logging.getLogger(__name__)


def _paths(config: dict[str, Any]) -> dict[str, Path]:
    storage = config.get("storage", {})
    signals = storage.get("signals_file", "data/signals.jsonl")
    return {
        "signals": Path(signals),
        "trades": Path(storage.get("trades_file", "data/trades.json")),
        "performance": Path(storage.get("performance_file", "data/performance.json")),
        "signal_csv": Path(str(signals).replace(".jsonl", ".csv")),
        "feature_archive": Path(storage.get("feature_archive_file", "data/feature_archive.jsonl")),
        "daily_summary": Path(storage.get("daily_summary_file", "data/summary_daily.json")),
        "weekly_summary": Path(storage.get("weekly_summary_file", "data/summary_weekly.json")),
    }


def _record_signal(signal: Signal, paths: dict[str, Path], config: dict[str, Any]) -> None:
    row = signal.to_dict()
    row["paper_trade_only"] = True
    row["validation_status"] = "not_validated"
    append_jsonl(paths["signals"], row, int(config.get("storage", {}).get("max_log_rows", 5000)))
    append_csv(paths["signal_csv"], row)


def _record_feature_archive(context: dict[str, Any], symbol: str, paths: dict[str, Path]) -> None:
    """Persist a point-in-time context snapshot without fabricating missing fields."""
    append_jsonl_unbounded(
        paths["feature_archive"],
        {
            "archive_schema": "feature-context-v1",
            "timestamp": context.get("collected_at", utc_now_iso()),
            "symbol": symbol,
            "feature_snapshot": context_feature_snapshot(context),
            "context_coverage": round(context_coverage(context), 4),
            "derivatives": context.get("derivatives", {}),
            "order_book": context.get("order_book", {}),
            "macro": context.get("macro", {}),
            "missingness_policy": "null_and_errors_preserved",
        },
    )


def _parse_timestamp_ms(value: Any) -> int | None:
    try:
        text = str(value).replace("Z", "+00:00")
        return int(datetime.fromisoformat(text).timestamp() * 1000)
    except (TypeError, ValueError, OverflowError):
        return None


def _timeframe_ms(timeframe: str) -> int:
    units = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    text = str(timeframe).strip().lower()
    if len(text) < 2 or text[-1] not in units:
        return 900_000
    try:
        return int(float(text[:-1]) * units[text[-1]])
    except ValueError:
        return 900_000


def _pnl_for_exit(trade: dict[str, Any], exit_price: float) -> tuple[float, float]:
    entry = float(trade["entry"])
    size = float(trade.get("position_size", 0) or 0)
    side = trade["side"]
    pnl = (exit_price - entry) * size if side == "LONG" else (entry - exit_price) * size
    risk_amount = float(trade.get("risk_amount", 0) or 0)
    return pnl, round(pnl / risk_amount, 3) if risk_amount else 0.0


def _close_trade(trade: dict[str, Any], status: str, exit_price: float, reason: str) -> None:
    pnl_amount, result_r = _pnl_for_exit(trade, exit_price)
    trade.update(
        {
            "status": status,
            "exit_price": round(exit_price, 12),
            "closed_at": utc_now_iso(),
            "pnl_amount": round(pnl_amount, 2),
            "result_r": result_r,
            "outcome_reason": reason,
        }
    )


def _update_open_trades(trades: list[dict[str, Any]], exchange, config: dict[str, Any]) -> bool:
    """Close open paper trades using subsequent closed candles, conservatively."""
    changed = False
    paper_cfg = config.get("paper_trading", {})
    timeout_candles = max(1, int(paper_cfg.get("timeout_candles", 8)))
    default_tf = str(config.get("exchange", {}).get("timeframes", {}).get("entry", "15m"))
    for trade in trades:
        if trade.get("status") != "OPEN":
            continue
        try:
            symbol = str(trade["symbol"])
            timeframe = str(trade.get("timeframe", default_tf))
            candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=timeout_candles + 20)
            if len(candles) < 2:
                continue
            opened_ms = _parse_timestamp_ms(trade.get("opened_at")) or 0
            last_checked = int(trade.get("last_checked_candle_ts", 0) or 0)
            holding_count = int(trade.get("holding_candles", 0) or 0)
            stop = float(trade["stop_loss"])
            target = float(trade["take_profit"])
            for candle in candles[:-1]:  # ignore the currently-forming candle
                candle_ts, _open, _high, _low, close, _volume = candle[:6]
                candle_ts = int(candle_ts)
                if candle_ts <= last_checked or candle_ts + _timeframe_ms(timeframe) <= opened_ms:
                    continue
                high = float(_high)
                low = float(_low)
                close = float(close)
                holding_count += 1
                trade["last_checked_candle_ts"] = candle_ts
                trade["holding_candles"] = holding_count
                side = trade["side"]
                hit_tp = high >= target if side == "LONG" else low <= target
                hit_sl = low <= stop if side == "LONG" else high >= stop
                if hit_tp and hit_sl:
                    _close_trade(trade, "SL_HIT", stop, "tp_and_sl_same_candle_conservative_sl_first")
                    changed = True
                    break
                if hit_tp:
                    _close_trade(trade, "TP_HIT", target, "take_profit_touched_on_closed_candle")
                    changed = True
                    break
                if hit_sl:
                    _close_trade(trade, "SL_HIT", stop, "stop_loss_touched_on_closed_candle")
                    changed = True
                    break
                if holding_count >= timeout_candles:
                    _close_trade(trade, "TIMEOUT", close, "maximum_holding_candles_reached")
                    changed = True
                    break
        except Exception as exc:  # one broken symbol must not stop the cycle
            LOGGER.warning("Could not update trade %s: %s", trade.get("signal_id"), exc)
    return changed


def _write_summaries(trades: list[dict[str, Any]], paths: dict[str, Path]) -> None:
    now = datetime.now(timezone.utc)
    daily = now.date().isoformat()
    iso = now.isocalendar()
    weekly = f"{iso.year}-W{iso.week:02d}"
    write_json(paths["performance"], build_performance(trades))
    write_json(paths["daily_summary"], build_period_summary(trades, daily))
    write_json(paths["weekly_summary"], build_period_summary(trades, weekly))


def scan(config_path: str = "config.yaml") -> int:
    config = load_config(config_path)
    paths = _paths(config)
    trades = read_json(paths["trades"], [])
    exchange = make_exchange(config)
    exchange.load_markets()

    try:
        updated = _update_open_trades(trades, exchange, config)
        if updated:
            LOGGER.info("Paper-trade outcome tracker closed one or more candle outcomes")
    except Exception as exc:
        LOGGER.warning("Open-trade update phase failed: %s", exc)

    state = calculate_risk_state(trades, config)
    if state.paused:
        message = format_risk_alert(state.pause_reason, state.to_dict(), config["notifications"]["disclaimer"])
        notify(message, config)
        _write_summaries(trades, paths)
        return 0

    try:
        news = fetch_news(config)
    except Exception as exc:
        LOGGER.warning("News phase failed; continuing without news filter: %s", exc)
        news = []
    symbols = select_symbols(exchange, config)
    try:
        macro_context = fetch_macro_context(config)
    except Exception as exc:
        LOGGER.warning("Macro context phase failed; continuing without macro data: %s", exc)
        macro_context = {"available": False, "source": "macro_bundle", "reason": type(exc).__name__}
    timeframes = config["exchange"]["timeframes"]
    limit = int(config["exchange"].get("candles", 250))
    seen: set[str] = set()
    generated = 0

    for symbol in symbols:
        try:
            frames = {tf: fetch_ohlcv(exchange, symbol, tf, limit) for tf in set(timeframes.values())}
            context = collect_market_context(exchange, symbol, config, macro_context)
            _record_feature_archive(context, symbol, paths)
            signal = generate_signal(symbol, frames, news, config, context)
            if not signal or signal.signal_id in seen:
                continue
            seen.add(signal.signal_id)
            allowed, reason = can_open_signal(signal, trades, state, config)
            if not allowed:
                LOGGER.info("Signal skipped for %s: %s", symbol, reason)
                continue
            trade = signal.to_dict()
            trade.update(
                {
                    "opened_at": signal.created_at,
                    "pnl_amount": 0.0,
                    "equity_after": state.current_balance,
                    "paper_trade_only": True,
                    "validation_status": "not_validated",
                    "holding_candles": 0,
                    "last_checked_candle_ts": 0,
                }
            )
            trades.append(trade)
            _record_signal(signal, paths, config)
            results = notify(format_signal(signal, config["notifications"]["disclaimer"]), config)
            LOGGER.info("Paper signal %s delivered: %s", signal.signal_id, results)
            generated += 1
        except Exception as exc:
            LOGGER.exception("Scan failed for %s; continuing: %s", symbol, exc)

    write_json(paths["trades"], trades[-int(config.get("storage", {}).get("max_log_rows", 5000)):])
    _write_summaries(trades, paths)
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
        _write_summaries(trades, paths)
        print(build_performance(trades))
        return 0
    return scan(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
