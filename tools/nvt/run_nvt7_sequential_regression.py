from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "pass": bool(passed), "detail": detail}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run research-only NVT7 lifecycle sequential regression contracts.")
    ap.add_argument("--graph", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    graph = load_json(args.graph)
    if graph.get("schema") != "nvt7-event-state-graph/0.1":
        raise ValueError("unexpected event/state graph schema")

    states = graph.get("states") or {}
    edges = {e.get("case_id"): e for e in (graph.get("edges") or [])}
    video = {v.get("observation_id"): v for v in (graph.get("gt0006_video_state_mapping") or [])}

    results: dict[str, dict] = {}

    gt2_checks = [
        check("current_state_exists", "CURRENT_ACTIVE" in states, "CURRENT_ACTIVE must exist."),
        check("reference_state_exists", "REFERENCE_RETAINED" in states, "REFERENCE_RETAINED must exist."),
        check(
            "update_keeps_reference",
            set((edges.get("GT_0002") or {}).get("to_states") or []) == {"REANCHORED_CURRENT", "REFERENCE_RETAINED"},
            "GT_0002 must update current while retaining an older useful reference.",
        ),
        check(
            "no_default_delete",
            (edges.get("GT_0002") or {}).get("delete_previous_by_default") is False,
            "GT_0002 must not delete the prior useful reference just because current geometry updates.",
        ),
    ]
    results["GT_0002"] = {"checks": gt2_checks, "pass": all(x["pass"] for x in gt2_checks)}

    gt4_checks = [
        check("reference_state_exists", "REFERENCE_RETAINED" in states, "Persistent reference state must exist."),
        check(
            "restore_reference_edge",
            (edges.get("GT_0004") or {}).get("to_states") == ["REFERENCE_RETAINED"],
            "GT_0004 must be able to restore/keep the persistent monitoring reference.",
        ),
        check(
            "newest_not_forced",
            (edges.get("GT_0004") or {}).get("delete_previous_by_default") is False,
            "Newest re-anchor must not automatically displace the persistent reference.",
        ),
    ]
    results["GT_0004"] = {"checks": gt4_checks, "pass": all(x["pass"] for x in gt4_checks)}

    suppressed = states.get("VALID_SUPPRESSED") or {}
    gt5_checks = [
        check("suppressed_state_exists", bool(suppressed), "VALID_SUPPRESSED must exist."),
        check("suppressed_stays_valid", suppressed.get("candidate_valid") is True, "Suppressed line remains structurally valid."),
        check("suppressed_is_hidden", suppressed.get("visible") is False, "Display suppression must be represented independently of validity."),
        check(
            "suppression_transition",
            (edges.get("GT_0005") or {}).get("to_states") == ["VALID_SUPPRESSED"],
            "GT_0005 must transition a valid candidate to display-suppressed state.",
        ),
    ]
    results["GT_0005"] = {"checks": gt5_checks, "pass": all(x["pass"] for x in gt5_checks)}

    v1 = video.get("V1_GENTLE_FAMILY") or {}
    v2 = video.get("V2_TRANSIENT_OR_DIFFERENT_GEOMETRY") or {}
    v3 = video.get("V3_STEEPER_STATE") or {}
    v4 = video.get("V4_LATER_HIGH_REANCHOR_STATE") or {}
    gt6_edge = edges.get("GT_0006") or {}
    gt6_checks = [
        check(
            "v2_transient_excluded",
            v2.get("mapped_lifecycle_state") == "EDIT_TRANSIENT" and v2.get("stable_for_market_lifecycle_training") is False,
            "Transient drag/edit evidence must not become a stable market-time lifecycle state.",
        ),
        check(
            "stable_samples_retained",
            all(v.get("stable_for_market_lifecycle_training") is True for v in [v1, v3, v4]),
            "V1/V3/V4 stable geometry observations remain available as lifecycle evidence.",
        ),
        check(
            "market_time_order_not_claimed",
            gt6_edge.get("market_time_transition_supported") is False,
            "Video edit order must not be promoted to market-time transition order.",
        ),
        check(
            "no_default_delete",
            gt6_edge.get("delete_previous_by_default") is False,
            "Re-anchor evidence does not prove that prior useful structures should be deleted.",
        ),
    ]
    results["GT_0006"] = {"checks": gt6_checks, "pass": all(x["pass"] for x in gt6_checks)}

    overall = all(v["pass"] for v in results.values())
    unresolved = list(graph.get("unresolved") or [])

    report = {
        "schema": "nvt7-sequential-regression/0.1",
        "status": "RESEARCH_ONLY",
        "phase": "NVT7-3_SEQUENTIAL_REGRESSION",
        "case_results": results,
        "all_contracts_pass": overall,
        "regression_failure_cases": [k for k, v in results.items() if not v["pass"]],
        "guards_preserved": {
            "latest_is_not_automatically_best": True,
            "validity_and_visibility_are_separate": True,
            "transient_edit_not_stable_market_state": True,
            "video_edit_order_not_market_time_order": True,
            "old_reference_not_deleted_by_default": True,
        },
        "unresolved": unresolved,
        "beta_candidate_can_be_built": overall,
        "beta_freeze_ready": False,
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
        "status": "PASS" if overall else "FAIL",
        "output": str(out),
        "all_contracts_pass": overall,
        "regression_failure_cases": report["regression_failure_cases"],
        "beta_candidate_can_be_built": overall,
        "beta_freeze_ready": False,
    }, ensure_ascii=False, indent=2))
    return 0 if overall else 2


if __name__ == "__main__":
    raise SystemExit(main())
