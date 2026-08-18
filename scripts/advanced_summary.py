import json
from pathlib import Path

p = json.loads((Path(__file__).resolve().parents[1] / "advanced_validation.json").read_text(encoding="utf-8"))
for symbol, item in p["per_symbol"].items():
    audit = item.get("data_audit_15m", {})
    regime = item.get("regime_15m", {})
    print(f"{symbol}: rows={audit.get('rows')} missing={audit.get('missing_candles')} outliers={audit.get('outlier_count')} regimes={regime.get('shares_pct')}")
    for w in item.get("walk_forward_fixed_parameter", []):
        print(f"  W{w['window']}: n={w['trades']} win={w['win_rate_pct_all_signals']}% net={w['net_r']}R dd={w['max_drawdown_r']}R")
