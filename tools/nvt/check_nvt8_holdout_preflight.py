from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check strict source-level NVT8 held-out readiness after the NVT7/NVT7.1 research freezes."
    )
    ap.add_argument("--partition", required=True)
    ap.add_argument("--nvt7-scoped-beta", required=True)
    ap.add_argument("--nvt7-regression", required=True)
    ap.add_argument("--nvt7-semantic-freeze", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    partition = load_json(args.partition)
    beta = load_json(args.nvt7_scoped_beta)
    regression = load_json(args.nvt7_regression)
    semantic = load_json(args.nvt7_semantic_freeze)

    if partition.get("schema") != "nvt8-source-partition/1.0":
        raise ValueError("unexpected NVT8 source partition schema")
    if beta.get("schema") != "nvt7-lifecycle-scoped-beta/1.0":
        raise ValueError("unexpected NVT7 scoped beta schema")
    if regression.get("schema") != "nvt7-frozen-scope-regression/1.0":
        raise ValueError("unexpected NVT7 frozen regression schema")
    if semantic.get("schema") != "nvt7.1-usdjpy-semantic-freeze-candidate/0.2":
        raise ValueError("unexpected NVT7.1 semantic freeze schema")

    clean = partition.get("clean_held_out_sources") or []

    nvt7_ready = (
        beta.get("scoped_beta_freeze_ready") is True
        and beta.get("held_out_validation_ready_for_scoped_rules") is True
        and regression.get("all_checks_pass") is True
        and regression.get("held_out_validation_ready") is True
    )

    semantic_ready = (
        semantic.get("status") == "PASS_CONTRACTS"
        and semantic.get("all_contracts_pass") is True
        and semantic.get("scoped_research_freeze_candidate") is True
        and semantic.get("symbol_scope") == "USDJPY_ONLY"
        and semantic.get("timeframe") == "H1"
        and semantic.get("production_writeback") is False
        and semantic.get("normal_run_modified") is False
        and semantic.get("mt4_object_writeback") is False
        and semantic.get("trade_authority") is False
    )

    source_ready = len(clean) > 0
    prerequisites_ready = nvt7_ready and semantic_ready
    strict_ready = prerequisites_ready and source_ready

    if strict_ready:
        status = "READY"
    elif not prerequisites_ready:
        status = "BLOCKED_PREREQUISITE"
    else:
        status = "BLOCKED_NO_CLEAN_SOURCE_LEVEL_HOLDOUT"

    report = {
        "schema": "nvt8-held-out-preflight/1.1",
        "status": status,
        "phase": "NVT8-0_HELD_OUT_PREFLIGHT",
        "nvt7_scoped_beta_ready": nvt7_ready,
        "nvt7_1_semantic_freeze_ready": semantic_ready,
        "nvt7_1_semantic_freeze_schema": semantic.get("schema"),
        "nvt7_1_semantic_evidence_class": semantic.get("evidence_class"),
        "nvt7_1_still_unfixed": semantic.get("still_unfixed") or [],
        "source_level_holdout_ready": source_ready,
        "strict_nvt8_can_start": strict_ready,
        "clean_held_out_source_count": len(clean),
        "clean_held_out_sources": clean,
        "development_or_touched_sources": partition.get("development_or_touched_sources") or [],
        "blocking_reasons": [],
        "next_action": None,
        "production_promotion_ready": False,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
    }

    if not nvt7_ready:
        report["blocking_reasons"].append(
            "NVT7 scoped lifecycle beta/regression is not ready for held-out validation."
        )
    if not semantic_ready:
        report["blocking_reasons"].append(
            "NVT7.1 semantic scoped freeze candidate 0.2 is not PASS_CONTRACTS or violates research-only guardrails."
        )
    if not source_ready:
        report["blocking_reasons"].append(
            "No clean source-level held-out video remains in the current five-video corpus."
        )
        report["blocking_reasons"].append(
            "All five known teacher videos were inspected, registered, or used as development evidence before strict NVT8."
        )

    if strict_ready:
        report["next_action"] = (
            "Register held-out events without tuning, freeze the event registry, then run NVT8 metric comparison by failure layer."
        )
    elif prerequisites_ready and not source_ready:
        report["next_action"] = (
            "Add at least one previously unseen USDJPY teacher video and register it as held-out before any teacher-event inspection. "
            "Do not use historical user-adjudicated NVT8-H as a substitute for this strict source-level gate."
        )
    else:
        report["next_action"] = "Repair the failed prerequisite gate before registering any NVT8 held-out source."

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "output": str(out),
        "nvt7_scoped_beta_ready": nvt7_ready,
        "nvt7_1_semantic_freeze_ready": semantic_ready,
        "source_level_holdout_ready": source_ready,
        "strict_nvt8_can_start": strict_ready,
        "clean_held_out_source_count": len(clean),
        "next_action": report["next_action"],
    }, ensure_ascii=False, indent=2))

    # A research BLOCKED status is an expected gate, not an execution failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
