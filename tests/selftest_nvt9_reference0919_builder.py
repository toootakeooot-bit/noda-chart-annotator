from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "nvt" / "build_nvt9_0919_reference.py"


def line(no: int, rid: str, tf: str, level: str, direction: str, base: float) -> dict:
    return {
        "reference_no": no,
        "reference_id": rid,
        "timeframe": tf,
        "structure_level": level,
        "line_id": f"NCA_TEST_{tf}_{level}_G001",
        "generation": 1,
        "status": "ACTIVE",
        "direction": direction,
        "anchor1_time": "2026-09-01T00:00:00",
        "anchor1_price": base,
        "anchor2_time": "2026-09-10T00:00:00",
        "anchor2_price": base + (1.0 if direction == "RISING" else -1.0),
        "ch_offset": 2.0 if direction == "RISING" else -2.0,
        "zone_width": 0.1,
        "selection_version": "TEST",
    }


def result(rid: str, tf: str, level: str, direction: str) -> dict:
    kind = "HIGH" if direction == "RISING" else "LOW"
    return {
        "reference_id": rid,
        "production_600_replay": {
            "reference_candidate": {
                "candidate_id": f"{direction}:2026-09-01T00:00:00:2026-09-10T00:00:00",
                "turn_span": 10,
                "tl_contacts": 3,
                "ch_contacts": 4,
                "unbroken_close": True,
                "decision_hl_kind": kind,
                "decision_hl_time": "2026-09-05T00:00:00",
                "decision_hl_price": 150.0,
                "hl_break_time": "2026-09-06T00:00:00",
                "hl_break_mode": "CLOSED_BAR_CLOSE",
            },
            "reference_candidate_audit": {
                "candidate_audit_id": f"C-{tf}-R-0001",
                "anchor1_pivot_id": f"P-{tf}-L-001",
                "anchor2_pivot_id": f"P-{tf}-L-002",
                "channel_anchor_pivot_id": f"P-{tf}-H-001",
            },
            "selector_trace_decision": {
                "selected_candidate_audit_id": f"C-{tf}-R-0001",
                "selected_native_candidate_id": "native",
                "anchor1_pivot_id": f"P-{tf}-L-001",
                "anchor2_pivot_id": f"P-{tf}-L-002",
                "priority_order": ["turn_span", "ch_contacts"],
                "selected_metrics": {"turn_span": 10},
            },
            "selector_reason": {"turn_span": 10},
            "selector_reason_status": "REPRODUCED_600BAR_SELECTOR_REASON",
            "display_reason": "FROZEN_0919_CURRENT_NEAREST_FAMILY",
            "display_reason_detail": {"distance_to_channel": 0.0},
        },
    }


def main() -> None:
    selected = ["R0919-02", "R0919-03", "R0919-06", "R0919-08"]
    lines = [
        line(2, "R0919-02", "D1", "MID_DOW", "RISING", 140.0),
        line(3, "R0919-03", "H4", "LARGE_DOW", "FALLING", 164.0),
        line(6, "R0919-06", "H1", "MID_DOW", "FALLING", 160.0),
        {**line(8, "R0919-08", "M15", "MID_DOW", "RISING", 153.0), "zone_width": 0.0},
    ]
    diag_results = [result(x["reference_id"], x["timeframe"], x["structure_level"], x["direction"]) for x in lines]

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        manifest = td / "manifest.json"
        diagnostic = td / "diagnostic.json"
        out = td / "out"
        for row in lines:
            if row["reference_id"] == "R0919-06":
                row["display_override"] = {"status": "SUPPRESSED"}
        manifest.write_text(json.dumps({"symbol": "USDJPY#", "lines": lines}), encoding="utf-8")
        diagnostic.write_text(json.dumps({
            "production_600_display_selected_refs": selected,
            "input_coverage": {
                "D1": {"last_replay_bar": "2026-09-18T00:00:00"},
                "H4": {"last_replay_bar": "2026-09-18T16:00:00"},
                "H1": {"last_replay_bar": "2026-09-18T22:00:00"},
                "M15": {"last_replay_bar": "2026-09-18T23:30:00"},
            },
            "results": diag_results,
        }), encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--manifest", str(manifest), "--diagnostic", str(diagnostic), "--output-dir", str(out)],
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

        index = json.loads((out / "NVT9_0919_REFERENCE_INDEX.json").read_text(encoding="utf-8"))
        expected_selected = sorted(set(selected) - {"R0919-06"})
        assert index["selected_reference_ids"] == expected_selected
        assert index["suppressed_reference_ids"] == ["R0919-06"]
        assert index["reference_count"] == 3
        assert index["draw_row_count"] == 13  # 2 full families + R0919-08 zero-width + 3 recovered HL

        csv_text = (out / "NVT9_0919_REFERENCE_DRAW.csv").read_text(encoding="utf-8")
        for rid in expected_selected:
            assert f"{rid}-HL" in csv_text
            assert rid in csv_text
        assert "R0919-06" not in csv_text

        # Missing historical HL evidence must not block TL/CH restoration.
        pending_diag = json.loads(diagnostic.read_text(encoding="utf-8"))
        pending_diag["results"][0]["production_600_replay"]["reference_candidate"]["decision_hl_kind"] = None
        pending_diag["results"][0]["production_600_replay"]["reference_candidate"]["decision_hl_time"] = None
        pending_diag["results"][0]["production_600_replay"]["reference_candidate"]["decision_hl_price"] = None
        pending_path = td / "diagnostic_pending.json"
        pending_out = td / "out_pending"
        pending_path.write_text(json.dumps(pending_diag), encoding="utf-8")

        proc2 = subprocess.run(
            [sys.executable, str(SCRIPT), "--manifest", str(manifest), "--diagnostic", str(pending_path), "--output-dir", str(pending_out)],
            text=True,
            capture_output=True,
        )
        assert proc2.returncode == 0, proc2.stdout + proc2.stderr
        pending_index = json.loads((pending_out / "NVT9_0919_REFERENCE_INDEX.json").read_text(encoding="utf-8"))
        assert pending_index["reference_count"] == 3
        assert pending_index["hl_pending_count"] == 1
        assert pending_index["hl_pending_reference_ids"] == ["R0919-02"]
        assert pending_index["draw_row_count"] == 12

        print("NVT9_REFERENCE0919_BUILDER_SELFTEST_PASS")


if __name__ == "__main__":
    main()
