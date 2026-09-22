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
    assert set(entries) >= {
        "RD0919-001", "RD0919-002", "RD0919-003", "RD0919-004",
        "RD0919-005", "RD0919-006", "RD0919-007", "RD0912-001",
        "RD0912-002", "RD0912-003", "RD0912-004", "RD0912-005", "RD0912-006",
        "RD0912-007", "RD0912-008",
    }

    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    r06 = next(x for x in ref["lines"] if x["reference_id"] == "R0919-06")
    assert r06["display_override"]["status"] == "SUPPRESSED"
    assert r06["display_override"]["reason_code"] == "USER_CONFIRMED_UNNECESSARY_0919_VISUAL"

    builder_text = REF_BUILDER.read_text(encoding="utf-8")
    assert 'abs(float(line["zone_width"])) <= 1e-12' in builder_text

    overlay_text = OVERLAY.read_text(encoding="utf-8")
    assert "TIGHTEST_UNBROKEN_BROAD_SUPPORT" in overlay_text
    assert "WEAKER_OVERLAP_OR_TOO_CLOSE_ZONE_SUPPRESSED" in overlay_text
    assert "build_h1_native_continuation" in overlay_text
    assert 'max_zones=(2 if case_tag == "0912" else 3)' in overlay_text
    assert "recent_anchor2_times = {p.time for p in lows[-10:]}" in overlay_text
    assert "build_d1_major_channel" in overlay_text
    assert "build_d1_visual_truth_0912" in overlay_text
    assert "build_d1_retained_reference_0912" in overlay_text
    assert "2025-04-01T00:00:00" in overlay_text
    assert "2025-08-20T00:00:00" in overlay_text
    assert "H1_NATIVE_FORMATION_VALID_AFTER_ANCHOR2" in overlay_text

    assert entries["RD0919-001"]["status"] == "ENFORCED"
    assert entries["RD0919-002"]["status"] == "ENFORCED"
    assert entries["RD0919-003"]["replacement_policy"] == "TIGHTEST_UNBROKEN_BROAD_SUPPORT"
    assert entries["RD0919-004"]["reason_code"] == "SUPPRESSED_OVERLAP"
    assert entries["RD0919-005"]["replacement_policy"] == "SEARCH_ALL_CONFIRMED_D1_LOWS_THEN_REQUIRE_BROAD_UNBROKEN_SUPPORT"
    assert entries["RD0919-006"]["replacement_policy"] == "H1_NATIVE_CONFIRMED_PIVOTS"
    assert entries["RD0919-007"]["replacement_policy"] == "MAX_3_WITH_MINIMUM_CENTER_GAP_AND_STRONGER_REACTION_EVIDENCE"
    assert entries["RD0912-001"]["reason_code"] == "NO_LINE_NO_SYNTHETIC_FALLBACK"
    assert entries["RD0912-002"]["replacement_policy"] == "SUPPRESS_SOURCE_AND_ALL_PLAN_B_COPIES_NO_REPLACEMENT"
    assert entries["RD0912-003"]["status"] == "SUPERSEDED_BY_VISUAL_TRUTH"
    assert entries["RD0912-003"]["superseded_by"] == "VT0912-D1-001"
    assert entries["RD0912-004"]["replacement_policy"] == "STRICT_FIRST_THEN_POST_ANCHOR2_UNBROKEN_H1_N_STRUCTURE"
    assert entries["RD0912-005"]["status"] == "SUPERSEDED_WRONG_INTERPRETATION"
    assert entries["RD0912-005"]["superseded_by"] == "VT0912-D1-001"
    assert entries["RD0912-006"]["replacement_policy"] == "CHANNEL_ANCHOR_FROM_ORIGINAL_FORMATION_WINDOW"
    assert entries["RD0912-007"]["replacement_policy"] == "PROJECT_TO_CUTOFF_THEN_RAY_RIGHT_FALSE"
    assert entries["RD0912-008"]["replacement_policy"] == "VT0912_D1_001_USER_ANNOTATED_2026_LOW_WINDOWS"

    print("NVT9_REJECTED_DRAW_LEDGER_SELFTEST_PASS")


if __name__ == "__main__":
    main()
