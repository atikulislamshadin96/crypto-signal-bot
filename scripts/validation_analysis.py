from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from signalbot.config import load_config
from signalbot.indicators import add_indicators
from signalbot.market import make_exchange

LOGGER = logging.getLogger(__name__)


def fetch_history(exchange: Any, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    cursor = start_ms
    rows: list[list[float]] = []
    while cursor < end_ms:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=1000)
        if not batch:
            break
        rows.extend(batch)
        last_ms = int(batch[-1][0])
        next_cursor = last_ms + 1
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if last_ms >= end_ms or len(batch) < 1000:
            break
        time.sleep(max(float(getattr(exchange, "rateLimit", 100)), 100) / 1000)
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], index=pd.DatetimeIndex([], tz="UTC"))
    frame = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
    frame = frame.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    frame = frame.loc[(frame.index >= start) & (frame.index <= end)]
    return frame.astype(float)


def aligned_row(frame: pd.DataFrame, timestamp: pd.Timestamp) -> pd.Series | None:
    position = frame.index.searchsorted(timestamp, side="right") - 1
    return frame.iloc[position] if position >= 0 else None


def evaluate_split(entry: pd.DataFrame, confirmation: pd.DataFrame, bias: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, cfg: dict[str, Any], horizon_bars: int = 96) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    strategy_cfg = cfg.get("strategy", {})
    min_confluence = int(strategy_cfg.get("min_confluence", 4))
    min_confidence = int(strategy_cfg.get("min_confidence", 65))
    volume_threshold = float(strategy_cfg.get("volume_spike_multiplier", 1.2))
    stop_mult = float(strategy_cfg.get("atr_stop_multiplier", 1.5))
    target_mult = float(strategy_cfg.get("atr_target_multiplier", 3.0))
    entry = entry.loc[(entry.index >= start) & (entry.index <= end)]
    trades: list[dict[str, Any]] = []
    factors: dict[str, dict[str, int]] = {}
    bins: dict[str, dict[str, int]] = {"65-69": {"trades": 0, "wins": 0}, "70-79": {"trades": 0, "wins": 0}, "80-89": {"trades": 0, "wins": 0}, "90-100": {"trades": 0, "wins": 0}}
    last_entry_time: pd.Timestamp | None = None

    for timestamp, row in entry.iterrows():
        if last_entry_time is not None and timestamp <= last_entry_time:
            continue
        c = aligned_row(confirmation, timestamp)
        b = aligned_row(bias, timestamp)
        if c is None or b is None or float(row.get("atr", 0)) <= 0:
            continue
        long_factors: list[str] = []
        short_factors: list[str] = []
        if b["ema_fast"] > b["ema_slow"] and c["close"] > c["ema_fast"]:
            long_factors.append("higher-timeframe uptrend")
        if b["ema_fast"] < b["ema_slow"] and c["close"] < c["ema_fast"]:
            short_factors.append("higher-timeframe downtrend")
        if 50 <= row["rsi"] <= 70 and row["macd_hist"] > 0:
            long_factors.append("positive RSI/MACD momentum")
        if 30 <= row["rsi"] <= 50 and row["macd_hist"] < 0:
            short_factors.append("negative RSI/MACD momentum")
        if row["volume_ratio"] >= volume_threshold:
            if row["close"] >= row["open"]:
                long_factors.append("volume confirmation")
            if row["close"] <= row["open"]:
                short_factors.append("volume confirmation")
        if pd.notna(row["high_20"]) and row["close"] > row["high_20"]:
            long_factors.append("20-candle breakout")
        if pd.notna(row["low_20"]) and row["close"] < row["low_20"]:
            short_factors.append("20-candle breakdown")
        side, chosen = max([("LONG", long_factors), ("SHORT", short_factors)], key=lambda item: len(item[1]))
        if len(chosen) < min_confluence:
            continue
        confidence = min(100, int(50 + len(chosen) * 10))
        if confidence < min_confidence:
            continue
        price = float(row["close"])
        atr = float(row["atr"])
        stop = price - atr * stop_mult if side == "LONG" else price + atr * stop_mult
        target = price + atr * target_mult if side == "LONG" else price - atr * target_mult
        future = entry.loc[entry.index > timestamp].head(horizon_bars)
        outcome = "TIMEOUT"
        result_r = 0.0
        for _, candle in future.iterrows():
            stop_hit = candle["low"] <= stop if side == "LONG" else candle["high"] >= stop
            target_hit = candle["high"] >= target if side == "LONG" else candle["low"] <= target
            if stop_hit:
                outcome, result_r = "SL_HIT", -1.0
                break
            if target_hit:
                outcome, result_r = "TP_HIT", target_mult / stop_mult
                break
        trade = {"timestamp": timestamp.isoformat(), "side": side, "confidence": confidence, "factors": chosen, "outcome": outcome, "result_r": result_r}
        trades.append(trade)
        last_entry_time = timestamp
        bucket = "65-69" if confidence < 70 else "70-79" if confidence < 80 else "80-89" if confidence < 90 else "90-100"
        bins[bucket]["trades"] += 1
        bins[bucket]["wins"] += int(outcome == "TP_HIT")
        for factor in chosen:
            stats = factors.setdefault(factor, {"trades": 0, "wins": 0})
            stats["trades"] += 1
            stats["wins"] += int(outcome == "TP_HIT")

    wins = sum(trade["outcome"] == "TP_HIT" for trade in trades)
    closed = sum(trade["outcome"] in {"TP_HIT", "SL_HIT"} for trade in trades)
    equity = peak = 0.0
    max_drawdown = 0.0
    for trade in trades:
        equity += float(trade["result_r"])
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    metrics = {
        "trades": len(trades),
        "closed_trades": closed,
        "wins": wins,
        "losses": sum(trade["outcome"] == "SL_HIT" for trade in trades),
        "timeouts": sum(trade["outcome"] == "TIMEOUT" for trade in trades),
        "win_rate_pct_closed_only": round(wins / closed * 100, 2) if closed else None,
        "win_rate_pct_all_signals": round(wins / len(trades) * 100, 2) if trades else None,
        "average_result_r_all_signals": round(sum(float(t["result_r"]) for t in trades) / len(trades), 3) if trades else None,
        "net_r": round(sum(float(t["result_r"]) for t in trades), 3),
        "max_drawdown_r": round(max_drawdown, 3),
        "horizon_bars": horizon_bars,
    }
    factor_metrics = {name: {**stats, "win_rate_pct": round(stats["wins"] / stats["trades"] * 100, 2) if stats["trades"] else None, "share_of_signals_pct": round(stats["trades"] / len(trades) * 100, 2) if trades else 0.0} for name, stats in factors.items()}
    confidence_metrics = {bucket: {**stats, "win_rate_pct_all_signals": round(stats["wins"] / stats["trades"] * 100, 2) if stats["trades"] else None} for bucket, stats in bins.items()}
    return trades, metrics, {"factor_contribution": factor_metrics, "confidence_buckets": confidence_metrics}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "config.yaml")
    exchange = make_exchange(cfg)
    exchange.load_markets()
    end_dt = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end_dt -= timedelta(minutes=end_dt.minute % 15)
    evaluation_start = end_dt - timedelta(days=60)
    split_dt = evaluation_start + timedelta(days=42)
    warmup_start = evaluation_start - timedelta(days=60)
    symbols = cfg["exchange"]["symbols"][:5]
    timeframes = cfg["exchange"]["timeframes"]
    all_results: dict[str, Any] = {"as_of_utc": end_dt.isoformat(), "symbols": symbols, "evaluation_start_utc": evaluation_start.isoformat(), "split_utc": split_dt.isoformat(), "evaluation_end_utc": end_dt.isoformat(), "data_source": "Binance public OHLCV via CCXT", "methodology": {"entry_timeframe": timeframes["entry"], "confirmation_timeframe": timeframes["confirmation"], "bias_timeframe": timeframes["bias"], "horizon_bars": 96, "news_in_backtest": False, "fees_slippage": False}}
    combined_trades: dict[str, list[dict[str, Any]]] = {"in_sample": [], "out_of_sample": []}
    combined_metrics: dict[str, dict[str, Any]] = {}
    combined_analysis: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        LOGGER.info("Fetching %s", symbol)
        frames: dict[str, pd.DataFrame] = {}
        for timeframe in set(timeframes.values()):
            frames[timeframe] = fetch_history(exchange, symbol, timeframe, warmup_start, end_dt)
        if any(frame.empty for frame in frames.values()):
            LOGGER.warning("Skipping %s because at least one timeframe is empty", symbol)
            continue
        indicators = {timeframe: add_indicators(frame, cfg["strategy"]) for timeframe, frame in frames.items()}
        entry_tf = timeframes["entry"]
        in_trades, in_metrics, in_analysis = evaluate_split(indicators[entry_tf], indicators[timeframes["confirmation"]], indicators[timeframes["bias"]], pd.Timestamp(evaluation_start), pd.Timestamp(split_dt - timedelta(minutes=15)), cfg)
        out_trades, out_metrics, out_analysis = evaluate_split(indicators[entry_tf], indicators[timeframes["confirmation"]], indicators[timeframes["bias"]], pd.Timestamp(split_dt), pd.Timestamp(end_dt - timedelta(minutes=15)), cfg)
        for trade in in_trades:
            trade["symbol"] = symbol
        for trade in out_trades:
            trade["symbol"] = symbol
        combined_trades["in_sample"].extend(in_trades)
        combined_trades["out_of_sample"].extend(out_trades)
        LOGGER.info("%s in-sample=%s out-of-sample=%s", symbol, in_metrics["trades"], out_metrics["trades"])

    for split, trades in combined_trades.items():
        wins = sum(t["outcome"] == "TP_HIT" for t in trades)
        closed = sum(t["outcome"] in {"TP_HIT", "SL_HIT"} for t in trades)
        equity = peak = max_dd = 0.0
        for trade in trades:
            equity += float(trade["result_r"])
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        combined_metrics[split] = {"trades": len(trades), "closed_trades": closed, "wins": wins, "losses": sum(t["outcome"] == "SL_HIT" for t in trades), "timeouts": sum(t["outcome"] == "TIMEOUT" for t in trades), "win_rate_pct_closed_only": round(wins / closed * 100, 2) if closed else None, "win_rate_pct_all_signals": round(wins / len(trades) * 100, 2) if trades else None, "net_r": round(sum(float(t["result_r"]) for t in trades), 3), "average_result_r_all_signals": round(sum(float(t["result_r"]) for t in trades) / len(trades), 3) if trades else None, "max_drawdown_r": round(max_dd, 3), "horizon_bars": 96}
        factor_summary: dict[str, dict[str, int]] = {}
        confidence_summary: dict[str, dict[str, int]] = {"65-69": {"trades": 0, "wins": 0}, "70-79": {"trades": 0, "wins": 0}, "80-89": {"trades": 0, "wins": 0}, "90-100": {"trades": 0, "wins": 0}}
        for trade in trades:
            for factor in trade["factors"]:
                factor_summary.setdefault(factor, {"trades": 0, "wins": 0})["trades"] += 1
                factor_summary[factor]["wins"] += int(trade["outcome"] == "TP_HIT")
            confidence = int(trade["confidence"])
            bucket = "65-69" if confidence < 70 else "70-79" if confidence < 80 else "80-89" if confidence < 90 else "90-100"
            confidence_summary[bucket]["trades"] += 1
            confidence_summary[bucket]["wins"] += int(trade["outcome"] == "TP_HIT")
        combined_analysis[split] = {"factor_contribution": {factor: {**stats, "win_rate_pct_all_signals": round(stats["wins"] / stats["trades"] * 100, 2) if stats["trades"] else None} for factor, stats in factor_summary.items()}, "confidence_buckets": {bucket: {**stats, "win_rate_pct_all_signals": round(stats["wins"] / stats["trades"] * 100, 2) if stats["trades"] else None} for bucket, stats in confidence_summary.items()}}
    forward_log = {"records_found": 0, "status": "No data/trades.json or data/signals.jsonl records were present before validation.", "note": "A live forward test cannot be inferred from code, backtest candles or notification configuration."}
    output = {**all_results, "metrics": combined_metrics, "analysis": combined_analysis, "forward_test": forward_log, "sample_trades": {split: trades[:10] for split, trades in combined_trades.items()}}
    (root / "validation_analysis.json").write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"as_of_utc": output["as_of_utc"], "metrics": combined_metrics, "forward_test": forward_log}, indent=2))


if __name__ == "__main__":
    main()
