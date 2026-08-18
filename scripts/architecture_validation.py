#!/usr/bin/env python3
"""Build honest old-vs-new architecture evidence without fabricating new OOS data."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="advanced_validation.json")
    parser.add_argument("--feature-panel", default="data/orthogonal_features.csv")
    parser.add_argument("--smoke", default="data/context_smoke.json")
    parser.add_argument("--output", default="data/architecture_validation.json")
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else {}
    aggregate = baseline.get("aggregate_oos", {})
    smoke_path = Path(args.smoke)
    smoke = json.loads(smoke_path.read_text(encoding="utf-8")) if smoke_path.exists() else None
    panel_path = Path(args.feature_panel)
    new_status = {
        "status": "not_tested",
        "reason": "No point-in-time historical orthogonal feature panel is present; current provider smoke test is not an OOS backtest.",
        "feature_panel": str(panel_path),
    }
    if panel_path.exists():
        new_status = {
            "status": "available_for_research",
            "reason": "Feature panel exists; run feature_ablation.py and a final untouched holdout before interpreting results.",
            "feature_panel": str(panel_path),
        }
    output: dict[str, Any] = {
        "as_of_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "baseline_old_retail_indicator": {
            "status": "tested",
            "oos_trades": aggregate.get("trades"),
            "oos_wins": aggregate.get("wins"),
            "oos_losses": aggregate.get("losses"),
            "oos_net_r": aggregate.get("net_r"),
            "source": str(baseline_path),
        },
        "new_multi_layer": new_status,
        "runtime_smoke": {
            "status": "tested_current_only" if smoke else "not_run",
            "source": str(smoke_path),
            "historical_claim_allowed": False,
            "available_layers": [
                layer for layer in ("derivatives", "order_book", "macro")
                if smoke and isinstance(smoke.get(layer), dict) and smoke[layer].get("available")
            ],
        },
        "ablation": {
            "status": "requires_real_labelled_feature_panel",
            "script": "scripts/feature_ablation.py",
            "no_fabricated_rows": True,
        },
        "final_holdout": {
            "status": "not_touched",
            "required_before_live_use": True,
        },
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
