from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ALLOWED = {"DRAW", "REFERENCE", "SUPPRESSED"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build an audit-only V6 preview from explicit V4 per-line display decisions."
    )
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    snapshot = Path(args.snapshot)
    decisions_path = Path(args.decisions)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    decisions_payload = load_json(decisions_path)
    raw_decisions = decisions_payload.get("decisions", [])
    errors = []
    decision_map = {}

    for d in raw_decisions:
        key = (d.get("line_id"), d.get("role"))
        vis = d.get("selected_visibility")
        if vis in (None, ""):
            errors.append({"key": key, "reason": "INCOMPLETE_DISPLAY_DECISION"})
            continue
        if vis not in ALLOWED:
            errors.append({"key": key, "reason": "INVALID_VISIBILITY", "value": vis})
            continue
        if d.get("locked_by_teacher_invariant") and vis == "SUPPRESSED":
            errors.append({"key": key, "reason": "TEACHER_INVARIANT_FORBIDS_SUPPRESSION"})
            continue
        decision_map[key] = vis

    if errors:
        print(json.dumps({
            "status": "BLOCKED_INCOMPLETE_V4",
            "error_count": len(errors),
            "errors": errors,
            "production_changed": False,
        }, ensure_ascii=False, indent=2))
        return 6

    with snapshot.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(f.fieldnames or [])

    kept = []
    audit_rows = []
    before = Counter()
    after = Counter()
    suppressed = Counter()
    seen_decisions = set()

    for row in rows:
        tf = row.get("timeframe", "")
        before[tf] += 1
        object_id = row.get("object_id", "")
        line_id = object_id.split("__", 1)[0] if "__" in object_id else object_id
        role = row.get("role")
        key = (line_id, role)
        vis = decision_map.get(key, "DRAW")
        if key in decision_map:
            seen_decisions.add(key)

        audit_rows.append({
            "object_id": object_id,
            "line_id": line_id,
            "timeframe": tf,
            "structure_level": row.get("structure_level"),
            "generation_role": row.get("generation_role"),
            "role": role,
            "visibility": vis,
            "reason": (
                "EXPLICIT_V4_DISPLAY_DECISION"
                if key in decision_map else "UNSPECIFIED_PASS_THROUGH"
            ),
        })

        if vis == "SUPPRESSED":
            suppressed[tf] += 1
            continue
        kept.append(row)
        after[tf] += 1

    missing_objects = [
        {"line_id": k[0], "role": k[1]}
        for k in decision_map
        if k not in seen_decisions
    ]
    if missing_objects:
        print(json.dumps({
            "status": "FAIL_V6_DECISION_OBJECT_NOT_FOUND",
            "missing_objects": missing_objects,
            "production_changed": False,
        }, ensure_ascii=False, indent=2))
        return 7

    stem = snapshot.stem
    preview = outdir / f"{stem}_V6_0919.csv"
    audit = outdir / f"{stem}_V6_0919_audit.json"

    with preview.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(kept)

    payload = {
        "schema": "nvt9-v6-visibility-preview/0.1",
        "status": "PASS_V6_PREVIEW",
        "source_snapshot": str(snapshot),
        "display_decisions": str(decisions_path),
        "counts_before": dict(before),
        "counts_after": dict(after),
        "suppressed_counts": dict(suppressed),
        "decisions": audit_rows,
        "preview_snapshot": str(preview),
        "source_snapshot_modified": False,
        "production_renderer_modified": False,
        "nca_draw_writeback": False,
    }
    audit.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "PASS_V6_PREVIEW",
        "counts_before": dict(before),
        "counts_after": dict(after),
        "suppressed_counts": dict(suppressed),
        "preview": str(preview),
        "audit": str(audit),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
