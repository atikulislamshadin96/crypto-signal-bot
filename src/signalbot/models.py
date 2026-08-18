from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class NewsItem:
    title: str
    url: str
    published_at: str
    source: str
    sentiment: str = "Neutral"
    impact: str = "normal"
    matched_keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Signal:
    signal_id: str
    created_at: str
    symbol: str
    side: str
    timeframe: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: int
    confluence_count: int
    factors: list[str]
    trend: str
    sentiment: str
    news_context: list[str]
    position_size: float
    risk_amount: float
    fusion_score: float = 0.0
    fusion_probability: float = 0.0
    context_coverage: float = 0.0
    feature_snapshot: dict[str, Any] = field(default_factory=dict)
    data_sources: dict[str, Any] = field(default_factory=dict)
    status: str = "OPEN"
    result_r: float | None = None
    closed_at: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskState:
    initial_balance: float
    current_balance: float
    equity_peak: float
    daily_realized_pnl: float
    daily_loss_pct: float
    drawdown_pct: float
    paused: bool
    pause_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
