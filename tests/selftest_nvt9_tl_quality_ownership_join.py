from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_tl_quality_ownership_join", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def candidate() -> dict:
    return {
        "candidate_id": "FALLING:2026-07-01T00:00:00:2026-08-01T00:00:00",
        "direction": "FALLING",
        "anchor1": {
            "kind": "HIGH",
            "time": "2026-07-01T00:00:00",
            "price": 160.0,
            "confirmed_by_time": "2026-07-02T00:00:00",
            "retracement": 0.38,
            "pivot_valid": True,
            "closed_bar_confirmed": True,
        },
        "anchor2": {
            "kind": "HIGH",
            "time": "2026-08-01T00:00:00",
            "price": 158.0,
            "confirmed_by_time": "2026-08-02T00:00:00",
            "retracement": 0.38,
            "pivot_valid": True,
            "closed_bar_confirmed": True,
        },
        "decision_hl": {
            "kind": "LOW",
            "time": "2026-07-15T00:00:00",
            "price": 155.0,
            "confirmed_by_time": "2026-07-16T00:00:00",
            "retracement": 0.38,
            "pivot_valid": True,
            "closed_bar_confirmed": True,
        },
        "hl_break_time": "2026-08-02T00:00:00",
        "hl_break_mode": "CLOSED_BAR_CLOSE_PROVISIONAL",
        "break_by_close": True,
        "slope_per_second": -7.4e-7,
        "turn_span": 10,
        "tl_contacts": 3,
        "ch_contacts": 4,
        "unbroken_close": True,
        "ch_offset": -4.0,
        "zone_width": 0.2,
    }


def sidecar_line(tf: str, line_id: str) -> dict:
    c = candidate()
    return {
        "line_id": line_id,
        "symbol": "USDJPY#",
        "timeframe": tf,
        "structure_level": "MID_DOW",
        "generation_role": "CURRENT",
        "line_status": "ACTIVE",
        "match_status": "EXACT_UNIQUE",
        "candidate_match_count": 1,
        "state_geometry": {
            "direction": "FALLING",
            "anchor1_time": c["anchor1"]["time"],
            "anchor1_price": c["anchor1"]["price"],
            "anchor2_time": c["anchor2"]["time"],
            "anchor2_price": c["anchor2"]["price"],
            "ch_offset": c["ch_offset"],
            "zone_width": c["zone_width"],
        },
        "candidate": c,
        "candidate_variants": [c],
        "selector_evidence": {
            "candidate_present": True,
            "direct_selected_candidate_id": c["candidate_id"],
            "selector_match": True,
            "reason": {"turn_span": 10},
            "selection_scope": "FULL_HISTORY_DIRECT_SELECTOR",
        },
        "quality_audit": {
            "Quality": "GOOD",
            "AuditReadiness": "READY",
            "OwnershipReadiness": "PASS",
            "checks": {"Cross-TF": "PASS"},
        },
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    mod = load_module(repo / "tools" / "nvt" / "build_nvt9_tl_quality_ownership_join.py")

    evidence = {
        "schema": "nvt9-tl-audit-evidence/1.0",
        "status": "PASS_AUDIT_EVIDENCE",
        "symbol": "USDJPY#",
        "timeframes": {
            "D1": {"lines": [sidecar_line("D1", "D1_A")]},
            "H4": {"lines": [sidecar_line("H4", "H4_A")]},
            "H1": {"lines": [sidecar_line("H1", "H1_A")]},
            "M15": {"lines": [sidecar_line("M15", "M15_A")]},
        },
    }

    ownership = {
        "schema": "nvt9-ownership-adjudication/0.2",
        "status": "BLOCKED_FINAL_ADJUDICATION",
        "symbol": "USDJPY#",
        "records": [
            {
                "source_tf": "H4",
                "line_id": "H4_A",
                "classification": "AMBIGUOUS_KEEP_VISIBLE",
                "structural_owner_tf": "H4",
                "adjudication_required": True,
                "user_observed_owner_candidate_tf": "D1",
                "best_metric_parent_tf": "D1",
                "display_recommendation": "KEEP_VISIBLE",
                "reason_code": "NON_EXACT_REQUIRES_TEACHER_ADJUDICATION",
                "relation": "PENDING_TEACHER_OR_MANUAL_ADJUDICATION",
            },
            {
                "source_tf": "H1",
                "line_id": "H1_A",
                "classification": "PARENT_OWNED_SAME_FAMILY",
                "structural_owner_tf": "H4",
                "same_family_parent_id": "H4_A",
                "adjudication_required": False,
                "display_recommendation": "REFERENCE_OR_REFINED_GEOMETRY",
                "reason_code": "EXACT_CROSS_TF_GEOMETRY_CONFIRMED",
                "relation": "AUTO_EXACT_GEOMETRY",
            },
            {
                "source_tf": "M15",
                "line_id": "M15_A",
                "classification": "LOCAL_OWNED_DISTINCT",
                "structural_owner_tf": "M15",
                "same_family_parent_id": None,
                "adjudication_required": False,
                "display_recommendation": "DRAW_LOCAL_STRUCTURE",
                "reason_code": "MANUAL_LOCAL_STRUCTURE_CONFIRMED",
                "relation": "MANUAL_TEACHER_ADJUDICATION",
                "teacher_evidence_note": "Teacher confirms M15-local structure.",
            },
        ],
    }

    gate = {
        "schema": "nvt9-ownership-gate/0.1",
        "status": "BLOCKED_V3_5",
        "unresolved": [{"source_tf": "H4", "line_id": "H4_A"}],
        "problems": [],
        "parent_match_unresolved": [],
    }

    result = mod.build_join(evidence=evidence, ownership=ownership, gate=gate)
    assert result["status"] == "PASS_OWNERSHIP_JOIN"
    assert result["line_count"] == 4
    assert result["quality_counts"] == {"GOOD": 3, "HOLD": 1}
    assert result["ownership_readiness_counts"] == {"PASS": 3, "HOLD": 1}
    assert result["ownership_unresolved_count"] == 1

    by_id = {}
    for tf_payload in result["timeframes"].values():
        for row in tf_payload["lines"]:
            by_id[row["line_id"]] = row

    d1 = by_id["D1_A"]
    assert d1["ownership_evidence"]["classification"] == "ROOT_LOCAL_OWNED"
    assert d1["ownership_evidence"]["owner_confirmed"] is True
    assert d1["quality_audit"]["Quality"] == "GOOD"
    assert d1["quality_audit"]["OwnershipReadiness"] == "PASS"
    assert "P21" in d1["quality_audit"]["matched_patterns"]

    h4 = by_id["H4_A"]
    assert h4["ownership_evidence"]["classification"] == "AMBIGUOUS_KEEP_VISIBLE"
    assert h4["ownership_evidence"]["owner_tf"] == "H4"
    assert h4["ownership_evidence"]["candidate_owner_tf"] == "D1"
    assert h4["ownership_evidence"]["owner_confirmed"] is False
    assert h4["quality_audit"]["Quality"] == "HOLD"
    assert h4["quality_audit"]["OwnershipReadiness"] == "HOLD"
    assert h4["quality_audit"]["cause_layer"] == "OWNERSHIP"
    assert any(x["reason_code"] == "OWNERSHIP_UNRESOLVED" for x in h4["quality_audit"]["reasons"])

    h1 = by_id["H1_A"]
    assert h1["ownership_evidence"]["classification"] == "PARENT_OWNED_SAME_FAMILY"
    assert h1["ownership_evidence"]["owner_tf"] == "H4"
    assert h1["ownership_evidence"]["same_family_parent_id"] == "H4_A"
    assert h1["ownership_evidence"]["parent_family_confirmed"] is True
    assert h1["quality_audit"]["Quality"] == "GOOD"
    assert h1["quality_audit"]["OwnershipReadiness"] == "PASS"
    assert "P08" in h1["quality_audit"]["matched_patterns"]

    m15 = by_id["M15_A"]
    assert m15["ownership_evidence"]["classification"] == "LOCAL_OWNED_DISTINCT"
    assert m15["ownership_evidence"]["owner_tf"] == "M15"
    assert m15["quality_audit"]["Quality"] == "GOOD"
    assert "P21" in m15["quality_audit"]["matched_patterns"]

    # Owner timeframe may be confirmed even when exact parent-family ID is unresolved.
    parent_open = mod.ownership_evidence(
        source_tf="H1",
        line_id="H1_B",
        rec={
            "source_tf": "H1",
            "line_id": "H1_B",
            "classification": "HIGHER_TF_OWNER_PARENT_UNRESOLVED",
            "structural_owner_tf": "H4",
            "same_family_parent_id": None,
            "adjudication_required": False,
            "teacher_evidence_note": "Teacher confirms H4 placement.",
            "reason_code": "HIGHER_TF_OWNER_CONFIRMED_PARENT_MATCH_UNRESOLVED",
            "relation": "MANUAL_TEACHER_ADJUDICATION",
        },
        gate={
            "buckets": ["parent_match_unresolved"],
            "items": [{"source_tf": "H1", "line_id": "H1_B", "owner_tf": "H4"}],
        },
    )
    assert parent_open["owner_tf"] == "H4"
    assert parent_open["owner_confirmed"] is True
    assert parent_open["parent_family_unresolved"] is True
    assert parent_open["parent_family_confirmed"] is False

    # Missing non-root ownership evidence is HOLD rather than accidental local PASS.
    missing = mod.ownership_evidence(
        source_tf="H1",
        line_id="H1_MISSING",
        rec=None,
        gate=None,
    )
    assert missing["owner_tf"] == "H1"
    assert missing["owner_confirmed"] is False
    assert missing["ownership_ambiguous"] is True

    again = mod.build_join(evidence=evidence, ownership=ownership, gate=gate)
    assert result == again

    print("NVT9 TL QUALITY OWNERSHIP JOIN SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
