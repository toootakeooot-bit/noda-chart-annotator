from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from nvt.structure_semantics import (
    StructuralHighEvidence,
    default_visibility,
    evaluate_rising_hierarchy,
    turn_line_role_after_small_dow_break,
)


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def add_check(checks: list[dict], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "pass": bool(passed), "detail": detail})


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Build the research-only NVT7.1 semantic freeze candidate for USDJPY H1. "
            "This validates user-operational structure semantics only and never writes Production/MT4."
        )
    )
    ap.add_argument("--importance-handoff", required=True)
    ap.add_argument("--batch03c", required=True)
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    importance = load_json(args.importance_handoff)
    batch03c = load_json(args.batch03c)
    adjudication = load_json(args.adjudication)

    if importance.get("schema") != "nvt7.1-b02-03-line-importance-handoff/0.1":
        raise ValueError("unexpected importance handoff schema")
    if batch03c.get("schema") != "nvt7.1-b02-03-sequence-proxy-search/0.1":
        raise ValueError("unexpected Batch03C schema")
    if adjudication.get("schema") != "nvt7.1-structure-hierarchy-user-adjudication/0.2":
        raise ValueError("unexpected structure hierarchy adjudication schema")

    cases = {c.get("case_id"): c for c in batch03c.get("cases") or []}
    b03c06 = cases.get("USDJPY_NVT71_B03C_06")

    line_roles = adjudication.get("line_roles") or {}
    turn_rule = line_roles.get("TURN_LINE") or {}
    large_tl_rule = line_roles.get("LARGE_DOW_TL") or {}
    hierarchy = adjudication.get("dow_hierarchy") or {}
    high_confirmation = adjudication.get("structural_high_confirmation") or {}
    unfixed = adjudication.get("unfixed_items") or []

    checks: list[dict] = []

    add_check(
        checks,
        "legacy_importance_contract_available",
        importance.get("status") == "PASS_CONTRACTS" and importance.get("all_contracts_pass") is True,
        "The prior B02_03 handoff remains an evidence artifact; conflicting line-promotion semantics are superseded, not deleted.",
    )
    add_check(
        checks,
        "batch03c_future_hidden_case_available",
        bool(b03c06) and b03c06.get("future_bars_included") is False,
        "B03C_06 must exist as future-hidden user-review evidence.",
    )
    add_check(
        checks,
        "turn_line_default_suppressed",
        default_visibility("TURN_LINE") == "VALID_SUPPRESSED"
        and turn_rule.get("default_visibility") == "VALID_SUPPRESSED",
        "TURN_LINE is technically valid/internal but normally not rendered.",
    )
    add_check(
        checks,
        "large_dow_tl_primary_drawable",
        default_visibility("LARGE_DOW_TL") == "DRAW"
        and large_tl_rule.get("default_visibility") == "DRAW"
        and large_tl_rule.get("primary_structure_role") is True,
        "LARGE_DOW_TL is the primary structural TL and is drawable by default.",
    )

    turn_after_break = turn_line_role_after_small_dow_break()
    add_check(
        checks,
        "small_break_does_not_promote_turn_line",
        turn_after_break.get("promoted_to_major_line") is False
        and turn_after_break.get("line_role") == "TURN_LINE"
        and turn_rule.get("small_dow_high_break_promotes_line") is False,
        "Breaking a small-Dow high changes structure state, not TURN_LINE role.",
    )

    local_only = evaluate_rising_hierarchy(
        small_dow_high_broken=True,
        active_large_dow_high_broken=False,
    )
    add_check(
        checks,
        "local_rise_parent_not_promoted",
        local_only.state == "SMALL_DOW_RISING_PARENT_NOT_PROMOTED"
        and local_only.large_dow_promoted is False
        and local_only.next_major_resistance == "ACTIVE_LARGE_DOW_HIGH",
        "A local rise remains capped by the active large-Dow high gate.",
    )

    large_promoted = evaluate_rising_hierarchy(
        small_dow_high_broken=True,
        active_large_dow_high_broken=True,
    )
    add_check(
        checks,
        "large_dow_requires_large_gate",
        large_promoted.state == "LARGE_DOW_PROMOTED"
        and large_promoted.large_dow_promoted is True
        and (hierarchy.get("active_large_dow_high_gate") or {}).get("if_broken_state") == "LARGE_DOW_PROMOTED",
        "Large-Dow promotion is tied to the active large-Dow high gate, not the local turn line.",
    )

    high_none = StructuralHighEvidence(False, False)
    high_38 = StructuralHighEvidence(True, False)
    high_low = StructuralHighEvidence(False, True)
    high_both = StructuralHighEvidence(True, True)
    add_check(
        checks,
        "structural_high_signals_separate",
        high_none.state == "SWING_HIGH_CANDIDATE"
        and high_38.state == "STRUCTURAL_HIGH_PARTIAL"
        and high_low.state == "STRUCTURAL_HIGH_PARTIAL"
        and high_both.state == "STRUCTURAL_HIGH_CONFIRMED_STRONG",
        "38% retrace and protected-low break are stored independently; both together produce strong confirmation.",
    )

    signals = high_confirmation.get("signals_tracked_separately") or {}
    add_check(
        checks,
        "production_38_detector_not_changed",
        (signals.get("RETRACE_38_CONFIRMED") or {}).get("existing_detector_reuse") is True
        and (signals.get("RETRACE_38_CONFIRMED") or {}).get("production_detector_semantics_changed") is False,
        "Research semantics reuse the existing 38% detector evidence without weakening/changing Production detector behavior.",
    )

    add_check(
        checks,
        "unfixed_break_semantics_preserved",
        any("structural high/gate" in x and "wick" in x and "close" in x for x in unfixed)
        and any("LAST_PULLBACK_LOW" in x and "wick" in x and "close" in x for x in unfixed),
        "Wick-vs-close rules remain explicitly unfixed instead of being invented.",
    )

    add_check(
        checks,
        "research_only_no_writeback",
        adjudication.get("production_writeback") is False
        and adjudication.get("normal_run_modified") is False
        and adjudication.get("mt4_object_writeback") is False
        and adjudication.get("trade_authority") is False,
        "No Production Normal Run, MT4 object, or trade-authority writeback is permitted.",
    )

    failure_checks = [c["name"] for c in checks if not c["pass"]]
    all_pass = not failure_checks

    report = {
        "schema": "nvt7.1-usdjpy-semantic-freeze-candidate/0.1",
        "status": "PASS_CONTRACTS" if all_pass else "FAIL_CONTRACTS",
        "phase": "NVT7.1_SEMANTIC_SCOPED_FREEZE_CANDIDATE",
        "symbol_scope": "USDJPY_ONLY",
        "timeframe": "H1",
        "evidence_class": "USER_OPERATIONAL_EVIDENCE",
        "teacher_validated": False,
        "strict_nvt8_satisfied": False,
        "source_artifacts": {
            "importance_handoff_schema": importance.get("schema"),
            "batch03c_schema": batch03c.get("schema"),
            "adjudication_schema": adjudication.get("schema"),
            "batch03c_selected_case_count": batch03c.get("selected_case_count"),
            "batch03c_case_used": "USDJPY_NVT71_B03C_06",
        },
        "supersession": {
            "prior_b02_03_artifact_retained": True,
            "conflicting_line_promotion_interpretation_superseded": True,
            "superseded_items": adjudication.get("supersedes_prior_b02_03_simplifications") or [],
        },
        "frozen_semantic_candidate": {
            "line_roles": line_roles,
            "dow_hierarchy": hierarchy,
            "structural_high_confirmation": high_confirmation,
            "research_examples": {
                "turn_line_after_small_break": turn_after_break,
                "local_only_hierarchy": local_only.to_dict(),
                "large_promoted_hierarchy": large_promoted.to_dict(),
                "high_candidate": high_none.to_dict(),
                "high_partial_38_only": high_38.to_dict(),
                "high_partial_protected_low_only": high_low.to_dict(),
                "high_strong_both": high_both.to_dict(),
            },
        },
        "contract_checks": checks,
        "failure_checks": failure_checks,
        "all_contracts_pass": all_pass,
        "scoped_research_freeze_candidate": all_pass,
        "still_unfixed": unfixed,
        "interpretation": (
            "PASS_CONTRACTS freezes the current research semantics only: TURN_LINE is normally suppressed; "
            "small-Dow breakout is local structure change; large-Dow promotion requires the active large-Dow high gate; "
            "38% retrace and protected-low break are independent structural-high evidence signals. "
            "It does not fix wick-vs-close thresholds, complete automatic Dow-scale classification, strict NVT8, or Production promotion."
        ),
        "recommended_next_action": (
            "Stop B02_03 proxy-search expansion after this scoped semantic freeze candidate. "
            "Proceed to independent/held-out validation gates before any NVT9 Production promotion."
        ),
        "production_promotion_ready": False,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "check_count": len(checks),
        "failure_checks": failure_checks,
        "scoped_research_freeze_candidate": report["scoped_research_freeze_candidate"],
        "output": str(out),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
