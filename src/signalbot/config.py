from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = "config.yaml"


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load YAML configuration and apply safe environment overrides."""
    config_path = Path(path)
    if not config_path.exists():
        example = config_path.with_name("config.example.yaml")
        if example.exists():
            config_path = example
        else:
            raise FileNotFoundError(f"Configuration file not found: {path}")

    with config_path.open("r", encoding="utf-8") as handle:
        config: dict[str, Any] = yaml.safe_load(handle) or {}

    risk = config.setdefault("risk", {})
    strategy = config.setdefault("strategy", {})
    exchange = config.setdefault("exchange", {})
    notifications = config.setdefault("notifications", {})

    risk["current_balance"] = _env_float("ACCOUNT_BALANCE", float(risk.get("current_balance", 10000)))
    risk["initial_balance"] = _env_float("INITIAL_BALANCE", float(risk.get("initial_balance", risk["current_balance"])))
    risk["risk_per_trade_pct"] = _env_float("RISK_PER_TRADE_PCT", float(risk.get("risk_per_trade_pct", 1.0)))
    risk["daily_loss_limit_pct"] = _env_float("DAILY_LOSS_LIMIT_PCT", float(risk.get("daily_loss_limit_pct", 5.0)))
    risk["max_drawdown_pct"] = _env_float("MAX_DRAWDOWN_PCT", float(risk.get("max_drawdown_pct", 10.0)))
    risk["max_open_trades"] = int(os.getenv("MAX_OPEN_TRADES", risk.get("max_open_trades", 5)))
    strategy["min_confidence"] = int(os.getenv("MIN_CONFIDENCE", strategy.get("min_confidence", 65)))
    strategy["min_confluence"] = int(os.getenv("MIN_CONFLUENCE", strategy.get("min_confluence", 4)))
    exchange["id"] = os.getenv("EXCHANGE_ID", exchange.get("id", "binance"))
    notifications["telegram_enabled"] = os.getenv("TELEGRAM_ENABLED", str(notifications.get("telegram_enabled", True))).lower() == "true"
    notifications["discord_enabled"] = os.getenv("DISCORD_ENABLED", str(notifications.get("discord_enabled", True))).lower() == "true"
    return config
