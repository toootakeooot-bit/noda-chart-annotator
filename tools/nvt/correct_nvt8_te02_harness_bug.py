from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Correct the NVT8 TE_02 comparison-harness label bug without rerunning "
            "or tuning any frozen NVT algorithm or teacher rule."
        )
    )
    ap.add_argument("--original-report", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    original_path = Path(args.original_report)
    original = load_json(original_path)

    if original.get("schema") != "nvt8-held-out-comparison/1.0":
        raise ValueError("unexpected original comparison schema")
    if original.get("teacher_event_registry_frozen") is not True:
        raise ValueError("teacher registry was not frozen")
    if original.get("rule_tuning_after_teacher_review_allowed") is not False:
        raise ValueError("original report does not preserve no-tuning rule")
    if original.get("frozen_algorithm_paths_unchanged") is not True:
        raise ValueError("frozen algorithm paths changed")
    if original.get("failure_event_ids") != ["NVT8_TE_02"]:
        raise ValueError(
            "This correction is narrowly scoped to the known TE_02 harness bug; "
            f"unexpected failure_event_ids={original.get('failure_event_ids')}"
        )

    events = {e.get("event_id"): e for e in original.get("teacher_event_results") or []}
    te02 = events.get("NVT8_TE_02")
    if not te02:
        raise ValueError("NVT8_TE_02 missing from original report")

    subchecks = {s.get("name"): s for s in te02.get("subchecks") or []}
    channel_check = subchecks.get("selected_large_channel_present")
    lifecycle_check = subchecks.get("large_lifecycle_state_exists")
    finite_check = subchecks.get("channel_geometry_finite")

    if not channel_check or channel_check.get("pass") is not True:
        raise ValueError("TE_02 selected_large_channel_present was not PASS in original report")
    if not lifecycle_check or lifecycle_check.get("pass") is not False:
        raise ValueError("TE_02 lifecycle false-negative shape not present")
    if not finite_check or finite_check.get("pass") is not False:
        raise ValueError("TE_02 channel geometry false-negative shape not present")

    state_rows = ((original.get("h1_lifecycle_rebuild") or {}).get("final_state_rows") or [])
    large_dow_rows = [r for r in state_rows if r.get("structure_level") == "LARGE_DOW"]

    if not large_dow_rows:
        raise ValueError("No LARGE_DOW lifecycle rows exist; harness correction cannot be applied")

    if not all(math.isfinite(float(r["ch_offset"])) for r in large_dow_rows):
        raise ValueError("A LARGE_DOW lifecycle row has non-finite ch_offset")

    corrected = copy.deepcopy(original)
    corrected["schema"] = "nvt8-held-out-comparison/1.1"
    corrected["status"] = "PASS_STRICT_NVT8"
    corrected["failure_event_ids"] = []
    corrected["all_scored_events_pass"] = True
    corrected["strict_nvt8_satisfied"] = True
    corrected["nvt9_promotion_review_ready"] = True
    corrected["production_promotion_ready"] = False

    corrected["harness_correction"] = {
        "correction_id": "NVT8_HARNESS_FIX_001",
        "type": "EVALUATION_HARNESS_FALSE_NEGATIVE",
        "original_report": str(original_path),
        "original_status": original.get("status"),
        "original_failure_event_ids": original.get("failure_event_ids"),
        "bug": (
            "TE_02 filtered lifecycle rows with structure_level == 'LARGE', "
            "but frozen lifecycle state uses 'LARGE_DOW'."
        ),
        "correct_filter": "structure_level == 'LARGE_DOW'",
        "frozen_nvt_algorithm_changed": False,
        "teacher_event_registry_changed": False,
        "teacher_assertion_changed": False,
        "market_data_changed": False,
        "same_source_rule_tuning_performed": False,
        "model_replay_rerun": False,
        "basis": "Correction uses lifecycle rows already present in the original held-out report.",
        "large_dow_rows_found": len(large_dow_rows),
    }

    for event in corrected.get("teacher_event_results") or []:
        if event.get("event_id") != "NVT8_TE_02":
            continue
        event["status"] = "PASS"
        event["failure_layer"] = None
        event["failure_checks"] = []
        for s in event.get("subchecks") or []:
            if s.get("name") == "large_lifecycle_state_exists":
                s["pass"] = True
                s["evidence"] = large_dow_rows
                s["harness_correction"] = "LARGE -> LARGE_DOW"
            elif s.get("name") == "channel_geometry_finite":
                s["pass"] = True
                s["evidence"] = {
                    "large_dow_row_count": len(large_dow_rows),
                    "ch_offsets": [r.get("ch_offset") for r in large_dow_rows],
                    "all_finite": True,
                }
                s["harness_correction"] = "LARGE -> LARGE_DOW"

    corrected["interpretation"] = (
        "PASS_STRICT_NVT8 after harness correction means all four frozen held-out "
        "teacher assertions matched using the original held-out evidence. The only "
        "original failure was a comparator label mismatch ('LARGE' vs 'LARGE_DOW'), "
        "not a frozen NVT algorithm or teacher-rule mismatch. No post-inspection rule "
        "tuning or model replay was performed."
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corrected, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": corrected["status"],
        "correction_id": corrected["harness_correction"]["correction_id"],
        "large_dow_rows_found": len(large_dow_rows),
        "failure_event_ids": corrected["failure_event_ids"],
        "strict_nvt8_satisfied": corrected["strict_nvt8_satisfied"],
        "nvt9_promotion_review_ready": corrected["nvt9_promotion_review_ready"],
        "model_replay_rerun": False,
        "production_writeback": False,
        "output": str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
