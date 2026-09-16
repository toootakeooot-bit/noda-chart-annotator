from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require_case(cases: dict[str, dict], case_id: str) -> dict:
    if case_id not in cases:
        raise ValueError(f"missing required case: {case_id}")
    return cases[case_id]


def main() -> int:
    ap = argparse.ArgumentParser(description="Finalize research-only NVT7.1 USDJPY Batch02 user adjudication and run contract checks.")
    ap.add_argument("--batch01-handoff", required=True)
    ap.add_argument("--batch02-targeted", required=True)
    ap.add_argument("--batch02-adjudication", required=True)
    ap.add_argument("--b02-03-importance", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    batch01 = load_json(args.batch01_handoff)
    batch02 = load_json(args.batch02_targeted)
    adjud = load_json(args.batch02_adjudication)
    importance = load_json(args.b02_03_importance)

    if batch01.get("schema") != "nvt7.1-usdjpy-post-batch-handoff/0.1":
        raise ValueError("unexpected Batch01 handoff schema")
    if batch02.get("schema") != "nvt7.1-usdjpy-targeted-historical-review/0.1":
        raise ValueError("unexpected Batch02 targeted-review schema")
    if adjud.get("schema") != "nvt7.1-usdjpy-user-adjudication-batch02/0.1":
        raise ValueError("unexpected Batch02 adjudication schema")

    targeted_cases = {c.get("case_id"): c for c in batch02.get("cases") or []}
    judged = adjud.get("cases") or {}
    c03 = require_case(targeted_cases, "USDJPY_NVT71_B02_03")
    c04 = require_case(targeted_cases, "USDJPY_NVT71_B02_04")
    c05 = require_case(targeted_cases, "USDJPY_NVT71_B02_05")
    j03 = require_case(judged, "USDJPY_NVT71_B02_03")
    j04 = require_case(judged, "USDJPY_NVT71_B02_04")
    j05 = require_case(judged, "USDJPY_NVT71_B02_05")

    checks: dict[str, bool] = {}
    checks["batch01_contracts_passed"] = batch01.get("status") == "PASS_CONTRACTS"
    checks["batch01_original_scoped_beta_unchanged"] = batch01.get("original_nvt7_scoped_beta_unchanged") is True
    checks["batch02_future_hidden"] = bool((batch02.get("selection_policy") or {}).get("future_hidden")) and all(
        c.get("future_bars_included") is False for c in batch02.get("cases") or []
    )
    checks["b02_03_has_reference_review_pattern"] = "REFERENCE_REANCHOR_RETIRE_REVIEW_CANDIDATE" in (c03.get("target_patterns") or [])
    checks["b02_04_has_reference_review_pattern"] = "REFERENCE_REANCHOR_RETIRE_REVIEW_CANDIDATE" in (c04.get("target_patterns") or [])
    checks["b02_05_has_reference_review_pattern"] = "REFERENCE_REANCHOR_RETIRE_REVIEW_CANDIDATE" in (c05.get("target_patterns") or [])
    checks["b02_03_user_allows_old_reference_retirement"] = (j03.get("user_judgment") or {}).get("old_line_delete_allowed") is True
    checks["b02_04_user_retains_old_rising_reference"] = (j04.get("user_judgment") or {}).get("old_rising_reference") == "RETAIN"
    checks["b02_05_user_retains_old_rising_reference"] = (j05.get("user_judgment") or {}).get("old_rising_reference") == "RETAIN"
    findings = adjud.get("aggregate_findings") or {}
    checks["gentler_alone_is_not_retire_trigger"] = findings.get("gentler_line_alone_retirement_forbidden") is True
    checks["newest_alone_is_not_retire_trigger"] = findings.get("newest_line_only_retirement_forbidden") is True
    checks["local_falling_alone_is_not_retire_trigger"] = findings.get("local_direction_flip_alone_retirement_forbidden") is True
    checks["prior_b02_03_importance_preserved"] = findings.get("preserve_prior_b02_03_importance_adjudication") is True and importance.get("status") in {
        "PASS_CONTRACTS", "PASS", "RESEARCH_ONLY_USER_OPERATIONAL_EVIDENCE", "USER_OPERATIONAL_EVIDENCE"
    }
    checks["no_production_writeback"] = adjud.get("production_writeback") is False
    checks["no_normal_run_modification"] = adjud.get("normal_run_modified") is False
    checks["no_mt4_object_writeback"] = adjud.get("mt4_object_writeback") is False

    failed = [name for name, ok in checks.items() if not ok]

    refined_rules = [
        {
            "rule_id": "PB02_REFERENCE_RETIRE_IS_CONTEXTUAL",
            "evidence_cases": ["USDJPY_NVT71_B02_03", "USDJPY_NVT71_B02_04", "USDJPY_NVT71_B02_05"],
            "evidence_class": "USER_OPERATIONAL_EVIDENCE",
            "rule": "An old reference may be retired in some re-anchor contexts, but a newer, gentler, or locally opposite-direction candidate does not by itself justify retirement.",
            "default_when_ambiguous": "RETAIN_REFERENCE",
            "automatic_numeric_threshold_fixed": False,
        },
        {
            "rule_id": "PB02_GENTLER_IS_NOT_SUFFICIENT_FOR_SUBSUMPTION",
            "evidence_cases": ["USDJPY_NVT71_B02_03", "USDJPY_NVT71_B02_04", "USDJPY_NVT71_B02_05"],
            "evidence_class": "USER_OPERATIONAL_EVIDENCE",
            "rule": "Gentleness can support a broader-structure interpretation, but it is not a standalone subsumption/retirement trigger. The older line may still retain distinct structural context.",
            "automatic_numeric_threshold_fixed": False,
        },
        {
            "rule_id": "PB02_IMPORTANCE_SEPARATE_FROM_LIFECYCLE",
            "evidence_cases": ["USDJPY_NVT71_B02_03"],
            "evidence_class": "USER_OPERATIONAL_EVIDENCE",
            "rule": "Whether an old reference can retire is separate from whether a newly drawable line is provisional, important, or the decision owner. Preserve the earlier B02_03 importance-phase adjudication.",
        },
    ]

    report = {
        "schema": "nvt7.1-usdjpy-batch02-final-handoff/0.1",
        "status": "PASS_CONTRACTS" if not failed else "FAIL_CONTRACTS",
        "symbol_scope": "USDJPY_ONLY",
        "evidence_class": "USER_OPERATIONAL_EVIDENCE",
        "source_batch01_status": batch01.get("status"),
        "source_batch02_schema": batch02.get("schema"),
        "source_adjudication_schema": adjud.get("schema"),
        "original_nvt7_scoped_beta_unchanged": True,
        "contract_checks": checks,
        "failed_checks": failed,
        "refined_candidate_rules": refined_rules,
        "case_contracts": {
            "USDJPY_NVT71_B02_03": {
                "old_reference": "RETIRE_ALLOWED",
                "preserve_prior_line_importance_phase_model": True,
                "automatic_retire_rule_created": False,
            },
            "USDJPY_NVT71_B02_04": {
                "old_rising_reference": "RETAIN",
                "new_candidate_does_not_force_retirement": True,
            },
            "USDJPY_NVT71_B02_05": {
                "old_rising_reference": "RETAIN",
                "new_candidate_does_not_force_retirement": True,
            },
        },
        "research_conclusion": {
            "retired_reference_state_remains_supported": True,
            "retirement_trigger_still_not_hard_fixed": True,
            "reference_retention_default_strengthened": True,
            "gentleness_only_retirement_rejected": True,
            "next_step": "Run another future-hidden USDJPY historical batch focused on discriminating RETAIN vs RETIRE contexts without inventing numeric thresholds.",
        },
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
        "failed_checks": failed,
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
