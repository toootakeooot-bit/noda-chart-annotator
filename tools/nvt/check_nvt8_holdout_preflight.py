from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Check strict source-level NVT8 held-out readiness.")
    ap.add_argument("--partition", required=True)
    ap.add_argument("--nvt7-scoped-beta", required=True)
    ap.add_argument("--nvt7-regression", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    partition = load_json(args.partition)
    beta = load_json(args.nvt7_scoped_beta)
    regression = load_json(args.nvt7_regression)

    if partition.get("schema") != "nvt8-source-partition/1.0":
        raise ValueError("unexpected NVT8 source partition schema")
    if beta.get("schema") != "nvt7-lifecycle-scoped-beta/1.0":
        raise ValueError("unexpected NVT7 scoped beta schema")
    if regression.get("schema") != "nvt7-frozen-scope-regression/1.0":
        raise ValueError("unexpected NVT7 frozen regression schema")

    clean = partition.get("clean_held_out_sources") or []
    nvt7_ready = (
        beta.get("scoped_beta_freeze_ready") is True
        and beta.get("held_out_validation_ready_for_scoped_rules") is True
        and regression.get("all_checks_pass") is True
        and regression.get("held_out_validation_ready") is True
    )
    source_ready = len(clean) > 0

    report = {
        "schema": "nvt8-held-out-preflight/1.0",
        "status": "READY" if nvt7_ready and source_ready else "BLOCKED",
        "phase": "NVT8-0_HELD_OUT_PREFLIGHT",
        "nvt7_scoped_beta_ready": nvt7_ready,
        "source_level_holdout_ready": source_ready,
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
        report["blocking_reasons"].append("NVT7 scoped lifecycle beta is not ready for held-out validation.")
    if not source_ready:
        report["blocking_reasons"].append(
            "No clean source-level held-out video remains in the current five-video corpus."
        )
        report["blocking_reasons"].append(
            "NVT_VIDEO_20260822 is not clean holdout because OBS_0007 was already registered during NVT1."
        )

    if report["status"] == "READY":
        report["next_action"] = "Register held-out events without tuning, then run NVT8 metric comparison by failure layer."
    else:
        report["next_action"] = (
            "Add at least one previously unseen video source and register it as held-out before any teacher-event inspection."
        )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "output": str(out),
        "nvt7_scoped_beta_ready": nvt7_ready,
        "source_level_holdout_ready": source_ready,
        "clean_held_out_source_count": len(clean),
        "next_action": report["next_action"],
    }, ensure_ascii=False, indent=2))

    # BLOCKED here is an expected research gate, not an execution failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
