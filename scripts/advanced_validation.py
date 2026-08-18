from __future__ import annotations

import json
import logging
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

from signalbot.config import load_config
from signalbot.indicators import add_indicators
from signalbot.market import make_exchange
from validation_analysis import evaluate_split, fetch_history

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(42)


def percentile(values: list[float] | np.ndarray, q: float) -> float | None:
    return round(float(np.percentile(values, q)), 4) if len(values) else None


def bootstrap_metrics(trades: list[dict]) -> dict:
    r = np.array([float(t["result_r"]) for t in trades], dtype=float)
    wins = np.array([int(t["outcome"] == "TP_HIT") for t in trades], dtype=float)
    if len(r) == 0:
        return {"trades": 0, "win_rate_ci_95_pct": None, "net_r_ci_95": None}
    win_rates: list[float] = []
    net_rs: list[float] = []
    for _ in range(10000):
        sample = RNG.integers(0, len(r), len(r))
        win_rates.append(float(wins[sample].mean() * 100))
        net_rs.append(float(r[sample].sum()))
    return {"trades": int(len(r)), "bootstrap_iterations": 10000, "seed": 42, "win_rate_ci_95_pct": [percentile(win_rates, 2.5), percentile(win_rates, 97.5)], "net_r_ci_95": [percentile(net_rs, 2.5), percentile(net_rs, 97.5)]}


def max_drawdown(sequence: np.ndarray) -> float:
    equity = np.cumsum(sequence)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    return float(np.max(peaks[1:] - equity)) if len(equity) else 0.0


def max_loss_streak(sequence: np.ndarray) -> int:
    current = best = 0
    for value in sequence:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def monte_carlo(trades: list[dict]) -> dict:
    r = np.array([float(t["result_r"]) for t in trades], dtype=float)
    if len(r) == 0:
        return {"trades": 0, "iterations": 0, "max_drawdown_r_p95": None, "max_loss_streak_p95": None}
    dds: list[float] = []
    streaks: list[int] = []
    for _ in range(10000):
        shuffled = RNG.permutation(r)
        dds.append(max_drawdown(shuffled))
        streaks.append(max_loss_streak(shuffled))
    return {"trades": int(len(r)), "iterations": 10000, "seed": 42, "historical_max_drawdown_r": round(max_drawdown(r), 4), "max_drawdown_r_p50": percentile(dds, 50), "max_drawdown_r_p95": percentile(dds, 95), "max_loss_streak_p50": percentile(streaks, 50), "max_loss_streak_p95": percentile(streaks, 95)}


def data_audit(frame: pd.DataFrame, timeframe_minutes: int) -> dict:
    if frame.empty:
        return {"rows": 0, "missing_candles": None, "outlier_count": None}
    expected = int((frame.index[-1] - frame.index[0]).total_seconds() / 60 / timeframe_minutes) + 1
    returns = frame["close"].pct_change().dropna().abs()
    median_abs = float(returns.median()) if not returns.empty else 0.0
    threshold = max(median_abs * 10, 0.05)
    return {"rows": int(len(frame)), "expected_rows_by_time_span": expected, "missing_candles": max(expected - len(frame), 0), "first_utc": frame.index[0].isoformat(), "last_utc": frame.index[-1].isoformat(), "outlier_threshold_abs_return": round(threshold, 6), "outlier_count": int((returns > threshold).sum())}


def classify_regime(frame: pd.DataFrame) -> dict:
    if len(frame) < 200:
        return {"status": "not enough rows"}
    close = frame["close"]
    fast = close.ewm(span=50, adjust=False).mean()
    slow = close.ewm(span=200, adjust=False).mean()
    realized = close.pct_change().rolling(96).std() * math.sqrt(96)
    usable = pd.DataFrame({"trend": (fast - slow).abs() / close, "vol": realized}).dropna()
    if usable.empty:
        return {"status": "not enough indicators"}
    trend_threshold = float(usable["trend"].median())
    vol_threshold = float(usable["vol"].median())
    counts = {"trending_high_vol": 0, "trending_low_vol": 0, "ranging_high_vol": 0, "ranging_low_vol": 0}
    for _, row in usable.iterrows():
        trending = row["trend"] >= trend_threshold
        high_vol = row["vol"] >= vol_threshold
        key = ("trending" if trending else "ranging") + ("_high_vol" if high_vol else "_low_vol")
        counts[key] += 1
    total = len(usable)
    return {"method": "15m absolute EMA(50)-EMA(200) spread and 96-bar realized volatility, each split at its sample median", "trend_median": round(trend_threshold, 6), "vol_median": round(vol_threshold, 6), "rows_classified": int(total), "counts": counts, "shares_pct": {k: round(v / total * 100, 2) for k, v in counts.items()}}


def cross_exchange_audit(symbol: str, start: datetime, end: datetime) -> dict:
    exchanges = {"binance": ccxt.binance({"enableRateLimit": True}), "kraken": ccxt.kraken({"enableRateLimit": True})}
    frames: dict[str, pd.DataFrame] = {}
    for name, exchange in exchanges.items():
        try:
            exchange.load_markets()
            market_symbol = symbol if symbol in exchange.markets else symbol.replace("/USDT", "/USD")
            if market_symbol not in exchange.markets:
                frames[name] = pd.DataFrame()
                continue
            frames[name] = fetch_history(exchange, market_symbol, "1h", start, end)
        except Exception as exc:  # explicit evidence of availability, not a silent fallback
            LOGGER.warning("%s cross-exchange fetch failed: %s", name, exc)
            frames[name] = pd.DataFrame()
    if any(frame.empty for frame in frames.values()):
        return {"symbol": symbol, "status": "not tested — one or more exchange datasets unavailable", "rows": {name: int(len(frame)) for name, frame in frames.items()}}
    a = frames["binance"]["close"].pct_change().rename("binance")
    b = frames["kraken"]["close"].pct_change().rename("kraken")
    aligned = pd.concat([a, b], axis=1).dropna()
    spread = (frames["binance"]["close"].reindex(aligned.index) / frames["kraken"]["close"].reindex(aligned.index) - 1).abs()
    return {"symbol": symbol, "status": "tested", "rows": {name: int(len(frame)) for name, frame in frames.items()}, "aligned_return_rows": int(len(aligned)), "return_correlation": round(float(aligned.corr().iloc[0, 1]), 6), "absolute_close_spread_median_pct": round(float(spread.median() * 100), 4), "absolute_close_spread_p95_pct": round(float(spread.quantile(0.95) * 100), 4)}


def summarize_walk_forward(indicators: dict, cfg: dict, start: pd.Timestamp, end: pd.Timestamp) -> list[dict]:
    windows: list[dict] = []
    total_days = (end - start).days
    window_days = max(7, total_days // 4)
    for i in range(4):
        w_start = start + pd.Timedelta(days=i * window_days)
        w_end = min(end, w_start + pd.Timedelta(days=window_days) - pd.Timedelta(minutes=15))
        trades, metrics, _ = evaluate_split(indicators["15m"], indicators["1h"], indicators["4h"], w_start, w_end, cfg)
        windows.append({"window": i + 1, "start_utc": w_start.isoformat(), "end_utc": w_end.isoformat(), "trades": metrics["trades"], "wins": metrics["wins"], "losses": metrics["losses"], "win_rate_pct_all_signals": metrics["win_rate_pct_all_signals"], "net_r": metrics["net_r"], "max_drawdown_r": metrics["max_drawdown_r"], "note": "fixed parameters; this is a stability check, not a tuned walk-forward optimizer"})
    return windows


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(ROOT / "config.yaml")
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end -= timedelta(minutes=end.minute % 15)
    start = end - timedelta(days=90)
    warmup = start - timedelta(days=60)
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
    exchange = make_exchange(cfg)
    exchange.load_markets()
    per_symbol: dict[str, dict] = {}
    all_oos_trades: list[dict] = []
    for symbol in symbols:
        LOGGER.info("advanced fetch %s", symbol)
        frames = {tf: fetch_history(exchange, symbol, tf, warmup, end) for tf in ["15m", "1h", "4h"]}
        if any(frame.empty for frame in frames.values()):
            per_symbol[symbol] = {"status": "not tested — missing Binance timeframe data"}
            continue
        indicators = {tf: add_indicators(frame, cfg["strategy"]) for tf, frame in frames.items()}
        oos_start = pd.Timestamp(start + timedelta(days=60))
        oos_end = pd.Timestamp(end - timedelta(minutes=15))
        trades, metrics, analysis = evaluate_split(indicators["15m"], indicators["1h"], indicators["4h"], oos_start, oos_end, cfg)
        for trade in trades:
            trade["symbol"] = symbol
        all_oos_trades.extend(trades)
        per_symbol[symbol] = {"status": "tested", "data_audit_15m": data_audit(frames["15m"].loc[start:end], 15), "regime_15m": classify_regime(frames["15m"].loc[start:end]), "walk_forward_fixed_parameter": summarize_walk_forward(indicators, cfg, pd.Timestamp(start), pd.Timestamp(end)), "oos_metrics": metrics, "oos_analysis": analysis}
    returns: dict[str, pd.Series] = {}
    for symbol in symbols:
        # Reuse the exchange fetches only for a compact 1h correlation audit.
        frame = fetch_history(exchange, symbol, "1h", start, end)
        if not frame.empty:
            returns[symbol] = frame["close"].pct_change()
    corr = pd.DataFrame(returns).corr()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool)).stack()
    correlation_summary = {"status": "tested", "matrix": corr.round(6).to_dict(), "pairwise_mean": round(float(upper.mean()), 6) if not upper.empty else None, "pairwise_min": round(float(upper.min()), 6) if not upper.empty else None, "pairwise_max": round(float(upper.max()), 6) if not upper.empty else None}
    cross_exchange = [cross_exchange_audit(symbol, start, end) for symbol in ["BTC/USDT", "ETH/USDT"]]
    boot = bootstrap_metrics(all_oos_trades)
    mc = monte_carlo(all_oos_trades)
    result = {"as_of_utc": end.isoformat(), "method": {"window_days": 90, "symbols": symbols, "parameters_frozen": True, "walk_forward_windows": 4, "bootstrap_iterations": 10000, "monte_carlo_iterations": 10000, "fees_slippage_funding": False}, "per_symbol": per_symbol, "aggregate_oos": {"trades": len(all_oos_trades), "wins": sum(t["outcome"] == "TP_HIT" for t in all_oos_trades), "losses": sum(t["outcome"] == "SL_HIT" for t in all_oos_trades), "net_r": round(sum(float(t["result_r"]) for t in all_oos_trades), 4)}, "bootstrap": boot, "monte_carlo": mc, "correlation": correlation_summary, "cross_exchange": cross_exchange, "ablation": {"status": "not tested — current validation harness has no one-factor-at-a-time rule toggle"}, "microstructure": {"status": "not tested — no historical order-book, funding-rate or open-interest data in the repository"}, "paper_protocol": {"status": "not started — no live/paper records found", "required_minimum": "4–8 weeks and 30–50 closed trades after parameter freeze"}}
    (ROOT / "advanced_validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"as_of_utc": result["as_of_utc"], "aggregate_oos": result["aggregate_oos"], "bootstrap": result["bootstrap"], "monte_carlo": result["monte_carlo"], "correlation": result["correlation"], "cross_exchange": result["cross_exchange"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
