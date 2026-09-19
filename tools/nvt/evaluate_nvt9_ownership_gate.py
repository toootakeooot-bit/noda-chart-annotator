from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED = {
    "PARENT_OWNED_SAME_FAMILY",
    "LOCAL_OWNED_DISTINCT",
    "AMBIGUOUS_KEEP_VISIBLE",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate the NVT9 V3.5 ownership gate.")
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    src = Path(args.adjudication)
    payload = json.loads(src.read_text(encoding="utf-8-sig"))
    records = payload.get("records", [])

    problems = []
    unresolved = []
    for rec in records:
        cls = rec.get("classification")
        source_tf = rec.get("source_tf")
        owner_tf = rec.get("structural_owner_tf")
        line_id = rec.get("line_id")
        if cls not in ALLOWED:
            problems.append({"line_id": line_id, "reason": "INVALID_CLASSIFICATION", "value": cls})
            continue
        if cls == "AMBIGUOUS_KEEP_VISIBLE":
            unresolved.append({"source_tf": source_tf, "line_id": line_id})
        elif cls == "PARENT_OWNED_SAME_FAMILY":
            if not rec.get("same_family_parent_id"):
                problems.append({"line_id": line_id, "reason": "PARENT_ID_REQUIRED"})
            if not owner_tf or owner_tf == source_tf:
                problems.append({"line_id": line_id, "reason": "HIGHER_OWNER_TF_REQUIRED"})
        elif cls == "LOCAL_OWNED_DISTINCT":
            if owner_tf != source_tf:
                problems.append({"line_id": line_id, "reason": "LOCAL_OWNER_MUST_EQUAL_SOURCE_TF"})

    gate_pass = bool(records) and not problems and not unresolved
    result = {
        "schema": "nvt9-ownership-gate/0.1",
        "status": "PASS_V3_5" if gate_pass else "BLOCKED_V3_5",
        "source_adjudication": str(src),
        "record_count": len(records),
        "problem_count": len(problems),
        "unresolved_count": len(unresolved),
        "problems": problems,
        "unresolved": unresolved,
        "v4_unblocked": gate_pass,
        "guardrail": "AMBIGUOUS_KEEP_VISIBLE blocks V4 but does not alter Production or MT4.",
        "production_changed": False,
        "renderer_changed": False,
        "snapshot_changed": False,
        "nca_draw_writeback": False,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
