from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

FIELDS = [
    "object_id", "symbol", "timeframe", "structure_level", "role",
    "t1", "p1", "t2", "p2", "generation_role", "generation", "status", "extent",
]


def snap_row(line_id: str, tf: str, level: str, gen_role: str, gen: str, role: str) -> dict:
    return {
        "object_id": f"{line_id}__{role}",
        "symbol": "USDJPY#",
        "timeframe": tf,
        "structure_level": level,
        "role": role,
        "t1": "2026.01.01 00:00:00",
        "p1": "100",
        "t2": "2026.01.02 00:00:00",
        "p2": "101",
        "generation_role": gen_role,
        "generation": gen,
        "status": "ACTIVE",
        "extent": "RAY_RIGHT",
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    template_tool = repo / "tools" / "nvt" / "build_nvt9_v4_display_template.py"
    preview_tool = repo / "tools" / "nvt" / "build_nvt9_v6_visibility_preview.py"
    validator = repo / "tools" / "nvt" / "validate_nvt9_visibility_invariants.py"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = root / "out"
        out.mkdir(parents=True, exist_ok=True)

        v4 = {
            "status": "READY_FOR_VISUAL_POLICY_SELECTION",
        }
        adj = {
            "records": [
                {
                    "source_tf": "H1",
                    "line_id": "H1_LARGE",
                    "structure_level": "LARGE_DOW",
                    "generation_role": "CURRENT",
                    "classification": "PARENT_OWNED_SAME_FAMILY",
                    "structural_owner_tf": "H4",
                    "same_family_parent_id": "H4_LARGE",
                }
            ]
        }
        v4_path = root / "v4.json"
        adj_path = root / "adj.json"
        v4_path.write_text(json.dumps(v4), encoding="utf-8")
        adj_path.write_text(json.dumps(adj), encoding="utf-8")

        template_path = root / "display_template.json"
        proc = subprocess.run(
            [
                sys.executable, str(template_tool),
                "--v4", str(v4_path),
                "--adjudication", str(adj_path),
                "--output", str(template_path),
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        template = json.loads(template_path.read_text(encoding="utf-8"))
        assert template["status"] == "READY_FOR_EXPLICIT_DISPLAY_DECISIONS"
        assert template["decision_count"] == 4

        by_role = {d["role"]: d for d in template["decisions"]}
        assert by_role["TL"]["selected_visibility"] == "DRAW"
        assert by_role["TL"]["locked_by_teacher_invariant"] is True
        assert by_role["CH"]["selected_visibility"] == "DRAW"
        assert by_role["TL_ZONE_EDGE"]["selected_visibility"] is None

        by_role["TL_ZONE_EDGE"]["selected_visibility"] = "SUPPRESSED"
        by_role["TL_ZONE_EDGE"]["evidence_note"] = "selftest redundant zone edge"
        by_role["CH_ZONE_EDGE"]["selected_visibility"] = "REFERENCE"
        by_role["CH_ZONE_EDGE"]["evidence_note"] = "selftest retain reference"
        decisions_path = root / "display_decisions.json"
        decisions_path.write_text(json.dumps(template), encoding="utf-8")

        rows = []
        for role in ("TL", "CH", "TL_ZONE_EDGE", "CH_ZONE_EDGE"):
            rows.append(snap_row("H1_LARGE", "H1", "LARGE_DOW", "CURRENT", "2", role))
        for role in ("TL", "CH"):
            rows.append(snap_row("H1_PREV", "H1", "LARGE_DOW", "PREVIOUS", "1", role))
        rows.append(snap_row("H1_MID", "H1", "MID_DOW", "CURRENT", "3", "TL"))
        rows.append(snap_row("H1_MID", "H1", "MID_DOW", "CURRENT", "3", "CH"))

        snapshot = root / "snapshot.csv"
        with snapshot.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)

        proc = subprocess.run(
            [
                sys.executable, str(preview_tool),
                "--snapshot", str(snapshot),
                "--decisions", str(decisions_path),
                "--output-dir", str(out),
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        audit = json.loads((out / "snapshot_V6_0919_audit.json").read_text(encoding="utf-8"))
        assert audit["status"] == "PASS_V6_PREVIEW"
        assert audit["suppressed_counts"]["H1"] == 1
        assert audit["counts_before"]["H1"] == 8
        assert audit["counts_after"]["H1"] == 7

        preview = out / "snapshot_V6_0919.csv"
        reg = out / "regression.json"
        proc = subprocess.run(
            [sys.executable, str(validator), "--preview", str(preview), "--output", str(reg)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        regression = json.loads(reg.read_text(encoding="utf-8"))
        assert regression["status"] == "PASS_V5"

        # Locked H1 LARGE_DOW CURRENT TL may never be suppressed.
        bad = json.loads(decisions_path.read_text(encoding="utf-8"))
        for d in bad["decisions"]:
            if d["role"] == "TL":
                d["selected_visibility"] = "SUPPRESSED"
        bad_path = root / "bad_decisions.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable, str(preview_tool),
                "--snapshot", str(snapshot),
                "--decisions", str(bad_path),
                "--output-dir", str(out),
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode == 6

    print("NVT9 V4/V6 PREVIEW SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
