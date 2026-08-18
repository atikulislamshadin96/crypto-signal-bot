"""Research-only strategy candidates.

This module is deliberately not imported by runner.py or the notification path.
The functions create candidate features/labels only; they do not place orders,
write production signals, or claim predictive performance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ResearchCandidate:
    candidate_id: str
    name: str
    rationale: str
    required_data: tuple[str, ...]
    production_enabled: bool = False
    status: str = "not yet tested"


CANDIDATES: tuple[ResearchCandidate, ...] = (
    ResearchCandidate(
        "funding_mean_reversion",
        "Funding-rate mean reversion",
        "Extreme funding or cross-venue funding spreads may normalize, but fees, settlement, borrow, latency and spread reversal can erase the edge.",
        ("funding_rate", "cross_venue_funding", "fees", "execution_cost"),
    ),
    ResearchCandidate(
        "order_flow_imbalance",
        "Denoised multi-level order-flow imbalance",
        "Persistent depth imbalance can proxy short-horizon supply-demand pressure, but flicker quotes, spoofing, latency and adverse selection require strict event-time controls.",
        ("multi_level_order_book", "trades", "spread", "latency"),
    ),
    ResearchCandidate(
        "regime_conditional_momentum",
        "Regime-conditional momentum",
        "Trend continuation may be state-dependent; a conservative candidate is to permit momentum only after persistent broad-market UP states.",
        ("broad_market_returns", "asset_returns", "volatility_regime"),
    ),
    ResearchCandidate(
        "cross_exchange_spread",
        "Cross-exchange spread / arbitrage-adjacent signal",
        "Temporary venue spreads may mean-revert, but transfer, inventory, execution, counterparty and fee risks make this a research hypothesis rather than an arbitrage claim.",
        ("synchronized_venue_prices", "fees", "latency", "inventory"),
    ),
)


def candidate_registry() -> list[dict[str, Any]]:
    """Return a serializable registry with an explicit research-only status."""
    return [asdict(candidate) for candidate in CANDIDATES]


def funding_mean_reversion_feature(
    funding: pd.Series,
    window: int = 96,
    min_periods: int | None = None,
) -> pd.Series:
    """Compute a lagged funding z-score; positive extremes imply a testable fade.

    This is a feature generator only. It does not convert the value into a
    production side or signal.
    """
    if min_periods is None:
        min_periods = min(window, max(20, window // 4))
    mean = funding.rolling(window, min_periods=min_periods).mean().shift(1)
    std = funding.rolling(window, min_periods=min_periods).std(ddof=0).shift(1)
    return (funding - mean) / std.replace(0, np.nan)


def order_book_imbalance_feature(
    bid_qty: pd.Series,
    ask_qty: pd.Series,
    smoothing_window: int = 5,
) -> pd.Series:
    """Compute smoothed depth imbalance in [-1, 1] from point-in-time inputs."""
    denominator = (bid_qty + ask_qty).replace(0, np.nan)
    raw = ((bid_qty - ask_qty) / denominator).clip(-1, 1)
    return raw.rolling(smoothing_window, min_periods=smoothing_window).mean().shift(1)


def regime_conditional_momentum_label(
    asset_returns: pd.Series,
    market_returns: pd.Series,
    lookback: int = 4,
) -> pd.Series:
    """Create an experimental UP-UP gate label without future leakage.

    A value of 1 means the prior two completed market states were UP and the
    asset's lagged return was positive; 0 means the candidate is inactive.
    """
    market_state = market_returns.rolling(lookback, min_periods=lookback).sum().shift(1).gt(0)
    prior_up_up = market_state & market_state.shift(1).fillna(False)
    lagged_asset_return = asset_returns.shift(1)
    return (prior_up_up & lagged_asset_return.gt(0)).astype(int)


def cross_exchange_spread_feature(
    venue_a: pd.Series,
    venue_b: pd.Series,
    window: int = 48,
) -> pd.Series:
    """Return a lagged standardized venue spread for research only."""
    spread = (venue_a - venue_b).replace([np.inf, -np.inf], np.nan)
    mean = spread.rolling(window, min_periods=max(10, window // 4)).mean().shift(1)
    std = spread.rolling(window, min_periods=max(10, window // 4)).std(ddof=0).shift(1)
    return (spread - mean) / std.replace(0, np.nan)
