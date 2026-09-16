from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build research-only NVT7 lifecycle beta candidate after sequential regression.")
    ap.add_argument("--graph", required=True)
    ap.add_argument("--regression", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    graph = load_json(args.graph)
    regression = load_json(args.regression)

    if graph.get("schema") != "nvt7-event-state-graph/0.1":
        raise ValueError("unexpected event/state graph schema")
    if regression.get("schema") != "nvt7-sequential-regression/0.1":
        raise ValueError("unexpected sequential regression schema")
    if regression.get("all_contracts_pass") is not True:
        raise ValueError("cannot build beta candidate while sequential regression fails")

    state_names = [
        "CURRENT_ACTIVE",
        "REFERENCE_RETAINED",
        "VALID_SUPPRESSED",
        "EDIT_TRANSIENT",
        "REANCHORED_CURRENT",
    ]
    states = {name: (graph.get("states") or {}).get(name) for name in state_names}

    transition_names = {
        "GT_0002": "UPDATE_AND_KEEP_REFERENCE",
        "GT_0004": "RESTORE_PERSISTENT_REFERENCE",
        "GT_0005": "SUPPRESS_VALID_SHORT_LIVED",
        "GT_0006": "REANCHOR_CURRENT_WITHOUT_DEFAULT_DELETE",
    }
    edges = graph.get("edges") or []
    selected_edges = []
    for case_id, event_name in transition_names.items():
        for edge in edges:
            if edge.get("case_id") == case_id and edge.get("event") == event_name:
                selected_edges.append(edge)
                break

    unresolved = list(dict.fromkeys((graph.get("unresolved") or []) + (regression.get("unresolved") or [])))

    report = {
        "schema": "nvt7-lifecycle-beta-candidate/0.1",
        "status": "RESEARCH_ONLY_NOT_FROZEN",
        "phase": "NVT7-4_BETA_CANDIDATE",
        "state_model_candidate": states,
        "transition_model_candidate": selected_edges,
        "semantic_rules_candidate": [
            "Validity and visibility are separate dimensions.",
            "Updating current geometry does not delete an older useful reference by default.",
            "Newest geometry is not automatically the preferred monitoring reference.",
            "Transient video drag/edit samples are excluded from stable market-time lifecycle training.",
            "Same MT4 object name may represent multiple geometry states over an edit sequence.",
            "GT_0006 video edit order must not be interpreted as market-time transition order without separate evidence.",
        ],
        "case_coverage": {
            "GT_0002": "current update + retained reference",
            "GT_0004": "persistent monitoring reference over newer re-anchor",
            "GT_0005": "valid but display-suppressed short-lived turn line",
            "GT_0006": "selector-to-lifecycle bridge; stable vs transient geometry states",
        },
        "sequential_regression_pass": True,
        "freeze_blockers": unresolved,
        "beta_freeze_ready": len(unresolved) == 0,
        "held_out_validation_ready": False,
        "next_required_action": (
            "Resolve freeze blockers and then run a frozen NVT7 sequential regression; only after that proceed to NVT8 held-out validation."
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
        "status": "PASS",
        "output": str(out),
        "state_count": len([v for v in states.values() if v is not None]),
        "transition_count": len(selected_edges),
        "freeze_blocker_count": len(unresolved),
        "beta_freeze_ready": report["beta_freeze_ready"],
        "held_out_validation_ready": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
