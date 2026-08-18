#!/usr/bin/env python3
"""Validate that the deep architecture report remains evidence-honest."""
from __future__ import annotations

from pathlib import Path


REQUIRED = [
    "## Section A —",
    "## Section B —",
    "## Section C —",
    "## Section D —",
    "## Section E —",
    "## Section F —",
    "## Section G —",
    "## Updated risk register",
    "## Retail-trap audit",
    "## Final updated verdict",
    "## References",
    "not trade-worthy",
    "not available",
    "not tested",
    "point-in-time",
]


def main() -> int:
    path = Path("ADVANCED_ARCHITECTURE_REPORT.md")
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in REQUIRED if needle.lower() not in text.lower()]
    if missing:
        raise SystemExit("Missing report requirements: " + ", ".join(missing))
    if "fabricated" not in text.lower() or "final holdout" not in text.lower():
        raise SystemExit("Report must explicitly address fabricated data and final holdout")
    print("advanced_architecture_report_validation_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
