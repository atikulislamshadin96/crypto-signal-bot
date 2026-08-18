import json
from pathlib import Path

p = json.loads((Path(__file__).resolve().parents[1] / "advanced_validation.json").read_text(encoding="utf-8"))
for i in range(4):
    windows = [item["walk_forward_fixed_parameter"][i] for item in p["per_symbol"].values() if "walk_forward_fixed_parameter" in item]
    trades = sum(w["trades"] for w in windows)
    wins = sum(w["wins"] for w in windows)
    losses = sum(w["losses"] for w in windows)
    net = sum(w["net_r"] for w in windows)
    dd = sum(w["max_drawdown_r"] for w in windows)
    print(f"W{i+1}: trades={trades} wins={wins} losses={losses} win_rate={wins/trades*100:.2f}% net={net:.1f}R sum_symbol_dd={dd:.1f}R")
