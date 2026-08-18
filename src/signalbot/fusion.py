from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .context import context_feature_snapshot, context_coverage

FEATURE_NAMES = [
    "funding_contrarian",
    "open_interest_change",
    "long_short_contrarian",
    "order_book_imbalance",
    "spread_quality",
    "liquidity_wall_support",
    "btc_dominance_context",
    "market_cap_change",
    "stablecoin_supply_change",
    "dxy_risk_context",
]


def _clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _safe(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def build_context_features(context: dict[str, Any], side: str, symbol: str = "") -> dict[str, float]:
    """Return side-relative, bounded context features; missing values remain neutral."""
    raw = context_feature_snapshot(context)
    direction = 1.0 if side.upper() == "LONG" else -1.0
    funding = _safe(raw.get("funding_rate"))
    oi_change = _safe(raw.get("open_interest_change_pct"))
    long_short = _safe(raw.get("long_short_ratio"), 1.0)
    imbalance = _safe(raw.get("order_book_imbalance"))
    spread = _safe(raw.get("spread_bps"))
    bid_wall = _safe(raw.get("bid_wall_ratio"), 1.0)
    ask_wall = _safe(raw.get("ask_wall_ratio"), 1.0)
    dominance = _safe(raw.get("btc_dominance"))
    market_change = _safe(raw.get("market_cap_change_24h_pct"))
    stable_change = _safe(raw.get("stablecoin_supply_change_7d_pct"))
    dxy_change = _safe(raw.get("dxy_change_pct"))

    # These transforms are intentionally transparent heuristics. They are not
    # claimed to be trained alpha until an offline labelled model is supplied.
    features = {
        "funding_contrarian": _clip(-direction * funding / 0.0005),
        "open_interest_change": _clip(direction * oi_change / 5.0),
        "long_short_contrarian": _clip(-direction * (long_short - 1.0) / 0.5),
        "order_book_imbalance": _clip(direction * imbalance),
        "spread_quality": _clip(1.0 - max(0.0, spread - 3.0) / 20.0),
        "liquidity_wall_support": _clip(direction * (bid_wall - ask_wall) / 3.0),
        "btc_dominance_context": _clip(direction * (dominance - 50.0) / 10.0) if symbol.upper().startswith("BTC") else _clip(-direction * (dominance - 50.0) / 10.0),
        "market_cap_change": _clip(direction * market_change / 5.0),
        "stablecoin_supply_change": _clip(direction * stable_change / 2.0),
        "dxy_risk_context": _clip(-direction * dxy_change / 1.0),
    }
    return features


@dataclass
class FusionResult:
    score: float
    probability: float
    coverage: float
    contributions: dict[str, float]
    features: dict[str, float]
    model_source: str
    eligible: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 6),
            "probability": round(self.probability, 6),
            "coverage": round(self.coverage, 6),
            "contributions": {key: round(value, 6) for key, value in self.contributions.items()},
            "features": {key: round(value, 6) for key, value in self.features.items()},
            "model_source": self.model_source,
            "eligible": self.eligible,
            "reason": self.reason,
        }


def _sigmoid(value: float) -> float:
    value = max(-30.0, min(30.0, value))
    return 1.0 / (1.0 + np.exp(-value))


def score_context(context: dict[str, Any], side: str, config: dict[str, Any], symbol: str = "") -> FusionResult:
    cfg = config.get("fusion", {})
    features = build_context_features(context, side, symbol)
    coverage = context_coverage(context)
    weights = cfg.get("weights", {})
    layer_weights = {
        "funding_contrarian": float(weights.get("derivatives", 0.35)) * 0.40,
        "open_interest_change": float(weights.get("derivatives", 0.35)) * 0.30,
        "long_short_contrarian": float(weights.get("derivatives", 0.35)) * 0.30,
        "order_book_imbalance": float(weights.get("order_book", 0.35)) * 0.45,
        "spread_quality": float(weights.get("order_book", 0.35)) * 0.20,
        "liquidity_wall_support": float(weights.get("order_book", 0.35)) * 0.35,
        "btc_dominance_context": float(weights.get("macro", 0.30)) * 0.25,
        "market_cap_change": float(weights.get("macro", 0.30)) * 0.30,
        "stablecoin_supply_change": float(weights.get("macro", 0.30)) * 0.25,
        "dxy_risk_context": float(weights.get("macro", 0.30)) * 0.20,
    }
    contributions = {name: features[name] * layer_weights[name] for name in FEATURE_NAMES}
    score = sum(contributions.values()) / max(sum(layer_weights.values()), 1e-9)
    probability = _sigmoid(float(cfg.get("model_intercept", 0.0)) + score * float(cfg.get("model_scale", 2.0)))
    min_coverage = float(cfg.get("min_feature_coverage", 0.5))
    min_score = float(cfg.get("min_score", 0.15))
    eligible = bool(cfg.get("enabled", True)) and coverage >= min_coverage and score >= min_score
    reason = "" if eligible else ("insufficient_context_coverage" if coverage < min_coverage else "fusion_score_below_threshold")
    return FusionResult(score, probability, coverage, contributions, features, "heuristic_untrained", eligible, reason)


def fit_logistic_model(X: np.ndarray, y: np.ndarray, l2: float = 1.0, steps: int = 2000, learning_rate: float = 0.05) -> dict[str, Any]:
    """Small deterministic logistic regression trainer for offline research only."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    if X.ndim != 2 or len(X) != len(y) or len(y) < 20:
        raise ValueError("Need a 2-D feature matrix with at least 20 labelled observations")
    mean = X.mean(axis=0)
    scale = X.std(axis=0)
    scale[scale == 0] = 1.0
    Z = (X - mean) / scale
    weights = np.zeros(Z.shape[1], dtype=float)
    intercept = 0.0
    for _ in range(steps):
        logits = np.clip(intercept + Z @ weights, -30, 30)
        probs = 1.0 / (1.0 + np.exp(-logits))
        error = probs - y
        intercept -= learning_rate * float(error.mean())
        gradient = (Z.T @ error) / len(y) + l2 * weights / len(y)
        weights -= learning_rate * gradient
    return {
        "feature_names": FEATURE_NAMES[: Z.shape[1]],
        "intercept": float(intercept),
        "weights": weights.tolist(),
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "training_rows": int(len(y)),
        "model_type": "logistic_regression",
    }


def predict_model(model: dict[str, Any], X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    mean = np.asarray(model["mean"], dtype=float)
    scale = np.asarray(model["scale"], dtype=float)
    weights = np.asarray(model["weights"], dtype=float)
    Z = (X - mean) / np.where(scale == 0, 1.0, scale)
    logits = np.clip(float(model["intercept"]) + Z @ weights, -30, 30)
    return 1.0 / (1.0 + np.exp(-logits))


def save_model(model: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")


def load_model(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))
