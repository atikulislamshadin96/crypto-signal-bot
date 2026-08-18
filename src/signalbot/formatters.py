from __future__ import annotations

from .models import Signal


def format_signal(signal: Signal, disclaimer: str) -> str:
    factors = ", ".join(signal.factors)
    news = " | ".join(signal.news_context) if signal.news_context else "No relevant high-impact news"
    return (
        f"🚨 CRYPTO SIGNAL — {signal.side}\n"
        f"Symbol: {signal.symbol}\n"
        f"Timeframe: {signal.timeframe}\n"
        f"Entry: {signal.entry}\n"
        f"Stop Loss: {signal.stop_loss}\n"
        f"Take Profit: {signal.take_profit}\n"
        f"Risk:Reward: 1:{signal.risk_reward}\n"
        f"Confidence: {signal.confidence}/100\n"
        f"Confluence ({signal.confluence_count}): {factors}\n"
        f"Trend: {signal.trend} | News sentiment: {signal.sentiment}\n"
        f"Position size (units): {signal.position_size}\n"
        f"Risk amount: {signal.risk_amount}\n"
        f"News context: {news}\n\n"
        f"Disclaimer: {disclaimer}"
    )


def format_risk_alert(reason: str, state: dict, disclaimer: str) -> str:
    return (
        "⚠️ RISK GUARD ACTIVATED\n"
        f"Reason: {reason}\n"
        f"Daily realized PnL: {state.get('daily_realized_pnl', 0):.2f}\n"
        f"Daily loss: {state.get('daily_loss_pct', 0):.2f}%\n"
        f"Drawdown: {state.get('drawdown_pct', 0):.2f}%\n\n"
        f"Disclaimer: {disclaimer}"
    )
