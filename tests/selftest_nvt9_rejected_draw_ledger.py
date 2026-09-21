from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "nvt" / "manifests" / "NVT9_REJECTED_DRAW_LEDGER_V01.json"
REFERENCE = ROOT / "nvt" / "manifests" / "NVT9_0919_REFERENCE_LINES_V01.json"
REF_BUILDER = ROOT / "tools" / "nvt" / "build_nvt9_0919_reference.py"
OVERLAY = ROOT / "tools" / "nvt" / "build_nvt9_structural_overlay_0919.py"


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    entries = {row["rejection_id"]: row for row in ledger["entries"]}
    assert set(entries) >= {"RD0919-001", "RD0919-002", "RD0919-003", "RD0919-004"}

    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    r06 = next(x for x in ref["lines"] if x["reference_id"] == "R0919-06")
    assert r06["display_override"]["status"] == "SUPPRESSED"
    assert r06["display_override"]["reason_code"] == "USER_CONFIRMED_UNNECESSARY_0919_VISUAL"

    builder_text = REF_BUILDER.read_text(encoding="utf-8")
    assert 'abs(float(line["zone_width"])) <= 1e-12' in builder_text

    overlay_text = OVERLAY.read_text(encoding="utf-8")
    assert "TIGHTEST_UNBROKEN_BROAD_SUPPORT" in overlay_text
    assert "LONGEST_DURATION_FIRST" in overlay_text
    assert "WEAKER_OVERLAPPING_ZONE_SUPPRESSED" in overlay_text

    assert entries["RD0919-001"]["status"] == "ENFORCED"
    assert entries["RD0919-002"]["status"] == "ENFORCED"
    assert entries["RD0919-003"]["replacement_policy"] == "TIGHTEST_UNBROKEN_BROAD_SUPPORT"
    assert entries["RD0919-004"]["reason_code"] == "SUPPRESSED_OVERLAP"

    print("NVT9_REJECTED_DRAW_LEDGER_SELFTEST_PASS")


if __name__ == "__main__":
    main()
