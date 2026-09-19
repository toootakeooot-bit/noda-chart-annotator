from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate NVT9 09/19 teacher visibility invariants on an audit preview."
    )
    ap.add_argument("--preview", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    preview = Path(args.preview)
    with preview.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    h1 = [r for r in rows if r.get("timeframe") == "H1"]
    checks = {}

    def exists(level: str | None, generation_role: str | None, role: str) -> bool:
        for r in h1:
            if level and r.get("structure_level") != level:
                continue
            if generation_role and r.get("generation_role") != generation_role:
                continue
            if r.get("role") == role:
                return True
        return False

    checks["large_current_tl_drawable"] = exists("LARGE_DOW", "CURRENT", "TL")
    checks["large_current_ch_drawable"] = exists("LARGE_DOW", "CURRENT", "CH")
    checks["previous_reference_tl_retained"] = exists(None, "PREVIOUS", "TL")
    checks["previous_reference_ch_retained"] = exists(None, "PREVIOUS", "CH")

    state_keys = {
        (
            r.get("structure_level"),
            r.get("generation_role"),
            r.get("generation"),
        )
        for r in h1
        if r.get("structure_level") and r.get("generation_role")
    }
    checks["h1_multiple_structural_states_coexist"] = len(state_keys) >= 2

    object_ids = [r.get("object_id") for r in rows if r.get("object_id")]
    checks["object_ids_unique"] = len(object_ids) == len(set(object_ids))

    failed = [k for k, v in checks.items() if not v]
    status = "PASS_V5" if not failed else "FAIL_V5"

    payload = {
        "schema": "nvt9-visibility-invariant-regression/0.1",
        "status": status,
        "audit_id": "ID10IQ200",
        "source_preview": str(preview),
        "row_count": len(rows),
        "h1_row_count": len(h1),
        "checks": checks,
        "failed_checks": failed,
        "teacher_scope_note": (
            "Checks are limited to frozen 09/19 H1 visibility/coexistence invariants. "
            "They do not prove exact teacher geometry or Production readiness."
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
    return 0 if status == "PASS_V5" else 5


if __name__ == "__main__":
    raise SystemExit(main())
