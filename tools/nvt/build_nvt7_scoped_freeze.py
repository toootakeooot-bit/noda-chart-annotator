from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Freeze the evidence-supported NVT7 lifecycle subset while explicitly deferring unsupported triggers/transitions."
    )
    ap.add_argument("--beta-candidate", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    beta = load_json(args.beta_candidate)
    if beta.get("schema") != "nvt7-lifecycle-beta-candidate/0.1":
        raise ValueError("unexpected beta candidate schema")
    if beta.get("sequential_regression_pass") is not True:
        raise ValueError("cannot scope-freeze NVT7 before sequential regression passes")

    states = beta.get("state_model_candidate") or {}
    edges = beta.get("transition_model_candidate") or []

    required_states = [
        "CURRENT_ACTIVE",
        "REFERENCE_RETAINED",
        "VALID_SUPPRESSED",
        "EDIT_TRANSIENT",
        "REANCHORED_CURRENT",
    ]
    missing_states = [name for name in required_states if not states.get(name)]
    if missing_states:
        raise ValueError(f"missing required candidate states: {missing_states}")

    edge_by_event = {edge.get("event"): edge for edge in edges}
    required_frozen_events = [
        "UPDATE_AND_KEEP_REFERENCE",
        "RESTORE_PERSISTENT_REFERENCE",
    ]
    missing_edges = [name for name in required_frozen_events if name not in edge_by_event]
    if missing_edges:
        raise ValueError(f"missing evidence-supported lifecycle transitions: {missing_edges}")

    # Freeze only rules that are already supported as market-time lifecycle evidence.
    frozen_transitions = [edge_by_event[name] for name in required_frozen_events]

    # Keep GT_0005 state semantics, but defer its quantitative automatic trigger.
    suppressed_edge = edge_by_event.get("SUPPRESS_VALID_SHORT_LIVED")
    # Keep GT_0006 as a video-edit guard only; do not freeze video edit order as market-time transition order.
    gt6_edge = edge_by_event.get("REANCHOR_CURRENT_WITHOUT_DEFAULT_DELETE")

    source_blockers = beta.get("freeze_blockers") or []
    deferred = []
    for blocker in source_blockers:
        if blocker == "Exact market-time sequence for GT_0006 re-anchor states.":
            disposition = "DEFER_TRANSITION_ORDER_OUT_OF_SCOPE"
            rationale = "GT_0006 proves multiple geometry/edit states, but not their market-time transition order."
        elif blocker == "Objective threshold for GT_0005 short-lived/display suppression.":
            disposition = "DEFER_AUTOMATIC_TRIGGER_OUT_OF_SCOPE"
            rationale = "Freeze validity/visibility separation and VALID_SUPPRESSED semantics, not a numeric suppression threshold."
        elif blocker == "Explicit RETIRED/DELETE transition evidence.":
            disposition = "OMIT_UNSUPPORTED_STATE_AND_TRANSITION"
            rationale = "NVT7 v1 does not invent RETIRED/DELETE behavior without teacher evidence; prior useful references are not deleted by default."
        elif blocker == "Exact anchor locks for DRAFT cases where still pending.":
            disposition = "DEFER_TO_BEHAVIOR_SPECIFIC_LOCK_AND_PROMOTION_GATE"
            rationale = "The scoped lifecycle semantic model does not depend on exact geometric anchors; NVT9 promotion still requires REVIEWED/LOCKED Ground Truth for promoted behavior."
        else:
            disposition = "UNCLASSIFIED_BLOCKER"
            rationale = "Unexpected blocker requires audit before freeze."
        deferred.append({
            "blocker": blocker,
            "disposition": disposition,
            "rationale": rationale,
        })

    unclassified = [x for x in deferred if x["disposition"] == "UNCLASSIFIED_BLOCKER"]

    report = {
        "schema": "nvt7-lifecycle-scoped-beta/1.0",
        "status": "FROZEN_RESEARCH_SCOPE" if not unclassified else "NOT_FROZEN_UNCLASSIFIED_BLOCKER",
        "phase": "NVT7-5_SCOPED_BETA_FREEZE",
        "scope_statement": (
            "Freeze only evidence-supported lifecycle semantics and market-time transitions. "
            "Do not invent unresolved automatic thresholds, delete/retire behavior, or GT_0006 market-time edit ordering."
        ),
        "market_lifecycle_states": {
            name: states[name]
            for name in ["CURRENT_ACTIVE", "REFERENCE_RETAINED", "VALID_SUPPRESSED", "REANCHORED_CURRENT"]
        },
        "observation_filter_states": {
            "EDIT_TRANSIENT": states["EDIT_TRANSIENT"],
        },
        "frozen_market_time_transitions": frozen_transitions,
        "semantic_rules_frozen": [
            "Validity and visibility are separate dimensions.",
            "Updating current geometry does not delete an older useful reference by default.",
            "Newest geometry is not automatically the preferred monitoring reference.",
            "Transient video drag/edit samples are excluded from stable market-time lifecycle training.",
            "Same MT4 object name does not imply one immutable geometry.",
        ],
        "deferred_not_frozen": {
            "gt0005_automatic_suppression_trigger": suppressed_edge,
            "gt0006_market_time_reanchor_order": gt6_edge,
            "retired_delete_behavior": None,
        },
        "blocker_dispositions": deferred,
        "unclassified_blocker_count": len(unclassified),
        "scoped_beta_freeze_ready": len(unclassified) == 0,
        "held_out_validation_ready_for_scoped_rules": len(unclassified) == 0,
        "production_promotion_ready": False,
        "promotion_guard": (
            "NVT8 held-out validation, Normal Run regression, MT4 verification, and behavior-specific REVIEWED/LOCKED Ground Truth remain required before NVT9 promotion."
        ),
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": "PASS" if report["scoped_beta_freeze_ready"] else "BLOCKED",
        "output": str(out),
        "frozen_state_count": len(report["market_lifecycle_states"]),
        "observation_filter_state_count": len(report["observation_filter_states"]),
        "frozen_transition_count": len(frozen_transitions),
        "deferred_blocker_count": len(deferred),
        "unclassified_blocker_count": len(unclassified),
        "scoped_beta_freeze_ready": report["scoped_beta_freeze_ready"],
        "held_out_validation_ready_for_scoped_rules": report["held_out_validation_ready_for_scoped_rules"],
    }, ensure_ascii=False, indent=2))

    return 0 if report["scoped_beta_freeze_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
