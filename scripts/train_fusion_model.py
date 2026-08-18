#!/usr/bin/env python3
"""Train an interpretable fusion model from a real labelled feature CSV.

Required columns: one binary `label` column plus any subset of FEATURE_NAMES.
The script refuses to fabricate rows and writes only a model artifact supplied
by the caller. Use time-ordered data and hold out the final period yourself.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from signalbot.fusion import FEATURE_NAMES, fit_logistic_model, save_model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Real labelled feature panel CSV")
    parser.add_argument("--output", default="data/fusion_model.json")
    parser.add_argument("--label", default="label")
    parser.add_argument("--limit-features", type=int, default=len(FEATURE_NAMES))
    args = parser.parse_args()

    frame = pd.read_csv(args.csv)
    if args.label not in frame.columns:
        raise SystemExit(f"Missing required label column: {args.label}")
    features = [name for name in FEATURE_NAMES[: args.limit_features] if name in frame.columns]
    if len(features) < 2:
        raise SystemExit("Need at least two recognised fusion feature columns")
    frame = frame[features + [args.label]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 20:
        raise SystemExit("Need at least 20 complete labelled rows; no rows were fabricated")
    labels = pd.to_numeric(frame[args.label], errors="coerce")
    frame = frame[labels.isin([0, 1])]
    if len(frame) < 20 or frame[args.label].nunique() < 2:
        raise SystemExit("Need at least 20 rows and both binary classes")
    model = fit_logistic_model(frame[features].to_numpy(), frame[args.label].to_numpy())
    model["feature_names"] = features
    save_model(model, args.output)
    print({"rows": len(frame), "features": features, "output": str(Path(args.output))})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
