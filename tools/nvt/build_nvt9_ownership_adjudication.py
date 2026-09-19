from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

TF_RANK = {"M15": 0, "H1": 1, "H4": 2, "D1": 3}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidate_sort_key(row: dict) -> tuple:
    exact = row.get("relation_without_threshold") == "EXACT_GEOMETRY_SAME_FAMILY"
    direction = bool(row.get("direction_match"))
    normalized_gap = row.get("tl_gap_end_over_max_channel_width")
    if normalized_gap is None:
        normalized_gap = float("inf")
    slope = row.get("slope_abs_diff_price_per_day")
    if slope is None:
        slope = float("inf")
    parent_tf = row.get("parent_tf", "")
    return (
        0 if exact else 1,
        0 if direction else 1,
        float(normalized_gap),
        float(slope),
        -TF_RANK.get(parent_tf, -1),
        row.get("parent_line_id", ""),
    )


def slim_candidate(row: dict) -> dict:
    keys = [
        "parent_tf",
        "parent_level",
        "parent_generation_role",
        "parent_line_id",
        "parent_direction",
        "direction_match",
        "relation_without_threshold",
        "tl_gap_at_eval_start",
        "tl_gap_at_eval_end",
        "tl_gap_end_over_max_channel_width",
        "slope_abs_diff_price_per_day",
        "parent_anchor_span_hours",
        "child_anchor_span_hours",
        "child_span_over_parent_span",
        "anchor1_time_diff_hours",
        "anchor2_time_diff_hours",
        "parent_ch_offset",
        "child_ch_offset",
    ]
    return {k: row.get(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a conservative NVT9 cross-TF ownership adjudication template."
    )
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    matrix_path = Path(args.matrix)
    policy_path = Path(args.policy)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    matrix = load_json(matrix_path)
    policy = load_json(policy_path)

    comparisons = matrix.get("comparisons", [])
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    child_meta: dict[tuple[str, str], dict] = {}

    for row in comparisons:
        child_tf = row.get("child_tf")
        child_line_id = row.get("child_line_id")
        if not child_tf or not child_line_id:
            continue
        key = (child_tf, child_line_id)
        groups[key].append(row)
        child_meta[key] = {
            "source_tf": child_tf,
            "line_id": child_line_id,
            "structure_level": row.get("child_level"),
            "generation_role": row.get("child_generation_role"),
            "direction": row.get("child_direction"),
        }

    records = []
    auto_resolved = 0
    ambiguous = 0
    user_candidates = policy.get("user_observed_owner_candidates", {})

    for key in sorted(groups, key=lambda k: (TF_RANK.get(k[0], 99), k[1]), reverse=True):
        rows = sorted(groups[key], key=candidate_sort_key)
        meta = child_meta[key]
        exact_rows = [
            r for r in rows
            if r.get("relation_without_threshold") == "EXACT_GEOMETRY_SAME_FAMILY"
            and r.get("direction_match") is True
        ]

        if exact_rows:
            chosen = sorted(
                exact_rows,
                key=lambda r: (-TF_RANK.get(r.get("parent_tf", ""), -1), candidate_sort_key(r)),
            )[0]
            classification = "PARENT_OWNED_SAME_FAMILY"
            owner_tf = chosen.get("parent_tf")
            parent_id = chosen.get("parent_line_id")
            relation = "AUTO_EXACT_GEOMETRY"
            adjudication_required = False
            auto_resolved += 1
        else:
            chosen = rows[0] if rows else None
            classification = "AMBIGUOUS_KEEP_VISIBLE"
            owner_tf = meta["source_tf"]
            parent_id = None
            relation = "PENDING_TEACHER_OR_MANUAL_ADJUDICATION"
            adjudication_required = True
            ambiguous += 1

        records.append({
            **meta,
            "classification": classification,
            "structural_owner_tf": owner_tf,
            "same_family_parent_id": parent_id,
            "relation": relation,
            "adjudication_required": adjudication_required,
            "user_observed_owner_candidate_tf": user_candidates.get(meta["source_tf"]),
            "best_metric_parent_tf": chosen.get("parent_tf") if chosen else None,
            "best_metric_parent_id": chosen.get("parent_line_id") if chosen else None,
            "candidate_parents": [slim_candidate(r) for r in rows],
            "display_recommendation": "KEEP_VISIBLE" if adjudication_required else "REFERENCE_OR_REFINED_GEOMETRY",
            "reason_code": (
                "EXACT_CROSS_TF_GEOMETRY_CONFIRMED"
                if not adjudication_required
                else "NON_EXACT_REQUIRES_TEACHER_ADJUDICATION"
            ),
        })

    status = "PASS_EXACT_ONLY" if ambiguous == 0 else "BLOCKED_PENDING_ADJUDICATION"
    payload = {
        "schema": "nvt9-ownership-adjudication/0.1",
        "status": status,
        "audit_id": "ID10IQ200",
        "symbol": matrix.get("symbol"),
        "source_matrix": str(matrix_path),
        "policy": str(policy_path),
        "record_count": len(records),
        "auto_resolved_count": auto_resolved,
        "ambiguous_count": ambiguous,
        "records": records,
        "guardrails": {
            "numeric_similarity_threshold_used": False,
            "elapsed_hour_threshold_used": False,
            "automatic_local_distinct_used": False,
            "ambiguous_lines_kept_visible": True,
        },
        "production_changed": False,
        "renderer_changed": False,
        "snapshot_changed": False,
        "nca_draw_writeback": False,
    }

    json_path = outdir / "NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_AUTO.json"
    csv_path = outdir / "NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_AUTO.csv"
    txt_path = outdir / "NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919_AUTO.txt"
    override_path = outdir / "NVT9_USDJPY_OWNERSHIP_OVERRIDES_0919_TEMPLATE.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    override_template = {
        "schema": "nvt9-ownership-overrides/0.1",
        "status": "TEMPLATE",
        "audit_id": "ID10IQ200",
        "source_auto_adjudication": str(json_path),
        "instructions": (
            "Fill only teacher/manual-confirmed rows. Do not infer from metric closeness or elapsed hours alone."
        ),
        "overrides": [
            {
                "source_tf": rec["source_tf"],
                "line_id": rec["line_id"],
                "classification": None,
                "structural_owner_tf": None,
                "same_family_parent_id": None,
                "relation": None,
                "teacher_evidence_note": None,
                "user_observed_owner_candidate_tf": rec.get("user_observed_owner_candidate_tf"),
                "best_metric_parent_tf": rec.get("best_metric_parent_tf"),
                "best_metric_parent_id": rec.get("best_metric_parent_id"),
            }
            for rec in records
            if rec.get("adjudication_required")
        ],
    }
    override_path.write_text(
        json.dumps(override_template, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fields = [
        "source_tf", "line_id", "structure_level", "generation_role", "direction",
        "classification", "structural_owner_tf", "same_family_parent_id", "relation",
        "adjudication_required", "user_observed_owner_candidate_tf",
        "best_metric_parent_tf", "best_metric_parent_id", "display_recommendation", "reason_code",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for rec in records:
            w.writerow({k: rec.get(k, "") for k in fields})

    lines = [
        "NVT9 OWNERSHIP ADJUDICATION - 09/19",
        f"status={status}",
        f"records={len(records)} auto_resolved={auto_resolved} ambiguous={ambiguous}",
        "",
        "Policy: exact geometry may auto-resolve; all non-exact cases remain visible and require adjudication.",
        "No elapsed-hour threshold is used.",
        "",
    ]
    for rec in records:
        lines.append(
            f"[{rec['source_tf']}] {rec['line_id']} {rec['direction']} "
            f"=> {rec['classification']} owner={rec['structural_owner_tf']} "
            f"userCandidate={rec.get('user_observed_owner_candidate_tf')} "
            f"metricParent={rec.get('best_metric_parent_tf')} "
            f"required={rec['adjudication_required']}"
        )
    lines += [
        "",
        "V4 remains blocked while any AMBIGUOUS_KEEP_VISIBLE record remains.",
        "No Production file was changed.",
    ]
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": status,
        "record_count": len(records),
        "auto_resolved_count": auto_resolved,
        "ambiguous_count": ambiguous,
        "json": str(json_path),
        "csv": str(csv_path),
        "txt": str(txt_path),
        "override_template": str(override_path),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
