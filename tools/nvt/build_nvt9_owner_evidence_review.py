from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

TF_SECONDS = {
    "D1": 86400,
    "H4": 14400,
    "H1": 3600,
    "M15": 900,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def same_parent_bar(parent_tf: str, parent_anchor2: str, child_anchor2: str) -> bool:
    if parent_tf not in TF_SECONDS:
        return False
    start = dt(parent_anchor2)
    child = dt(child_anchor2)
    end = start + timedelta(seconds=TF_SECONDS[parent_tf])
    return start <= child < end


def evidence_class(row: dict) -> str:
    if not row.get("direction_match"):
        return "OPPOSITE_DIRECTION"
    same_terminal_price = float(row.get("anchor2_price_diff") or 0.0) == 0.0
    same_terminal_bar = same_parent_bar(
        row.get("parent_tf"),
        # parent/child anchor2 timestamps are not directly exported, but
        # equal terminal price + time diff can be evaluated only if the caller
        # injects the timestamps from the line sets below.
        row["_parent_anchor2_time"],
        row["_child_anchor2_time"],
    )
    nested_span = float(row.get("child_span_over_parent_span") or 999.0) < 1.0
    child_starts_later = dt(row["_child_anchor1_time"]) >= dt(row["_parent_anchor1_time"])

    if same_terminal_price and same_terminal_bar and nested_span and child_starts_later:
        return "SHARED_TERMINAL_PIVOT_NESTED_SCALE"

    if row.get("parent_generation_role") == "PREVIOUS":
        return "SAME_DIRECTION_RETAINED_PARENT_REFERENCE"

    return "SAME_DIRECTION_NONEXACT"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a threshold-free structural-owner evidence review from the NVT9 cross-TF matrix."
    )
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    matrix_path = Path(args.matrix)
    matrix = load_json(matrix_path)

    # Index actual line timestamps from current + retained line sets.
    line_index = {}
    for container in ("current_line_sets", "retained_parent_line_sets"):
        for tf, rows in (matrix.get(container) or {}).items():
            for line in rows:
                line_index[line.get("line_id")] = line

    grouped = defaultdict(list)
    for row in matrix.get("comparisons", []):
        p = line_index.get(row.get("parent_line_id"))
        c = line_index.get(row.get("child_line_id"))
        if not p or not c:
            continue
        enriched = dict(row)
        enriched["_parent_anchor1_time"] = p.get("anchor1_time")
        enriched["_parent_anchor2_time"] = p.get("anchor2_time")
        enriched["_child_anchor1_time"] = c.get("anchor1_time")
        enriched["_child_anchor2_time"] = c.get("anchor2_time")
        enriched["structural_evidence_class"] = evidence_class(enriched)
        grouped[(row.get("child_tf"), row.get("child_line_id"))].append(enriched)

    records = []
    counts = defaultdict(int)
    for (child_tf, child_line_id), rows in sorted(grouped.items()):
        strong = [
            r for r in rows
            if r["structural_evidence_class"] == "SHARED_TERMINAL_PIVOT_NESTED_SCALE"
        ]
        retained = [
            r for r in rows
            if r["structural_evidence_class"] == "SAME_DIRECTION_RETAINED_PARENT_REFERENCE"
        ]
        if strong:
            # Deterministic tie break only for presentation; this does not promote ownership.
            best = sorted(
                strong,
                key=lambda r: (
                    0 if r.get("parent_generation_role") == "CURRENT" else 1,
                    r.get("parent_level", ""),
                    r.get("parent_line_id", ""),
                ),
            )[0]
            status = "STRONG_OWNER_CANDIDATE_NEEDS_TEACHER_CONFIRMATION"
            rationale = (
                "Child and higher-TF parent share direction and the exact terminal pivot price; "
                "the child terminal timestamp falls inside the same parent candle and the child span is nested. "
                "This is threshold-free structural evidence, not automatic same-family promotion."
            )
        elif retained:
            best = sorted(
                retained,
                key=lambda r: (
                    float(r.get("tl_gap_end_over_max_channel_width") or 999999.0),
                    float(r.get("slope_abs_diff_price_per_day") or 999999.0),
                ),
            )[0]
            status = "RETAINED_PARENT_CANDIDATE_NEEDS_VISUAL_CONFIRMATION"
            rationale = (
                "The best same-direction higher-TF evidence is a retained PREVIOUS reference. "
                "This is consistent with NVT8 coexistence semantics but does not establish same-family ownership."
            )
        else:
            same_dir = [r for r in rows if r.get("direction_match")]
            if same_dir:
                best = sorted(
                    same_dir,
                    key=lambda r: (
                        float(r.get("tl_gap_end_over_max_channel_width") or 999999.0),
                        float(r.get("slope_abs_diff_price_per_day") or 999999.0),
                    ),
                )[0]
                status = "NONEXACT_OWNER_CANDIDATE_NEEDS_TEACHER_CONFIRMATION"
                rationale = "Same-direction higher-TF candidates exist, but no threshold-free shared-terminal-pivot relation was found."
            else:
                best = sorted(
                    rows,
                    key=lambda r: (
                        float(r.get("tl_gap_end_over_max_channel_width") or 999999.0),
                        float(r.get("slope_abs_diff_price_per_day") or 999999.0),
                    ),
                )[0]
                status = "NO_SAME_DIRECTION_PARENT_CANDIDATE"
                rationale = "No same-direction parent candidate exists in CURRENT+PREVIOUS retained parent scope."

        counts[status] += 1
        records.append({
            "source_tf": child_tf,
            "line_id": child_line_id,
            "structure_level": best.get("child_level"),
            "direction": best.get("child_direction"),
            "status": status,
            "candidate_owner_tf": best.get("parent_tf"),
            "candidate_parent_generation_role": best.get("parent_generation_role"),
            "candidate_parent_level": best.get("parent_level"),
            "candidate_parent_line_id": best.get("parent_line_id"),
            "structural_evidence_class": best.get("structural_evidence_class"),
            "terminal_pivot_price_exact": float(best.get("anchor2_price_diff") or 0.0) == 0.0,
            "terminal_pivot_same_parent_bar": same_parent_bar(
                best.get("parent_tf"),
                best["_parent_anchor2_time"],
                best["_child_anchor2_time"],
            ),
            "child_span_nested": float(best.get("child_span_over_parent_span") or 999.0) < 1.0,
            "parent_anchor2_time": best["_parent_anchor2_time"],
            "child_anchor2_time": best["_child_anchor2_time"],
            "anchor2_price_diff": best.get("anchor2_price_diff"),
            "tl_gap_end_over_max_channel_width": best.get("tl_gap_end_over_max_channel_width"),
            "slope_abs_diff_price_per_day": best.get("slope_abs_diff_price_per_day"),
            "rationale": rationale,
            "automatic_owner_promotion": False,
            "teacher_or_manual_confirmation_required": True,
        })

    payload = {
        "schema": "nvt9-owner-evidence-review/0.1",
        "status": "READY_FOR_TARGETED_OWNER_CONFIRMATION",
        "audit_id": "ID10IQ200",
        "source_matrix": str(matrix_path),
        "record_count": len(records),
        "status_counts": dict(counts),
        "records": records,
        "decision_policy": {
            "numeric_similarity_threshold_used": False,
            "elapsed_hour_threshold_used": False,
            "shared_terminal_pivot_rule": (
                "same direction + exact terminal pivot price + child terminal time inside parent candle "
                "+ nested child span + child starts no earlier than parent"
            ),
            "automatic_owner_promotion": False,
            "reason": "Evidence classes narrow the manual review; they do not replace teacher/manual ownership confirmation.",
        },
        "production_changed": False,
        "renderer_changed": False,
        "snapshot_changed": False,
        "nca_draw_writeback": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": payload["status"],
        "record_count": len(records),
        "status_counts": dict(counts),
        "output": str(out),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
