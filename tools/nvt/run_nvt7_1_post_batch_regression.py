from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_rule(candidate: dict, rule_id: str) -> dict | None:
    for rule in candidate.get("post_batch_candidate_rules") or []:
        if rule.get("rule_id") == rule_id:
            return rule
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Regression-check the research-only NVT7.1 USDJPY post-batch candidate.")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    candidate = load_json(args.candidate)
    if candidate.get("schema") != "nvt7.1-post-batch-lifecycle-ownership-candidate/0.1":
        raise ValueError("unexpected NVT7.1 candidate schema")

    original = candidate.get("original_nvt7_frozen_scope_preserved") or {}
    contracts = candidate.get("historical_case_contracts") or {}
    untouched = candidate.get("unadjudicated_cases_no_new_label") or []

    r_break = find_rule(candidate, "PB01_BREAK_NOT_DIRECTION_FLIP") or {}
    r_retire = find_rule(candidate, "PB01_REFERENCE_RETIRE_BY_SUBSUMPTION") or {}
    r_owner = find_rule(candidate, "PB01_VISIBILITY_DECISION_OWNER_DECOUPLED") or {}

    c03 = contracts.get("USDJPY_HIST_03") or {}
    c07 = contracts.get("USDJPY_HIST_07") or {}
    c08 = contracts.get("USDJPY_HIST_08") or {}

    h03 = ((c03.get("observed") or {}).get("H1") or {})
    h08_d1 = ((c08.get("observed") or {}).get("D1") or {})
    h08_h4 = ((c08.get("observed") or {}).get("H4") or {})
    h08_h1 = ((c08.get("observed") or {}).get("H1") or {})

    expected_untouched = {
        "USDJPY_HIST_01",
        "USDJPY_HIST_02",
        "USDJPY_HIST_04",
        "USDJPY_HIST_05",
        "USDJPY_HIST_06",
    }

    checks = [
        {
            "name": "original_frozen_scope_preserved",
            "pass": bool(original.get("market_lifecycle_states")) and bool(original.get("semantic_rules_frozen")),
            "detail": "NVT7.1 must layer new user-operational hypotheses on top of, not overwrite, the frozen NVT7 scoped beta.",
        },
        {
            "name": "three_post_batch_rules_present",
            "pass": all([r_break, r_retire, r_owner]),
            "detail": "Break/direction, structural retirement, and decision-ownership separation rules must all be present.",
        },
        {
            "name": "hist03_active_leg_does_not_override_parent_structure",
            "pass": (
                h03.get("active_leg") == "FALLING"
                and h03.get("baseline_large_direction") == "RISING"
                and h03.get("baseline_mid_direction") == "RISING"
                and c03.get("expected_parent_h1_direction_flip") is False
                and c03.get("expected_draw_parent_h1_descending_tl") is False
            ),
            "detail": "HIST03 is the key conflict case: local active leg can be FALLING while retained parent H1 TL/CH remains RISING; no parent H1 downtrend flip is allowed from the break alone.",
        },
        {
            "name": "hist03_optional_small_dow_is_separate",
            "pass": c03.get("small_dow_br_line") == "OPTIONAL",
            "detail": "Optional small-Dow BR drawing must not promote the parent H1 structure to downtrend.",
        },
        {
            "name": "hist07_reference_not_permanent_but_not_newest_only",
            "pass": (
                c07.get("expected_old_reference_initially_retained_after_break") is True
                and c07.get("expected_retire_allowed_after_broader_replacement") is True
                and c07.get("expected_newest_only_delete") is False
                and r_retire.get("forbidden_trigger") == "NEWEST_LINE_ONLY"
            ),
            "detail": "HIST07 permits retirement only after structural replacement/subsumption; a newer line alone cannot delete the old reference.",
        },
        {
            "name": "hist07_gentle_broad_line_can_outlive_steep_redraw",
            "pass": c07.get("gentler_vs_steeper") == "BROADER_GENTLER_LINE_MAY_OUTLIVE_STEEPER_INTERIM_REDRAW",
            "detail": "The post-batch model preserves the user's observation that a gentler broad-structure line may outlive a steeper interim redraw.",
        },
        {
            "name": "hist08_visibility_and_decision_owner_are_separate",
            "pass": (
                c08.get("expected_prior_lines_visible_for_now") is True
                and c08.get("expected_primary_decision_owner") == "D1_TL"
                and c08.get("expected_immediate_delete") is False
                and (candidate.get("decision_ownership_candidate") or {}).get("dimension_separate_from_visibility") is True
            ),
            "detail": "HIST08 keeps prior lower-TF lines for context while moving primary decision authority to D1.",
        },
        {
            "name": "hist08_observed_structure_supports_escalation_case",
            "pass": (
                h08_d1.get("active_leg") == "FALLING"
                and h08_h4.get("active_leg") == "FALLING"
                and h08_h1.get("active_leg") == "FALLING"
            ),
            "detail": "At the HIST08 cutoff the mechanical active-leg view is falling across D1/H4/H1; the user still retains old lines but uses D1 as the decision owner.",
        },
        {
            "name": "hist08_new_h1_down_tl_not_required_for_primary_decision",
            "pass": c08.get("expected_new_h1_descending_tl_required_for_primary_decision") is False,
            "detail": "Primary judgment can escalate to D1 without requiring a new H1 descending TL immediately.",
        },
        {
            "name": "five_unadjudicated_cases_not_relabelled",
            "pass": set(untouched) == expected_untouched,
            "detail": "HIST01/02/04/05/06 remain unlabeled by the new post-batch rules; they are not silently converted into positive validation cases.",
        },
        {
            "name": "retired_reference_is_candidate_not_frozen_teacher_rule",
            "pass": (
                ((candidate.get("new_candidate_state") or {}).get("RETIRED_REFERENCE") or {}).get("teacher_validated") is False
                and ((candidate.get("new_candidate_state") or {}).get("RETIRED_REFERENCE") or {}).get("automatic_trigger_fixed") is False
            ),
            "detail": "RETIRED_REFERENCE is supported only by user operational evidence at this stage, so no teacher/production claim is allowed.",
        },
        {
            "name": "production_untouched",
            "pass": (
                candidate.get("production_writeback") is False
                and candidate.get("normal_run_modified") is False
                and candidate.get("mt4_object_writeback") is False
            ),
            "detail": "NVT7.1 remains research-only and must not change Production Normal Run or MT4 objects.",
        },
    ]

    failures = [x["name"] for x in checks if not x["pass"]]
    report = {
        "schema": "nvt7.1-usdjpy-post-batch-regression/0.1",
        "status": "PASS_CONTRACTS" if not failures else "FAIL_CONTRACTS",
        "phase": "NVT7.1_POST_BATCH_HISTORICAL_REGRESSION",
        "symbol_scope": "USDJPY_ONLY",
        "evidence_class": "USER_OPERATIONAL_EVIDENCE",
        "checks": checks,
        "failure_checks": failures,
        "all_contracts_pass": not failures,
        "interpretation": (
            "PASS_CONTRACTS means the research candidate reproduces the recorded HIST03/HIST07/HIST08 user adjudication without overwriting the frozen NVT7 beta and without relabeling unadjudicated cases. It is not strict NVT8 held-out or production validation."
        ),
        "what_changed_vs_frozen_nvt7": [
            "TL break and parent direction flip are separated.",
            "REFERENCE_RETAINED gains a user-evidence retirement candidate based on structural subsumption rather than recency.",
            "Line visibility and decision-timeframe ownership are modeled as separate dimensions.",
        ],
        "still_unfixed": [
            "Objective numeric threshold for meaningful lower-low / direction-flip confirmation.",
            "Objective numeric threshold for structural subsumption and broad/gentle replacement.",
            "General decision-owner escalation rule beyond the adjudicated HIST08 pattern.",
            "Teacher-video validation of RETIRED_REFERENCE behavior.",
        ],
        "recommended_next_research_action": (
            "Keep the original NVT7 scoped beta frozen. Use NVT7.1 only as a research candidate and test the three new contracts on additional USDJPY historical cutoffs before considering any freeze amendment."
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
        "output": str(out),
        "check_count": len(checks),
        "failure_count": len(failures),
        "all_contracts_pass": report["all_contracts_pass"],
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
