from __future__ import annotations

import argparse
import json
from pathlib import Path

ROLES = ("TL", "CH", "TL_ZONE_EDGE", "CH_ZONE_EDGE")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build explicit V4 display-decision template.")
    ap.add_argument("--v4", required=True)
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    v4 = load_json(Path(args.v4))
    adj = load_json(Path(args.adjudication))

    entries = []
    if v4.get("status") == "READY_FOR_VISUAL_POLICY_SELECTION":
        for rec in adj.get("records", []):
            if rec.get("classification") != "PARENT_OWNED_SAME_FAMILY":
                continue
            for role in ROLES:
                locked = (
                    rec.get("source_tf") == "H1"
                    and rec.get("structure_level") == "LARGE_DOW"
                    and rec.get("generation_role") == "CURRENT"
                    and role in ("TL", "CH")
                )
                entries.append({
                    "source_tf": rec.get("source_tf"),
                    "line_id": rec.get("line_id"),
                    "structure_level": rec.get("structure_level"),
                    "generation_role": rec.get("generation_role"),
                    "structural_owner_tf": rec.get("structural_owner_tf"),
                    "same_family_parent_id": rec.get("same_family_parent_id"),
                    "role": role,
                    "selected_visibility": "DRAW" if locked else None,
                    "locked_by_teacher_invariant": locked,
                    "evidence_note": (
                        "09/19 H1 LARGE_DOW CURRENT TL/CH must remain visible."
                        if locked else None
                    ),
                    "allowed_visibility": ["DRAW", "REFERENCE", "SUPPRESSED"],
                })

    status = (
        "READY_FOR_EXPLICIT_DISPLAY_DECISIONS"
        if v4.get("status") == "READY_FOR_VISUAL_POLICY_SELECTION"
        else "BLOCKED_PENDING_V3_5"
    )
    payload = {
        "schema": "nvt9-v4-display-decisions/0.1",
        "status": status,
        "audit_id": "ID10IQ200",
        "source_v4": args.v4,
        "source_adjudication": args.adjudication,
        "instructions": (
            "Fill selected_visibility only from explicit visual/teacher review. "
            "Do not suppress from ownership or elapsed-time metrics alone."
        ),
        "decision_count": len(entries),
        "decisions": entries,
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
        "decision_count": len(entries),
        "output": str(out),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
