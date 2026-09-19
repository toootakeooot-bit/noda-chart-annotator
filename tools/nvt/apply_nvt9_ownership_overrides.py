from __future__ import annotations

import argparse
import json
from pathlib import Path

TF_RANK = {"M15": 0, "H1": 1, "H4": 2, "D1": 3}
ALLOWED = {
    "PARENT_OWNED_SAME_FAMILY",
    "LOCAL_OWNED_DISTINCT",
    "AMBIGUOUS_KEEP_VISIBLE",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Apply explicit teacher/manual ownership overrides to NVT9 auto adjudication."
    )
    ap.add_argument("--auto", required=True)
    ap.add_argument("--overrides", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    auto_path = Path(args.auto)
    overrides_path = Path(args.overrides)
    auto = load_json(auto_path)
    overrides = load_json(overrides_path)

    records = [dict(r) for r in auto.get("records", [])]
    by_key = {(r.get("source_tf"), r.get("line_id")): r for r in records}
    problems = []
    applied = 0

    for ov in overrides.get("overrides", []):
        source_tf = ov.get("source_tf")
        line_id = ov.get("line_id")
        cls = ov.get("classification")
        key = (source_tf, line_id)

        if cls in (None, ""):
            continue
        if key not in by_key:
            problems.append({"source_tf": source_tf, "line_id": line_id, "reason": "UNKNOWN_LINE"})
            continue
        if cls not in ALLOWED:
            problems.append({
                "source_tf": source_tf,
                "line_id": line_id,
                "reason": "INVALID_CLASSIFICATION",
                "value": cls,
            })
            continue

        rec = by_key[key]
        owner_tf = ov.get("structural_owner_tf")
        parent_id = ov.get("same_family_parent_id")
        relation = ov.get("relation") or "MANUAL_TEACHER_ADJUDICATION"
        note = ov.get("teacher_evidence_note")

        if cls == "PARENT_OWNED_SAME_FAMILY":
            if not owner_tf or TF_RANK.get(owner_tf, -1) <= TF_RANK.get(source_tf, -1):
                problems.append({
                    "source_tf": source_tf,
                    "line_id": line_id,
                    "reason": "HIGHER_OWNER_TF_REQUIRED",
                })
                continue
            if not parent_id:
                problems.append({
                    "source_tf": source_tf,
                    "line_id": line_id,
                    "reason": "PARENT_ID_REQUIRED",
                })
                continue
            candidate_ids = {
                c.get("parent_line_id")
                for c in rec.get("candidate_parents", [])
                if c.get("parent_line_id")
            }
            if parent_id not in candidate_ids:
                problems.append({
                    "source_tf": source_tf,
                    "line_id": line_id,
                    "reason": "PARENT_ID_NOT_IN_REVIEW_MATRIX",
                    "parent_id": parent_id,
                })
                continue
            display = "REFERENCE_OR_REFINED_GEOMETRY"
            reason_code = "MANUAL_PARENT_FAMILY_CONFIRMED"
        elif cls == "LOCAL_OWNED_DISTINCT":
            if owner_tf not in (None, "", source_tf):
                problems.append({
                    "source_tf": source_tf,
                    "line_id": line_id,
                    "reason": "LOCAL_OWNER_MUST_EQUAL_SOURCE_TF",
                })
                continue
            owner_tf = source_tf
            parent_id = None
            display = "DRAW_LOCAL_STRUCTURE"
            reason_code = "MANUAL_LOCAL_STRUCTURE_CONFIRMED"
        else:
            owner_tf = source_tf
            parent_id = None
            display = "KEEP_VISIBLE"
            reason_code = "MANUAL_AMBIGUOUS_KEEP_VISIBLE"

        rec["classification"] = cls
        rec["structural_owner_tf"] = owner_tf
        rec["same_family_parent_id"] = parent_id
        rec["relation"] = relation
        rec["adjudication_required"] = cls == "AMBIGUOUS_KEEP_VISIBLE"
        rec["display_recommendation"] = display
        rec["reason_code"] = reason_code
        rec["teacher_evidence_note"] = note
        rec["override_applied"] = True
        applied += 1

    unresolved = [
        {"source_tf": r.get("source_tf"), "line_id": r.get("line_id")}
        for r in records
        if r.get("classification") == "AMBIGUOUS_KEEP_VISIBLE"
        or r.get("adjudication_required") is True
    ]

    status = (
        "PASS_FINAL_ADJUDICATION"
        if not problems and not unresolved
        else "BLOCKED_FINAL_ADJUDICATION"
    )
    payload = {
        **auto,
        "schema": "nvt9-ownership-adjudication/0.2",
        "status": status,
        "source_auto_adjudication": str(auto_path),
        "source_overrides": str(overrides_path),
        "override_applied_count": applied,
        "override_problem_count": len(problems),
        "override_problems": problems,
        "ambiguous_count": len(unresolved),
        "unresolved": unresolved,
        "records": records,
        "guardrails": {
            **auto.get("guardrails", {}),
            "manual_override_requires_explicit_classification": True,
            "parent_override_must_reference_matrix_parent": True,
            "elapsed_hour_threshold_used": False,
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
        "status": status,
        "override_applied_count": applied,
        "override_problem_count": len(problems),
        "ambiguous_count": len(unresolved),
        "output": str(out),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if not problems else 4


if __name__ == "__main__":
    raise SystemExit(main())
