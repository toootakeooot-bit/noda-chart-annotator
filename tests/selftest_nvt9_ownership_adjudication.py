from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    builder = repo / "tools" / "nvt" / "build_nvt9_ownership_adjudication.py"
    gate = repo / "tools" / "nvt" / "evaluate_nvt9_ownership_gate.py"
    policy = repo / "nvt" / "manifests" / "NVT9_OWNERSHIP_ADJUDICATION_POLICY_0919_V01.json"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = root / "out"
        out.mkdir(parents=True, exist_ok=True)

        matrix = {
            "schema": "nvt9-cross-tf-review/0.2",
            "status": "PASS",
            "symbol": "USDJPY#",
            "comparisons": [
                {
                    "parent_tf": "D1",
                    "parent_level": "LARGE_DOW",
                    "parent_generation_role": "CURRENT",
                    "parent_line_id": "D1_A",
                    "parent_direction": "RISING",
                    "child_tf": "H4",
                    "child_level": "LARGE_DOW",
                    "child_generation_role": "CURRENT",
                    "child_line_id": "H4_A",
                    "child_direction": "RISING",
                    "direction_match": True,
                    "relation_without_threshold": "EXACT_GEOMETRY_SAME_FAMILY",
                    "tl_gap_at_eval_start": 0.0,
                    "tl_gap_at_eval_end": 0.0,
                    "tl_gap_end_over_max_channel_width": 0.0,
                    "slope_abs_diff_price_per_day": 0.0,
                    "parent_anchor_span_hours": 240.0,
                    "child_anchor_span_hours": 240.0,
                    "child_span_over_parent_span": 1.0,
                    "anchor1_time_diff_hours": 0.0,
                    "anchor2_time_diff_hours": 0.0,
                    "parent_ch_offset": 4.0,
                    "child_ch_offset": 3.0
                },
                {
                    "parent_tf": "H4",
                    "parent_level": "LARGE_DOW",
                    "parent_generation_role": "CURRENT",
                    "parent_line_id": "H4_A",
                    "parent_direction": "RISING",
                    "child_tf": "H1",
                    "child_level": "LARGE_DOW",
                    "child_generation_role": "CURRENT",
                    "child_line_id": "H1_A",
                    "child_direction": "RISING",
                    "direction_match": True,
                    "relation_without_threshold": "PENDING_TEACHER_CALIBRATION",
                    "tl_gap_at_eval_start": 0.1,
                    "tl_gap_at_eval_end": 0.2,
                    "tl_gap_end_over_max_channel_width": 0.05,
                    "slope_abs_diff_price_per_day": 0.03,
                    "parent_anchor_span_hours": 240.0,
                    "child_anchor_span_hours": 96.0,
                    "child_span_over_parent_span": 0.4,
                    "anchor1_time_diff_hours": 120.0,
                    "anchor2_time_diff_hours": 0.0,
                    "parent_ch_offset": 3.0,
                    "child_ch_offset": 1.5
                }
            ]
        }
        matrix_path = root / "matrix.json"
        matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

        proc = subprocess.run(
            [
                sys.executable,
                str(builder),
                "--matrix",
                str(matrix_path),
                "--policy",
                str(policy),
                "--output-dir",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout

        adjudication_path = out / "NVT9_USDJPY_OWNERSHIP_ADJUDICATION_0919.json"
        adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
        assert adjudication["status"] == "BLOCKED_PENDING_ADJUDICATION"
        assert adjudication["record_count"] == 2
        assert adjudication["auto_resolved_count"] == 1
        assert adjudication["ambiguous_count"] == 1

        by_tf = {r["source_tf"]: r for r in adjudication["records"]}
        assert by_tf["H4"]["classification"] == "PARENT_OWNED_SAME_FAMILY"
        assert by_tf["H4"]["structural_owner_tf"] == "D1"
        assert by_tf["H4"]["same_family_parent_id"] == "D1_A"
        assert by_tf["H4"]["adjudication_required"] is False

        assert by_tf["H1"]["classification"] == "AMBIGUOUS_KEEP_VISIBLE"
        assert by_tf["H1"]["structural_owner_tf"] == "H1"
        assert by_tf["H1"]["adjudication_required"] is True
        assert by_tf["H1"]["user_observed_owner_candidate_tf"] == "H4"

        gate_path = out / "gate.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(gate),
                "--adjudication",
                str(adjudication_path),
                "--output",
                str(gate_path),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
        assert gate_payload["status"] == "BLOCKED_V3_5"
        assert gate_payload["v4_unblocked"] is False
        assert gate_payload["unresolved_count"] == 1
        assert gate_payload["problem_count"] == 0

        # Simulate a completed human/teacher adjudication for the non-exact H1 row.
        for rec in adjudication["records"]:
            if rec["source_tf"] == "H1":
                rec["classification"] = "PARENT_OWNED_SAME_FAMILY"
                rec["structural_owner_tf"] = "H4"
                rec["same_family_parent_id"] = "H4_A"
                rec["relation"] = "MANUAL_TEACHER_CONFIRMED_SAME_FAMILY"
                rec["adjudication_required"] = False

        completed = out / "completed.json"
        completed.write_text(json.dumps(adjudication), encoding="utf-8")
        passed_gate = out / "gate_pass.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(gate),
                "--adjudication",
                str(completed),
                "--output",
                str(passed_gate),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        gate_payload = json.loads(passed_gate.read_text(encoding="utf-8"))
        assert gate_payload["status"] == "PASS_V3_5"
        assert gate_payload["v4_unblocked"] is True
        assert gate_payload["unresolved_count"] == 0
        assert gate_payload["problem_count"] == 0

    print("NVT9 OWNERSHIP ADJUDICATION SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
