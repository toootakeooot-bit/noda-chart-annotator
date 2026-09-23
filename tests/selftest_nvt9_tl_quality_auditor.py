from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_tl_quality_auditor", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def base_record() -> dict:
    return {
        "line_id": "D1_DOWN_03",
        "direction": "FALLING",
        "source_tf": "D1",
        "owner_tf": "D1",
        "structure_level": "LARGE_DOW",
        "anchor1": {
            "kind": "HIGH",
            "time": "2026-07-01T00:00:00",
            "price": 160.0,
            "confirmed_by_time": "2026-07-02T00:00:00",
            "retracement": 0.38,
        },
        "anchor2": {
            "kind": "HIGH",
            "time": "2026-08-01T00:00:00",
            "price": 158.0,
            "confirmed_by_time": "2026-08-02T00:00:00",
            "retracement": 0.38,
        },
        "turn_span": 10,
        "tl_contacts": 3,
        "unbroken_close": True,
        "structure": {
            "hl_exists": True,
            "n_pattern_confirmed": True,
            "dow_confirmed": True,
            "hl_break": True,
            "break_by_close": True,
        },
        "outer_inner": {
            "outer_candidate_exists": True,
            "selected_outer": True,
        },
    }


def reason_codes(result: dict) -> set[str]:
    return {item["reason_code"] for item in result["reasons"]}


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    mod = load_module(repo / "tools" / "nvt" / "tl_quality_auditor.py")

    # 9/19: baseline normal structure should remain GOOD.
    case_0919 = base_record()
    case_0919["matched_patterns"] = ["9/19 Baseline"]
    good = mod.audit_line(case_0919)
    assert good["Quality"] == "GOOD"
    assert good["Confidence"] == "HIGH"
    assert "P01" in good["matched_patterns"]
    assert "P02" in good["matched_patterns"]
    assert "P07" in good["matched_patterns"]

    # 9/12: inner line selected despite an important outer structure.
    case_0912 = base_record()
    case_0912["outer_inner"] = {
        "outer_candidate_exists": True,
        "selected_outer": False,
        "major_wick_outside": True,
    }
    bad_outer = mod.audit_line(case_0912)
    assert bad_outer["Quality"] == "BAD"
    assert bad_outer["cause_layer"] == "ANCHOR"
    assert "OUTER_STRUCTURE_MISMATCH" in reason_codes(bad_outer)
    assert any(x["pattern_id"] == "P03" for x in bad_outer["reasons"])

    # 9/5: old TL is broken, but a new TL is not structurally ready.
    case_0905 = base_record()
    case_0905["structure"] = {
        "prior_tl_broken": True,
        "new_structure_ready": False,
        "hl_exists": True,
        "n_pattern_confirmed": False,
        "dow_confirmed": False,
        "hl_break": False,
        "break_by_close": False,
    }
    hold_no_line = mod.audit_line(case_0905)
    assert hold_no_line["Quality"] == "HOLD"
    assert hold_no_line["cause_layer"] == "STRUCTURE"
    assert "NO_LINE_HOLD" in reason_codes(hold_no_line)
    assert any(x["pattern_id"] == "P04" for x in hold_no_line["reasons"])

    # Wick-only break cannot activate a new TL.
    wick_only = base_record()
    wick_only["structure"]["break_by_close"] = False
    hold_wick = mod.audit_line(wick_only)
    assert hold_wick["Quality"] == "HOLD"
    assert "WICK_ONLY_BREAK" in reason_codes(hold_wick)
    assert any(x["pattern_id"] == "P06" for x in hold_wick["reasons"])

    # Cross-TF transfer may be valid when ownership is confirmed.
    cross_ok = base_record()
    cross_ok["source_tf"] = "H4"
    cross_ok["owner_tf"] = "D1"
    cross_ok["cross_tf"] = {"mapping_allowed": True, "owner_confirmed": True}
    cross_good = mod.audit_line(cross_ok)
    assert cross_good["Quality"] == "GOOD"
    assert cross_good["checks"]["Cross-TF"] == "PASS"
    assert "P08" in cross_good["matched_patterns"]

    # Ambiguous ownership is HOLD, not BAD.
    cross_hold = base_record()
    cross_hold["source_tf"] = "H4"
    cross_hold["owner_tf"] = "D1"
    cross_hold["cross_tf"] = {
        "mapping_allowed": True,
        "owner_confirmed": False,
        "ownership_ambiguous": True,
    }
    hold_owner = mod.audit_line(cross_hold)
    assert hold_owner["Quality"] == "HOLD"
    assert hold_owner["cause_layer"] == "OWNERSHIP"
    assert "OWNERSHIP_UNRESOLVED" in reason_codes(hold_owner)

    # Explicit ambiguity must HOLD even when runtime visibility falls back to source_tf.
    same_tf_fallback = base_record()
    same_tf_fallback["source_tf"] = "H4"
    same_tf_fallback["owner_tf"] = "H4"
    same_tf_fallback["cross_tf"] = {
        "classification": "AMBIGUOUS_KEEP_VISIBLE",
        "mapping_allowed": True,
        "owner_confirmed": False,
        "ownership_ambiguous": True,
        "candidate_owner_tf": "D1",
    }
    same_tf_hold = mod.audit_line(same_tf_fallback)
    assert same_tf_hold["Quality"] == "HOLD"
    assert same_tf_hold["OwnershipReadiness"] == "HOLD"
    assert same_tf_hold["checks"]["Cross-TF"] == "HOLD"
    assert "OWNERSHIP_UNRESOLVED" in reason_codes(same_tf_hold)
    assert "P09" in {x["pattern_id"] for x in same_tf_hold["reasons"]}

    # Explicit local ownership confirmation is PASS and gets P21.
    local_confirmed = base_record()
    local_confirmed["source_tf"] = "H4"
    local_confirmed["owner_tf"] = "H4"
    local_confirmed["cross_tf"] = {
        "classification": "LOCAL_OWNED_DISTINCT",
        "mapping_allowed": True,
        "owner_confirmed": True,
        "ownership_ambiguous": False,
    }
    local_result = mod.audit_line(local_confirmed)
    assert local_result["Quality"] == "GOOD"
    assert local_result["OwnershipReadiness"] == "PASS"
    assert "P21" in local_result["matched_patterns"]

    # Higher timeframe owner may be confirmed while parent-family match remains unresolved.
    higher_owner = base_record()
    higher_owner["source_tf"] = "H1"
    higher_owner["owner_tf"] = "H4"
    higher_owner["cross_tf"] = {
        "classification": "HIGHER_TF_OWNER_PARENT_UNRESOLVED",
        "mapping_allowed": True,
        "owner_confirmed": True,
        "ownership_ambiguous": False,
        "parent_family_unresolved": True,
    }
    higher_result = mod.audit_line(higher_owner)
    assert higher_result["Quality"] == "GOOD"
    assert higher_result["OwnershipReadiness"] == "PASS"
    assert "P08" in higher_result["matched_patterns"]

    # Candidate-generation and selector failures must be separated.
    missing_candidate = base_record()
    missing_candidate["candidate"] = {"candidate_present": False}
    bad_candidate = mod.audit_line(missing_candidate)
    assert bad_candidate["Quality"] == "BAD"
    assert bad_candidate["cause_layer"] == "CANDIDATE_GENERATION"
    assert "CANDIDATE_GENERATION_ERROR" in reason_codes(bad_candidate)

    selector_error = base_record()
    selector_error["candidate"] = {"candidate_present": True}
    selector_error["selector"] = {"selector_match": False}
    bad_selector = mod.audit_line(selector_error)
    assert bad_selector["Quality"] == "BAD"
    assert bad_selector["cause_layer"] == "SELECTOR"
    assert "SELECTOR_ERROR" in reason_codes(bad_selector)

    # Small-Dow evidence must not be promoted to a major TL.
    small_only = base_record()
    small_only["structure"]["small_dow_only"] = True
    bad_small = mod.audit_line(small_only)
    assert bad_small["Quality"] == "BAD"
    assert "SMALL_DOW_MAJOR_PROMOTION" in reason_codes(bad_small)

    # Latest-only precedence is prohibited.
    latest_only = base_record()
    latest_only["selector"] = {"precedence_basis": "LATEST_ONLY"}
    bad_latest = mod.audit_line(latest_only)
    assert bad_latest["Quality"] == "BAD"
    assert "LATEST_ONLY_PRECEDENCE" in reason_codes(bad_latest)

    # Explicit invalid Pivot is a hard BAD.
    invalid_pivot = base_record()
    invalid_pivot["anchor2"]["retracement"] = 0.20
    bad_pivot = mod.audit_line(invalid_pivot)
    assert bad_pivot["Quality"] == "BAD"
    assert "PIVOT_ERROR" in reason_codes(bad_pivot)

    # Persistent monitoring reference can remain structurally important.
    persistent = base_record()
    persistent["lifecycle_evidence"] = {"persistent_reference_retained": True}
    persistent_result = mod.audit_line(persistent)
    assert "P16" in persistent_result["matched_patterns"]

    # Valid TURN_LINE may be intentionally display-suppressed.
    suppressed = base_record()
    suppressed["lifecycle_evidence"] = {
        "candidate_valid": True,
        "display_suppressed": True,
        "line_role": "TURN_LINE",
    }
    suppressed_result = mod.audit_line(suppressed)
    assert "P17" in suppressed_result["matched_patterns"]

    # Gentler-angle preference is a Selector rule only when multiple valid alternatives exist.
    gentler = base_record()
    gentler["selector"] = {
        "multiple_valid_alternatives": True,
        "gentler_preference_satisfied": True,
    }
    gentler_result = mod.audit_line(gentler)
    assert "P18" in gentler_result["matched_patterns"]

    missed_gentler = base_record()
    missed_gentler["selector"] = {
        "multiple_valid_alternatives": True,
        "gentler_preference_satisfied": False,
    }
    missed_gentler_result = mod.audit_line(missed_gentler)
    assert missed_gentler_result["Quality"] == "BAD"
    assert "GENTLER_PREFERENCE_MISMATCH" in reason_codes(missed_gentler_result)

    # Approximate teacher-window absence is diagnostic HOLD, not hard BAD.
    window_gap = base_record()
    window_gap["candidate"] = {"teacher_window_absent_diagnostic": True}
    window_gap_result = mod.audit_line(window_gap)
    assert window_gap_result["Quality"] == "HOLD"
    assert "TEACHER_WINDOW_ABSENT_DIAGNOSTIC" in reason_codes(window_gap_result)

    # AuditReadiness distinguishes missing evidence from a market-structure HOLD.
    sparse = {
        "line_id": "SPARSE",
        "direction": "FALLING",
        "source_tf": "H4",
        "owner_tf": "H4",
        "anchor1_time": "2026-01-01T00:00:00",
        "anchor1_price": 160.0,
        "anchor2_time": "2026-02-01T00:00:00",
        "anchor2_price": 159.0,
    }
    sparse_result = mod.audit_line(sparse)
    assert sparse_result["Quality"] == "HOLD"
    assert sparse_result["AuditReadiness"] in {"PARTIAL", "INSUFFICIENT"}
    assert sparse_result["missing_evidence"]

    # Repeated input must be deterministic.
    first = mod.audit_line(case_0919)
    second = mod.audit_line(json.loads(json.dumps(case_0919)))
    assert first == second

    batch = mod.audit_lines([case_0919, case_0905, case_0912])
    assert batch["quality_counts"] == {"GOOD": 1, "HOLD": 1, "BAD": 1}

    print("NVT9 TL QUALITY AUDITOR SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
