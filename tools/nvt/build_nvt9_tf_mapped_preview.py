from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROLES = ("TL", "CH", "TL_ZONE_EDGE", "CH_ZONE_EDGE")
GEN_ROLES = ("previous", "current")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mt4_datetime(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%Y.%m.%d %H:%M:%S")


def line_points(s: dict, role: str) -> tuple[float, float]:
    p1 = float(s["anchor1_price"])
    p2 = float(s["anchor2_price"])
    offset = float(s["ch_offset"])
    width = float(s["zone_width"])
    direction = s["direction"]

    if role == "TL":
        return p1, p2
    if role == "CH":
        return p1 + offset, p2 + offset
    if role == "TL_ZONE_EDGE":
        z = width if direction == "RISING" else -width
        return p1 + z, p2 + z
    if role == "CH_ZONE_EDGE":
        z = -width if direction == "RISING" else width
        return p1 + offset + z, p2 + offset + z
    raise ValueError(role)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build research-only one-step-lower timeframe display preview from deep lifecycle state."
    )
    ap.add_argument("--state", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    state_path = Path(args.state)
    policy_path = Path(args.policy)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    state = load_json(state_path)
    policy = load_json(policy_path)
    mapping = policy.get("mapping") or {}

    if state.get("research_status") != "PASS_DEEP_LIFECYCLE_STATE":
        raise ValueError(f"deep lifecycle state is not PASS: {state.get('research_status')}")

    rows = []
    audit_rows = []
    source_counts = Counter()
    display_counts = Counter()
    suppressed_source_counts = Counter()

    for _, slot in sorted((state.get("slots") or {}).items()):
        for gen_role in GEN_ROLES:
            s = slot.get(gen_role)
            if not s:
                continue

            source_tf = s["timeframe"]
            display_tf = mapping.get(source_tf)
            source_counts[source_tf] += len(ROLES)

            if display_tf is None:
                suppressed_source_counts[source_tf] += len(ROLES)
                for role in ROLES:
                    audit_rows.append({
                        "source_tf": source_tf,
                        "structural_owner_tf": source_tf,
                        "display_tf": None,
                        "line_id": s["line_id"],
                        "structure_level": s["structure_level"],
                        "generation_role": gen_role.upper(),
                        "role": role,
                        "action": "NO_INDEPENDENT_DISPLAY",
                        "reason": "TF_DISPLAY_MAP_POLICY",
                    })
                continue

            for role in ROLES:
                p1, p2 = line_points(s, role)
                object_id = (
                    f"TFMAP__SRC_{source_tf}__DST_{display_tf}__"
                    f"{s['line_id']}__{role}"
                )
                rows.append([
                    object_id,
                    s["symbol"],
                    display_tf,
                    s["structure_level"],
                    role,
                    mt4_datetime(s["anchor1_time"]),
                    f"{p1:.8f}",
                    mt4_datetime(s["anchor2_time"]),
                    f"{p2:.8f}",
                    gen_role.upper(),
                    str(s["generation"]),
                    s["status"],
                    "RAY_RIGHT",
                ])
                display_counts[display_tf] += 1
                audit_rows.append({
                    "source_tf": source_tf,
                    "structural_owner_tf": source_tf,
                    "display_tf": display_tf,
                    "line_id": s["line_id"],
                    "structure_level": s["structure_level"],
                    "generation_role": gen_role.upper(),
                    "role": role,
                    "action": "DRAW_ON_MAPPED_LOWER_TF",
                    "reason": "TF_DISPLAY_MAP_POLICY",
                })

    header = [
        "object_id","symbol","timeframe","structure_level","role",
        "t1","p1","t2","p2","generation_role","generation","status","extent",
    ]
    csv_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"
    audit_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    expected_display_counts = {}
    for source_tf, display_tf in mapping.items():
        if display_tf is not None:
            expected_display_counts[display_tf] = source_counts.get(source_tf, 0)

    problems = []
    for tf, expected in expected_display_counts.items():
        actual = display_counts.get(tf, 0)
        if actual != expected:
            problems.append({
                "display_tf": tf,
                "reason": "DISPLAY_COUNT_MISMATCH",
                "expected": expected,
                "actual": actual,
            })
    if display_counts.get("D1", 0) != 0:
        problems.append({"display_tf": "D1", "reason": "D1_SHOULD_HAVE_NO_MAPPED_ROWS"})
    if suppressed_source_counts.get("M15", 0) != source_counts.get("M15", 0):
        problems.append({"source_tf": "M15", "reason": "M15_SOURCE_NOT_FULLY_SUPPRESSED"})

    status = "PASS_TF_MAPPED_PREVIEW" if not problems else "FAIL_TF_MAPPED_PREVIEW"
    audit = {
        "schema": "nvt9-tf-mapped-preview/0.1",
        "status": status,
        "audit_id": "ID10IQ200",
        "source_state": str(state_path),
        "display_policy": str(policy_path),
        "mapping": mapping,
        "source_row_counts": dict(source_counts),
        "display_row_counts": dict(display_counts),
        "suppressed_source_row_counts": dict(suppressed_source_counts),
        "expected_display_row_counts": expected_display_counts,
        "row_count": len(rows),
        "problems": problems,
        "rows": audit_rows,
        "semantics": {
            "csv_timeframe_column": "DISPLAY_TF_FOR_RESEARCH_RENDERER",
            "structural_owner_tf": "SOURCE_TF",
            "m15_source_displayed": False,
        },
        "production_changed": False,
        "production_snapshot_changed": False,
        "production_renderer_changed": False,
        "nca_draw_writeback": False,
        "trade_authority": False,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": status,
        "mapping": mapping,
        "display_row_counts": dict(display_counts),
        "suppressed_source_row_counts": dict(suppressed_source_counts),
        "csv": str(csv_path),
        "audit": str(audit_path),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if status == "PASS_TF_MAPPED_PREVIEW" else 6


if __name__ == "__main__":
    raise SystemExit(main())
