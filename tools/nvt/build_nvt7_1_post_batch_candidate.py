from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def tf_observation(case: dict, tf: str) -> dict:
    block = (case.get("timeframes") or {}).get(tf) or {}
    analysis = block.get("analysis") or {}
    large = analysis.get("baseline_large") or {}
    mid = analysis.get("baseline_mid") or {}
    return {
        "availability": block.get("availability"),
        "active_leg": analysis.get("active_leg"),
        "baseline_large_direction": large.get("direction"),
        "baseline_large_id": large.get("candidate_id"),
        "baseline_mid_direction": mid.get("direction"),
        "baseline_mid_id": mid.get("candidate_id"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build research-only NVT7.1 lifecycle/ownership candidate from frozen NVT7 beta plus USDJPY historical user adjudication."
    )
    ap.add_argument("--scoped-beta", required=True)
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--historical-bundle", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    scoped = load_json(args.scoped_beta)
    adjudication = load_json(args.adjudication)
    bundle = load_json(args.historical_bundle)

    if scoped.get("schema") != "nvt7-lifecycle-scoped-beta/1.0":
        raise ValueError("unexpected scoped NVT7 beta schema")
    if adjudication.get("schema") != "nvt8h-usdjpy-user-adjudication/0.1":
        raise ValueError("unexpected adjudication schema")
    if bundle.get("schema") != "nvt8h-usdjpy-historical-review-bundle/0.2":
        raise ValueError("unexpected historical review bundle schema")
    if bundle.get("symbol_scope") != "USDJPY_ONLY":
        raise ValueError("NVT7.1 post-batch candidate currently supports USDJPY only")

    cases = {c.get("case_id"): c for c in bundle.get("cases") or []}
    required_case_ids = [f"USDJPY_HIST_{i:02d}" for i in range(1, 9)]
    missing = [cid for cid in required_case_ids if cid not in cases]
    if missing:
        raise ValueError(f"missing historical cases: {missing}")

    judged = adjudication.get("cases") or {}
    for cid in ["USDJPY_HIST_03", "USDJPY_HIST_07", "USDJPY_HIST_08"]:
        if cid not in judged:
            raise ValueError(f"missing required user adjudication: {cid}")

    # Preserve the frozen teacher/development-supported NVT7 scope unchanged.
    frozen_market_states = scoped.get("market_lifecycle_states") or {}
    frozen_filters = scoped.get("observation_filter_states") or {}
    frozen_transitions = scoped.get("frozen_market_time_transitions") or []
    frozen_rules = scoped.get("semantic_rules_frozen") or []

    # New rules are deliberately USER_OPERATIONAL_EVIDENCE only. They are candidates for
    # historical regression; they do not rewrite the already frozen NVT7 beta.
    post_batch_rules = [
        {
            "rule_id": "PB01_BREAK_NOT_DIRECTION_FLIP",
            "evidence_case": "USDJPY_HIST_03",
            "evidence_class": "USER_OPERATIONAL_EVIDENCE",
            "rule": "A TL break alone does not flip the parent timeframe direction. For a rising parent structure, do not promote a descending parent-TL state without meaningful structure confirmation; a meaningful lower-low update is required at minimum in this observed case.",
            "visibility_effect": "KEEP_EXISTING_PARENT_TL_CH_WHILE_STILL_STRUCTURALLY_USEFUL",
            "optional_auxiliary": "SMALL_DOW_BR_LINE_MAY_COEXIST_WITHOUT_PARENT_DIRECTION_FLIP",
            "numeric_threshold_fixed": False,
        },
        {
            "rule_id": "PB01_REFERENCE_RETIRE_BY_SUBSUMPTION",
            "evidence_case": "USDJPY_HIST_07",
            "evidence_class": "USER_OPERATIONAL_EVIDENCE",
            "rule": "REFERENCE_RETAINED is conditional, not permanent. An old reference may retire when a later valid line captures the structure more broadly; recency alone is insufficient, and a gentler broad-structure line may outlive a steeper interim redraw.",
            "candidate_state": "RETIRED_REFERENCE",
            "retire_trigger": "STRUCTURAL_SUBSUMPTION_OR_BROADER_VALID_REPLACEMENT",
            "forbidden_trigger": "NEWEST_LINE_ONLY",
            "numeric_threshold_fixed": False,
        },
        {
            "rule_id": "PB01_VISIBILITY_DECISION_OWNER_DECOUPLED",
            "evidence_case": "USDJPY_HIST_08",
            "evidence_class": "USER_OPERATIONAL_EVIDENCE",
            "rule": "A lower-timeframe line may remain visible after its decision authority is lost. When H1 and H4 TLs are broken in the observed case, keep prior lines for context while escalating primary decision ownership to D1 TL.",
            "decision_owner": "D1_TL",
            "visibility_policy": "LOWER_TF_LINES_MAY_REMAIN_VISIBLE_FOR_CONTEXT",
            "immediate_delete_required": False,
            "new_h1_descending_tl_required_for_primary_decision": False,
        },
    ]

    case_contracts = {
        "USDJPY_HIST_03": {
            "expected_parent_h1_direction_flip": False,
            "expected_draw_parent_h1_descending_tl": False,
            "expected_existing_h1_tl_ch": "RETAIN",
            "small_dow_br_line": "OPTIONAL",
            "observed": {
                "D1": tf_observation(cases["USDJPY_HIST_03"], "D1"),
                "H4": tf_observation(cases["USDJPY_HIST_03"], "H4"),
                "H1": tf_observation(cases["USDJPY_HIST_03"], "H1"),
            },
        },
        "USDJPY_HIST_07": {
            "expected_old_reference_initially_retained_after_break": True,
            "expected_reanchor_allowed": True,
            "expected_retire_allowed_after_broader_replacement": True,
            "expected_newest_only_delete": False,
            "gentler_vs_steeper": "BROADER_GENTLER_LINE_MAY_OUTLIVE_STEEPER_INTERIM_REDRAW",
            "observed": {
                "D1": tf_observation(cases["USDJPY_HIST_07"], "D1"),
                "H4": tf_observation(cases["USDJPY_HIST_07"], "H4"),
                "H1": tf_observation(cases["USDJPY_HIST_07"], "H1"),
            },
        },
        "USDJPY_HIST_08": {
            "expected_prior_lines_visible_for_now": True,
            "expected_h1_decision_owner": False,
            "expected_h4_decision_owner": False,
            "expected_primary_decision_owner": "D1_TL",
            "expected_immediate_delete": False,
            "expected_new_h1_descending_tl_required_for_primary_decision": False,
            "observed": {
                "D1": tf_observation(cases["USDJPY_HIST_08"], "D1"),
                "H4": tf_observation(cases["USDJPY_HIST_08"], "H4"),
                "H1": tf_observation(cases["USDJPY_HIST_08"], "H1"),
            },
        },
    }

    untouched = [cid for cid in required_case_ids if cid not in case_contracts]
    report = {
        "schema": "nvt7.1-post-batch-lifecycle-ownership-candidate/0.1",
        "status": "RESEARCH_ONLY_USER_OPERATIONAL_EVIDENCE",
        "phase": "NVT7.1_POST_BATCH_CANDIDATE",
        "symbol_scope": "USDJPY_ONLY",
        "source_scoped_beta_schema": scoped.get("schema"),
        "source_adjudication_schema": adjudication.get("schema"),
        "source_historical_bundle_schema": bundle.get("schema"),
        "original_nvt7_frozen_scope_preserved": {
            "market_lifecycle_states": frozen_market_states,
            "observation_filter_states": frozen_filters,
            "frozen_market_time_transitions": frozen_transitions,
            "semantic_rules_frozen": frozen_rules,
        },
        "post_batch_candidate_rules": post_batch_rules,
        "new_candidate_state": {
            "RETIRED_REFERENCE": {
                "evidence_class": "USER_OPERATIONAL_EVIDENCE_ONLY",
                "meaning": "Previously useful reference is no longer displayed/active after a structurally broader valid replacement subsumes its role.",
                "teacher_validated": False,
                "automatic_trigger_fixed": False,
            }
        },
        "decision_ownership_candidate": {
            "dimension_separate_from_visibility": True,
            "owner_values": ["H1", "H4", "D1"],
            "observed_escalation": "H1/H4_BROKEN -> D1_TL_PRIMARY_DECISION_OWNER",
            "evidence_case": "USDJPY_HIST_08",
            "automatic_generalization_fixed": False,
        },
        "historical_case_contracts": case_contracts,
        "unadjudicated_cases_no_new_label": untouched,
        "guardrails": [
            "Do not modify the original NVT7 scoped beta in place.",
            "Do not infer a direction flip from TL break alone.",
            "Do not retire a reference because a newer line merely exists.",
            "Do not equate line visibility with decision ownership.",
            "Do not promote these user-operational rules to teacher-validated or production-ready status.",
        ],
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
        "status": "PASS",
        "output": str(out),
        "post_batch_rule_count": len(post_batch_rules),
        "adjudicated_case_count": len(case_contracts),
        "unadjudicated_case_count": len(untouched),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
