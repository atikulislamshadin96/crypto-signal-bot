from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd

from .indicators import add_indicators
from .models import NewsItem, Signal, utc_now_iso
from .news import news_filter


def _signal_id(symbol: str, side: str, candle_time: str) -> str:
    raw = f"{symbol}|{side}|{candle_time}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def generate_signal(symbol: str, frames: dict[str, pd.DataFrame], news: list[NewsItem], config: dict[str, Any]) -> Signal | None:
    strategy_cfg = config.get("strategy", {})
    risk_cfg = config.get("risk", {})
    entry_tf = config.get("exchange", {}).get("timeframes", {}).get("entry", "15m")
    confirmation_tf = config.get("exchange", {}).get("timeframes", {}).get("confirmation", "1h")
    bias_tf = config.get("exchange", {}).get("timeframes", {}).get("bias", "4h")

    if entry_tf not in frames or confirmation_tf not in frames or bias_tf not in frames:
        return None
    entry = add_indicators(frames[entry_tf], strategy_cfg)
    confirmation = add_indicators(frames[confirmation_tf], strategy_cfg)
    bias = add_indicators(frames[bias_tf], strategy_cfg)
    if len(entry) < 3 or len(confirmation) < 2 or len(bias) < 2:
        return None

    e = entry.iloc[-1]
    c = confirmation.iloc[-1]
    b = bias.iloc[-1]
    long_factors: list[str] = []
    short_factors: list[str] = []
    if b["ema_fast"] > b["ema_slow"] and c["close"] > c["ema_fast"]:
        long_factors.append("higher-timeframe uptrend")
    if b["ema_fast"] < b["ema_slow"] and c["close"] < c["ema_fast"]:
        short_factors.append("higher-timeframe downtrend")
    if e["rsi"] >= 50 and e["rsi"] <= 70 and e["macd_hist"] > 0:
        long_factors.append("positive RSI/MACD momentum")
    if e["rsi"] >= 30 and e["rsi"] <= 50 and e["macd_hist"] < 0:
        short_factors.append("negative RSI/MACD momentum")
    if e["volume_ratio"] >= float(strategy_cfg.get("volume_spike_multiplier", 1.2)):
        if e["close"] >= e["open"]:
            long_factors.append("volume confirmation")
        if e["close"] <= e["open"]:
            short_factors.append("volume confirmation")
    if pd.notna(e["high_20"]) and e["close"] > e["high_20"]:
        long_factors.append("20-candle breakout")
    if pd.notna(e["low_20"]) and e["close"] < e["low_20"]:
        short_factors.append("20-candle breakdown")

    candidates = [("LONG", long_factors), ("SHORT", short_factors)]
    side, factors = max(candidates, key=lambda item: len(item[1]))
    min_confluence = int(strategy_cfg.get("min_confluence", 4))
    if len(factors) < min_confluence:
        return None

    blocked, context, sentiment = news_filter(symbol, side, news, config)
    if blocked:
        return None

    price = float(e["close"])
    atr = float(e["atr"])
    if not price > 0 or not atr > 0:
        return None
    stop_mult = float(strategy_cfg.get("atr_stop_multiplier", 1.5))
    target_mult = float(strategy_cfg.get("atr_target_multiplier", 3.0))
    if side == "LONG":
        stop_loss = price - atr * stop_mult
        take_profit = price + atr * target_mult
        trend = "BULLISH"
    else:
        stop_loss = price + atr * stop_mult
        take_profit = price - atr * target_mult
        trend = "BEARISH"
    distance = abs(price - stop_loss)
    risk_amount = float(risk_cfg.get("current_balance", 10000)) * float(risk_cfg.get("risk_per_trade_pct", 1.0)) / 100
    position_size = risk_amount / distance if distance else 0.0
    confidence = min(100, int(50 + len(factors) * 10 + (5 if sentiment == "Neutral" else 0)))
    if confidence < int(strategy_cfg.get("min_confidence", 65)):
        return None
    candle_time = str(entry.index[-1])
    return Signal(
        signal_id=_signal_id(symbol, side, candle_time),
        created_at=utc_now_iso(),
        symbol=symbol,
        side=side,
        timeframe=entry_tf,
        entry=round(price, 8),
        stop_loss=round(stop_loss, 8),
        take_profit=round(take_profit, 8),
        risk_reward=round(abs(take_profit - price) / distance, 2),
        confidence=confidence,
        confluence_count=len(factors),
        factors=factors,
        trend=trend,
        sentiment=sentiment,
        news_context=context,
        position_size=round(position_size, 8),
        risk_amount=round(risk_amount, 2),
    )
