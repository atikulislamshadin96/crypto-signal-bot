from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import RiskState, Signal


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_trade_records(path: str) -> list[dict[str, Any]]:
    import json
    from pathlib import Path
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def calculate_risk_state(trades: list[dict[str, Any]], config: dict[str, Any]) -> RiskState:
    risk = config.get("risk", {})
    initial = float(risk.get("initial_balance", 10000))
    current = float(risk.get("current_balance", initial))
    closed = [trade for trade in trades if trade.get("status") in {"TP_HIT", "SL_HIT", "CLOSED"}]
    realized = sum(float(trade.get("pnl_amount", 0) or 0) for trade in closed)
    current = current + realized
    peak = max([initial, current] + [float(t.get("equity_after", initial)) for t in trades if t.get("equity_after") is not None])
    daily = sum(float(t.get("pnl_amount", 0) or 0) for t in closed if str(t.get("closed_at", "")).startswith(_today()))
    daily_loss_pct = max(0.0, -daily / initial * 100) if initial else 0.0
    drawdown_pct = max(0.0, (peak - current) / peak * 100) if peak else 0.0
    daily_limit = float(risk.get("daily_loss_limit_pct", 5.0))
    max_dd = float(risk.get("max_drawdown_pct", 10.0))
    paused = drawdown_pct >= max_dd
    reason = f"Maximum drawdown reached: {drawdown_pct:.2f}% >= {max_dd:.2f}%" if paused else ""
    return RiskState(initial, current, peak, daily, daily_loss_pct, drawdown_pct, paused, reason)


def can_open_signal(signal: Signal, trades: list[dict[str, Any]], state: RiskState, config: dict[str, Any]) -> tuple[bool, str]:
    risk = config.get("risk", {})
    if state.paused:
        return False, state.pause_reason
    if state.daily_loss_pct >= float(risk.get("daily_loss_limit_pct", 5.0)):
        return False, "Daily loss limit reached; new signals are disabled until the next UTC day."
    if float(signal.risk_amount) > state.current_balance * float(risk.get("max_risk_per_trade_pct", 2.0)) / 100:
        return False, "Signal risk exceeds configured per-trade risk cap."
    open_trades = sum(trade.get("status") == "OPEN" for trade in trades)
    if open_trades >= int(risk.get("max_open_trades", 5)):
        return False, "Maximum open-trade limit reached."
    if any(trade.get("signal_id") == signal.signal_id for trade in trades):
        return False, "Duplicate signal already recorded."
    return True, "approved"
