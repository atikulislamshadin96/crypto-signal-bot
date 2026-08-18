from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    data = df.copy()
    fast = int(cfg.get("ema_fast", 50))
    slow = int(cfg.get("ema_slow", 200))
    rsi_period = int(cfg.get("rsi_period", 14))
    atr_period = int(cfg.get("atr_period", 14))
    volume_window = int(cfg.get("volume_window", 20))

    data["ema_fast"] = data["close"].ewm(span=fast, adjust=False).mean()
    data["ema_slow"] = data["close"].ewm(span=slow, adjust=False).mean()
    delta = data["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / rsi_period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / rsi_period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    data["rsi"] = (100 - (100 / (1 + rs))).fillna(50)

    ema12 = data["close"].ewm(span=12, adjust=False).mean()
    ema26 = data["close"].ewm(span=26, adjust=False).mean()
    data["macd"] = ema12 - ema26
    data["macd_signal"] = data["macd"].ewm(span=9, adjust=False).mean()
    data["macd_hist"] = data["macd"] - data["macd_signal"]

    previous_close = data["close"].shift(1)
    true_range = pd.concat(
        [data["high"] - data["low"], (data["high"] - previous_close).abs(), (data["low"] - previous_close).abs()], axis=1
    ).max(axis=1)
    data["atr"] = true_range.ewm(alpha=1 / atr_period, adjust=False).mean()
    data["volume_mean"] = data["volume"].rolling(volume_window).mean()
    data["volume_ratio"] = data["volume"] / data["volume_mean"].replace(0, np.nan)
    data["high_20"] = data["high"].rolling(20).max().shift(1)
    data["low_20"] = data["low"].rolling(20).min().shift(1)
    # Preserve the original candle index so signal IDs change when a new candle arrives.
    return data.dropna()
