from pathlib import Path

report = Path(__file__).resolve().parents[1] / "VALIDATION_REPORT.md"
text = report.read_text(encoding="utf-8")
required_sections = [
    "## 1. Setup ও test status summary",
    "## 3. Backtest metrics — in-sample বনাম out-of-sample",
    "## 4. Factor contribution analysis",
    "## 5. Confidence বনাম win-rate analysis",
    "## 6. Forward-test log",
    "## 7. Known limitations and risk register",
    "## Final verdict",
]
for section in required_sections:
    assert section in text, section
for phrase in ["34.51%", "17.0R", "Live signal records", "বর্তমানে live trade-worthy নয়"]:
    assert phrase in text, phrase
assert "কোনো সংখ্যা অনুমান" not in text
print("validation_report_ok")
