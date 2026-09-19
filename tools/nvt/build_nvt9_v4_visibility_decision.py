from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build the NVT9 V4 ownership-aware visibility decision input."
    )
    ap.add_argument("--gate", required=True)
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    gate = load_json(Path(args.gate))
    adjudication = load_json(Path(args.adjudication))
    records = adjudication.get("records", [])

    if gate.get("status") != "PASS_V3_5":
        payload = {
            "schema": "nvt9-v4-visibility-decision/0.1",
            "status": "BLOCKED_PENDING_V3_5",
            "gate_status": gate.get("status"),
            "unresolved": gate.get("unresolved", []),
            "v4_policy_selected": False,
            "production_changed": False,
            "renderer_changed": False,
            "snapshot_changed": False,
            "nca_draw_writeback": False,
        }
    else:
        counts = Counter(r.get("classification") for r in records)
        parent_owned = [
            r for r in records if r.get("classification") == "PARENT_OWNED_SAME_FAMILY"
        ]
        parent_unresolved = [
            r for r in records if r.get("classification") == "HIGHER_TF_OWNER_PARENT_UNRESOLVED"
        ]
        local_owned = [
            r for r in records if r.get("classification") == "LOCAL_OWNED_DISTINCT"
        ]
        h1_parent_owned = any(
            r.get("source_tf") == "H1"
            and r.get("classification") == "PARENT_OWNED_SAME_FAMILY"
            for r in records
        )

        recommendations = []
        for r in records:
            cls = r.get("classification")
            if cls == "PARENT_OWNED_SAME_FAMILY":
                rec = "REFERENCE_OR_REFINED_GEOMETRY_REVIEW"
                note = (
                    "Same-family ownership is confirmed. Decide DRAW vs REFERENCE vs SUPPRESSED "
                    "from visual redundancy; ownership alone does not authorize suppression."
                )
            elif cls == "HIGHER_TF_OWNER_PARENT_UNRESOLVED":
                rec = "KEEP_VISIBLE_PARENT_MATCH_UNRESOLVED"
                note = (
                    "Higher-timeframe structural ownership is confirmed, but no current NCA parent-family "
                    "match is fixed. Keep visible; suppression is forbidden until parent recall/match is resolved."
                )
            elif cls == "LOCAL_OWNED_DISTINCT":
                rec = "DRAW_FULL_LOCAL_CONTEXT"
                note = "Distinct local structure should not be removed as a parent duplicate."
            else:
                rec = "KEEP_VISIBLE"
                note = "Ambiguous ownership must remain visible."
            recommendations.append({
                "source_tf": r.get("source_tf"),
                "line_id": r.get("line_id"),
                "classification": cls,
                "structural_owner_tf": r.get("structural_owner_tf"),
                "same_family_parent_id": r.get("same_family_parent_id"),
                "v4_display_review": rec,
                "note": note,
            })

        payload = {
            "schema": "nvt9-v4-visibility-decision/0.1",
            "status": "READY_FOR_VISUAL_POLICY_SELECTION",
            "gate_status": gate.get("status"),
            "classification_counts": dict(counts),
            "parent_owned_count": len(parent_owned),
            "parent_match_unresolved_count": len(parent_unresolved),
            "local_owned_count": len(local_owned),
            "recommendations": recommendations,
            "legacy_h1_16_to_12_candidate": {
                "status": (
                    "BLOCKED_BY_PARENT_MATCH_UNRESOLVED"
                    if any(r.get("source_tf") == "H1" for r in parent_unresolved)
                    else (
                        "SECONDARY_ONLY_PARENT_DUPLICATION_PRESENT"
                        if h1_parent_owned
                        else "MAY_BE_EVALUATED_AFTER_VISUAL_REVIEW"
                    )
                ),
                "automatic_run_allowed": False,
                "reason": (
                    "H1 structural owner is higher-TF but its current NCA parent-family match is unresolved; "
                    "generic suppression is not allowed."
                    if any(r.get("source_tf") == "H1" for r in parent_unresolved)
                    else (
                        "H1 has a confirmed higher-timeframe parent family; test duplicate display "
                        "handling before generic PREVIOUS-zone suppression."
                        if h1_parent_owned
                        else "No confirmed H1 parent-family duplication blocks evaluation of the old "
                        "PREVIOUS-zone visibility hypothesis, but teacher invariants still apply."
                    )
                ),
            },
            "v4_policy_selected": False,
            "next_required_evidence": (
                "Visual review of confirmed parent-owned lower-TF lines to decide whether each "
                "lower-TF representation materially improves geometry at that chart scale."
            ),
            "production_changed": False,
            "renderer_changed": False,
            "snapshot_changed": False,
            "nca_draw_writeback": False,
        }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
