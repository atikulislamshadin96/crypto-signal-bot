from __future__ import annotations

from typing import Any

import pandas as pd

from .indicators import add_indicators


def run_backtest(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Simple candle-by-candle ATR strategy replay for sanity checking, not a guarantee of live performance."""
    cfg = config.get("strategy", {})
    data = add_indicators(df, cfg)
    stop_mult = float(cfg.get("atr_stop_multiplier", 1.5))
    target_mult = float(cfg.get("atr_target_multiplier", 3.0))
    trades: list[dict[str, float | str]] = []
    for index in range(1, len(data) - 1):
        row = data.iloc[index]
        side = "LONG" if row["ema_fast"] > row["ema_slow"] and row["macd_hist"] > 0 and row["rsi"] >= 50 else "SHORT" if row["ema_fast"] < row["ema_slow"] and row["macd_hist"] < 0 and row["rsi"] <= 50 else None
        if not side:
            continue
        entry = float(row["close"])
        atr = float(row["atr"])
        stop = entry - atr * stop_mult if side == "LONG" else entry + atr * stop_mult
        target = entry + atr * target_mult if side == "LONG" else entry - atr * target_mult
        result = 0.0
        for future_index in range(index + 1, len(data)):
            future = data.iloc[future_index]
            if side == "LONG" and future["low"] <= stop:
                result = -1.0
                break
            if side == "LONG" and future["high"] >= target:
                result = target_mult / stop_mult
                break
            if side == "SHORT" and future["high"] >= stop:
                result = -1.0
                break
            if side == "SHORT" and future["low"] <= target:
                result = target_mult / stop_mult
                break
        trades.append({"side": side, "result_r": result})
    results = [float(trade["result_r"]) for trade in trades]
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for result in results:
        equity += result
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    wins = sum(result > 0 for result in results)
    return {
        "total_trades": len(results),
        "wins": wins,
        "losses": len(results) - wins,
        "win_rate_pct": round(wins / len(results) * 100, 2) if results else 0.0,
        "average_rr": round(sum(results) / len(results), 3) if results else 0.0,
        "max_drawdown_r": round(max_dd, 3),
        "net_r": round(sum(results), 3),
    }
