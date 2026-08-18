from pathlib import Path

from signalbot.config import load_config

root = Path(__file__).resolve().parents[1]
config = load_config(root / "config.yaml")
assert config["risk"]["daily_loss_limit_pct"] == 5.0
assert config["exchange"]["timeframes"]["entry"] == "15m"
assert (root / ".github/workflows/signal_scan.yml").exists()
assert (root / "README.md").exists()
print("repository_validation_ok")
