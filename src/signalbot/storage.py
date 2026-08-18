from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def ensure_parent(path: str | Path) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path


def append_jsonl(path: str | Path, row: dict[str, Any], max_rows: int = 5000) -> None:
    file_path = ensure_parent(path)
    rows: list[dict[str, Any]] = []
    if file_path.exists():
        for line in file_path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows.append(row)
    rows = rows[-max_rows:]
    file_path.write_text("\n".join(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in rows) + "\n", encoding="utf-8")


def append_jsonl_unbounded(path: str | Path, row: dict[str, Any]) -> None:
    """Append one immutable JSONL record without pruning historical archive rows."""
    file_path = ensure_parent(path)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: str | Path, payload: Any) -> None:
    file_path = ensure_parent(path)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: str | Path, default: Any) -> Any:
    file_path = Path(path)
    if not file_path.exists():
        return default
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def append_csv(path: str | Path, row: dict[str, Any]) -> None:
    file_path = ensure_parent(path)
    flattened = {key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()}
    fieldnames = list(flattened)
    exists = file_path.exists() and file_path.stat().st_size > 0
    with file_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(flattened)


def build_period_summary(trades: list[dict[str, Any]], period: str) -> dict[str, Any]:
    """Return a compact paper-trading summary for a named reporting period."""
    closed = [trade for trade in trades if trade.get("status") in {"TP_HIT", "SL_HIT", "TIMEOUT", "CLOSED"}]
    wins = [trade for trade in closed if float(trade.get("result_r", 0) or 0) > 0]
    return {
        "paper_trade_only": True,
        "period": period,
        "signals_total": len(trades),
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(closed) - len(wins),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 2) if closed else 0.0,
        "net_r": round(sum(float(t.get("result_r", 0) or 0) for t in closed), 3),
        "sample_status": "insufficient_sample" if len(closed) < 30 else "observed_sample",
    }


def build_performance(trades: list[dict[str, Any]]) -> dict[str, Any]:
    closed = [trade for trade in trades if trade.get("status") in {"TP_HIT", "SL_HIT", "CLOSED"}]
    wins = [trade for trade in closed if float(trade.get("result_r", 0) or 0) > 0]
    return {
        "total_signals": len(trades),
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(closed) - len(wins),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 2) if closed else 0.0,
        "average_r": round(sum(float(t.get("result_r", 0) or 0) for t in closed) / len(closed), 3) if closed else 0.0,
        "total_r": round(sum(float(t.get("result_r", 0) or 0) for t in closed), 3),
    }
