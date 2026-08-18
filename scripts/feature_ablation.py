#!/usr/bin/env python3
"""Time-ordered one-feature-at-a-time ablation for a real labelled panel.

This is intentionally conservative: the final chronological holdout is never
used for feature selection. The script reports baseline and add-one-feature
log loss/Brier/AUC when sklearn is available, otherwise it exits clearly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from signalbot.fusion import FEATURE_NAMES


def _metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float | None]:
    eps = 1e-9
    p = np.clip(p, eps, 1 - eps)
    log_loss = float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())
    brier = float(((p - y) ** 2).mean())
    try:
        from sklearn.metrics import roc_auc_score

        auc = float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None
    except ImportError:
        auc = None
    return {"log_loss": log_loss, "brier": brier, "auc": auc}


def _fit_predict(train_x: pd.DataFrame, train_y: np.ndarray, test_x: pd.DataFrame) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=0))
    model.fit(train_x, train_y)
    return model.predict_proba(test_x)[:, 1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Real time-ordered labelled feature panel CSV")
    parser.add_argument("--output", default="data/feature_ablation.json")
    parser.add_argument("--label", default="label")
    parser.add_argument("--holdout-fraction", type=float, default=0.20)
    args = parser.parse_args()

    try:
        import sklearn  # noqa: F401
    except ImportError as exc:
        raise SystemExit("scikit-learn is required for ablation; install it explicitly") from exc

    frame = pd.read_csv(args.csv)
    if args.label not in frame.columns:
        raise SystemExit(f"Missing label column: {args.label}")
    features = [name for name in FEATURE_NAMES if name in frame.columns]
    if len(features) < 2:
        raise SystemExit("Need at least two recognised feature columns")
    frame = frame[features + [args.label]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 40:
        raise SystemExit("Need at least 40 complete chronological rows")
    y = pd.to_numeric(frame[args.label], errors="coerce").to_numpy()
    if not set(np.unique(y)).issubset({0, 1}) or len(np.unique(y)) < 2:
        raise SystemExit("Label must contain both binary classes")
    split = int(len(frame) * (1 - args.holdout_fraction))
    if split < 20 or len(frame) - split < 10:
        raise SystemExit("Train/holdout split is too small")
    train_y, test_y = y[:split], y[split:]
    baseline_features = [features[0]]
    results: list[dict[str, object]] = []
    for feature_set_name, feature_set in [("baseline", baseline_features)] + [
        (f"baseline_plus_{feature}", baseline_features + [feature]) for feature in features[1:]
    ]:
        probabilities = _fit_predict(frame.iloc[:split][feature_set], train_y, frame.iloc[split:][feature_set])
        result = {"feature_set": feature_set_name, "features": feature_set, "metrics": _metrics(test_y, probabilities)}
        results.append(result)
    output = {"rows": len(frame), "train_rows": split, "holdout_rows": len(frame) - split, "results": results, "status": "research_only"}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
