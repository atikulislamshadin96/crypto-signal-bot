from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from signalbot.indicators import add_indicators
from signalbot.models import NewsItem, Signal
from signalbot.news import classify_text, news_filter
from signalbot.risk import calculate_risk_state, can_open_signal


def test_classify_text_and_high_impact():
    sentiment, impact, matched = classify_text("ETF approval brings bullish inflow", ["approval", "bullish", "inflow"], ["hack"], ["ETF"])
    assert sentiment == "Positive"
    assert impact == "high"
    assert "ETF" in matched


def test_negative_news_blocks_long():
    items = [NewsItem("Bitcoin hack causes bearish outflow", "https://example.com/btc", "2026-01-01T00:00:00+00:00", "example", "Negative", "high", ["hack"])]
    blocked, context, sentiment = news_filter("BTC/USDT", "LONG", items, {})
    assert blocked is True
    assert context
    assert sentiment == "Negative"


def test_indicators_are_added():
    rows = 250
    frame = pd.DataFrame({
        "open": [100 + i * 0.1 for i in range(rows)],
        "high": [101 + i * 0.1 for i in range(rows)],
        "low": [99 + i * 0.1 for i in range(rows)],
        "close": [100 + i * 0.1 for i in range(rows)],
        "volume": [1000 + (100 if i == rows - 1 else 0) for i in range(rows)],
    })
    result = add_indicators(frame, {})
    assert {"ema_fast", "ema_slow", "rsi", "macd_hist", "atr", "volume_ratio"}.issubset(result.columns)
    assert len(result) > 0


def test_daily_loss_guard():
    config = {"risk": {"initial_balance": 10000, "current_balance": 10000, "daily_loss_limit_pct": 5, "max_drawdown_pct": 10, "max_open_trades": 5}}
    today = datetime.now(timezone.utc).date().isoformat()
    trades = [{"status": "SL_HIT", "pnl_amount": -500, "closed_at": f"{today}T12:00:00+00:00"}]
    state = calculate_risk_state(trades, config)
    assert state.daily_loss_pct == 5
    signal = Signal("id", f"{today}T12:00:00+00:00", "BTC/USDT", "LONG", "15m", 100, 95, 110, 2, 80, 4, ["trend"], "BULLISH", "Neutral", [], 20, 100)
    allowed, reason = can_open_signal(signal, trades, state, config)
    assert allowed is False
    assert "Daily loss" in reason



def test_context_fusion_is_explainable_and_coverage_aware():
    from signalbot.fusion import score_context

    config = {
        "fusion": {
            "enabled": True,
            "min_feature_coverage": 0.5,
            "min_score": -0.5,
            "weights": {"derivatives": 0.4, "order_book": 0.35, "macro": 0.25},
        }
    }
    context = {
        "derivatives": {"available": True, "funding_rate": -0.0003, "open_interest_change_pct": 2.0, "long_short_ratio": 0.8},
        "order_book": {"available": True, "imbalance": 0.35, "spread_bps": 2.0, "bid_wall_ratio": 2.5, "ask_wall_ratio": 1.0},
        "macro": {"available": True, "btc_dominance": 55.0, "market_cap_change_24h_pct": 1.0, "stablecoin_supply_change_7d_pct": 0.4, "dxy": {"available": False}},
    }
    result = score_context(context, "LONG", config, "ETH/USDT")
    assert result.coverage >= 0.5
    assert result.eligible is True
    assert result.model_source == "heuristic_untrained"
    assert "order_book_imbalance" in result.contributions


def test_context_missingness_is_not_fabricated():
    from signalbot.context import context_coverage, context_feature_snapshot

    context = {"derivatives": {"available": False}, "order_book": {"available": False}, "macro": {"available": False}}
    snapshot = context_feature_snapshot(context)
    assert all(value is None for value in snapshot.values())
    assert context_coverage(context) == 0.0


def test_paper_trade_closes_on_next_closed_candle():
    from signalbot.runner import _update_open_trades

    class FakeExchange:
        def fetch_ohlcv(self, symbol, timeframe, limit):
            return [
                [1_000, 100, 101, 99, 100, 10],
                [901_000, 100, 111, 99, 109, 10],  # closed candle hits LONG TP
                [1_801_000, 109, 110, 108, 109, 10],  # forming candle is ignored
            ]

    trades = [{
        "signal_id": "paper-1",
        "symbol": "BTC/USDT",
        "side": "LONG",
        "timeframe": "15m",
        "entry": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "position_size": 1.0,
        "risk_amount": 5.0,
        "opened_at": "1970-01-01T00:00:00+00:00",
        "status": "OPEN",
    }]
    changed = _update_open_trades(trades, FakeExchange(), {"paper_trading": {"timeout_candles": 8}})
    assert changed is True
    assert trades[0]["status"] == "TP_HIT"
    assert trades[0]["result_r"] == 2.0


def test_feature_archive_is_append_only(tmp_path):
    from signalbot.storage import append_jsonl_unbounded

    archive = tmp_path / "feature_archive.jsonl"
    append_jsonl_unbounded(archive, {"timestamp": "t1", "symbol": "BTC/USDT"})
    append_jsonl_unbounded(archive, {"timestamp": "t2", "symbol": "ETH/USDT"})
    rows = archive.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
    assert '"timestamp": "t1"' in rows[0]
    assert '"timestamp": "t2"' in rows[1]


def test_period_summary_marks_small_sample_as_insufficient():
    from signalbot.storage import build_period_summary

    summary = build_period_summary([], "2026-08-18")
    assert summary["paper_trade_only"] is True
    assert summary["sample_status"] == "insufficient_sample"
    assert summary["closed_trades"] == 0


def test_research_candidates_are_not_production_enabled():
    from signalbot.research_candidates import candidate_registry, funding_mean_reversion_feature

    registry = candidate_registry()
    assert len(registry) >= 4
    assert all(item["production_enabled"] is False for item in registry)
    assert all(item["status"] == "not yet tested" for item in registry)

    funding = pd.Series([0.001 * i for i in range(30)])
    feature = funding_mean_reversion_feature(funding, window=10)
    assert feature.iloc[:10].isna().all()
