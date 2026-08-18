from pathlib import Path

report = Path(__file__).resolve().parents[1] / "ADVANCED_VALIDATION_REPORT.md"
text = report.read_text(encoding="utf-8")
required = [
    "## Section A — Statistical Rigor ও Overfitting Discipline",
    "## Section B — Market Microstructure ও Anti-Retail-Trap Design",
    "## Section C — Data Integrity ও Regime Awareness",
    "## Section D — Portfolio-Level ও Correlated Risk",
    "## Section E — Additional Circuit Breakers",
    "## Section F — News/Sentiment Sophistication",
    "## Section G — Strict Paper-Trading Protocol",
    "## Retail-trap audit",
    "## Updated risk register",
    "## Final updated verdict",
    "## Reproducibility and references",
]
for heading in required:
    assert heading in text, heading
for phrase in ["−18.0R", "24.79%–36.55%", "44R", "0.825", "not tested", "বর্তমানে live capital-এর জন্য trade-worthy নয়", "4–8 weeks", "30–50 closed trades"]:
    assert phrase in text, phrase
assert "[1]" in text and "[2]" in text and "[3]" in text and "[4]" in text and "[5]" in text and "[6]" in text
print("advanced_validation_report_ok")
