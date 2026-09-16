from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Regression-test the frozen NVT7 scoped lifecycle beta.")
    ap.add_argument("--scoped-beta", required=True)
    ap.add_argument("--sequential-regression", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    scoped = load_json(args.scoped_beta)
    seq = load_json(args.sequential_regression)

    if scoped.get("schema") != "nvt7-lifecycle-scoped-beta/1.0":
        raise ValueError("unexpected scoped beta schema")
    if seq.get("schema") != "nvt7-sequential-regression/0.1":
        raise ValueError("unexpected sequential regression schema")

    states = scoped.get("market_lifecycle_states") or {}
    filters = scoped.get("observation_filter_states") or {}
    transitions = scoped.get("frozen_market_time_transitions") or []
    rules = set(scoped.get("semantic_rules_frozen") or [])
    events = {x.get("event") for x in transitions}
    deferred = scoped.get("deferred_not_frozen") or {}

    checks = [
        {
            "name": "dev_sequential_regression_pass",
            "pass": seq.get("all_contracts_pass") is True,
            "detail": "Original NVT7 development contracts must remain PASS.",
        },
        {
            "name": "current_state_frozen",
            "pass": "CURRENT_ACTIVE" in states,
            "detail": "CURRENT_ACTIVE must be frozen in scoped beta.",
        },
        {
            "name": "reference_state_frozen",
            "pass": "REFERENCE_RETAINED" in states,
            "detail": "REFERENCE_RETAINED must be frozen in scoped beta.",
        },
        {
            "name": "suppressed_state_semantics_frozen",
            "pass": "VALID_SUPPRESSED" in states and states.get("VALID_SUPPRESSED", {}).get("candidate_valid") is True and states.get("VALID_SUPPRESSED", {}).get("visible") is False,
            "detail": "GT_0005 validity/visibility semantics must remain explicit.",
        },
        {
            "name": "transient_is_filter_not_market_state",
            "pass": "EDIT_TRANSIENT" in filters and "EDIT_TRANSIENT" not in states,
            "detail": "Transient video edits must not become a stable market-time lifecycle state.",
        },
        {
            "name": "update_keep_reference_transition_frozen",
            "pass": "UPDATE_AND_KEEP_REFERENCE" in events,
            "detail": "GT_0002 market-time update+reference retention must be frozen.",
        },
        {
            "name": "restore_reference_transition_frozen",
            "pass": "RESTORE_PERSISTENT_REFERENCE" in events,
            "detail": "GT_0004 persistent-reference restoration must be frozen.",
        },
        {
            "name": "gt0005_numeric_trigger_not_invented",
            "pass": deferred.get("gt0005_automatic_suppression_trigger") is not None and "SUPPRESS_VALID_SHORT_LIVED" not in events,
            "detail": "VALID_SUPPRESSED is frozen semantically, while its numeric auto-trigger remains deferred.",
        },
        {
            "name": "gt0006_market_time_order_not_invented",
            "pass": deferred.get("gt0006_market_time_reanchor_order") is not None and "REANCHOR_CURRENT_WITHOUT_DEFAULT_DELETE" not in events,
            "detail": "GT_0006 video edit sequence must not be frozen as market-time order.",
        },
        {
            "name": "delete_retire_not_invented",
            "pass": deferred.get("retired_delete_behavior") is None,
            "detail": "No unsupported RETIRED/DELETE transition is introduced.",
        },
        {
            "name": "no_default_reference_delete_rule_preserved",
            "pass": "Updating current geometry does not delete an older useful reference by default." in rules,
            "detail": "Old useful references remain protected from newest-only deletion.",
        },
        {
            "name": "scoped_freeze_flag",
            "pass": scoped.get("scoped_beta_freeze_ready") is True,
            "detail": "Scoped beta must explicitly declare freeze readiness.",
        },
    ]

    failures = [x["name"] for x in checks if not x["pass"]]
    report = {
        "schema": "nvt7-frozen-scope-regression/1.0",
        "status": "PASS" if not failures else "FAIL",
        "phase": "NVT7-6_FROZEN_SCOPE_REGRESSION",
        "checks": checks,
        "failure_checks": failures,
        "all_checks_pass": not failures,
        "nvt7_scoped_beta_frozen": not failures,
        "held_out_validation_ready": not failures,
        "held_out_scope": [
            "current update with retained useful reference",
            "persistent reference may outrank newer re-anchor for monitoring",
            "validity and visibility are separate; VALID_SUPPRESSED semantics",
            "transient video edits excluded from stable lifecycle evidence",
        ],
        "not_in_held_out_scope_yet": [
            "numeric automatic suppression threshold for GT_0005-like short-lived lines",
            "GT_0006 market-time re-anchor ordering derived from video drag order",
            "RETIRED/DELETE transition semantics",
            "production promotion or production MT4 rendering",
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
        "status": report["status"],
        "output": str(out),
        "check_count": len(checks),
        "failure_count": len(failures),
        "nvt7_scoped_beta_frozen": report["nvt7_scoped_beta_frozen"],
        "held_out_validation_ready": report["held_out_validation_ready"],
    }, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
