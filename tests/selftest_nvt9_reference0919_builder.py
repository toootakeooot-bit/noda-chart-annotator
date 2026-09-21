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
        line(8, "R0919-08", "M15", "MID_DOW", "RISING", 153.0),
    ]
    diag_results = [result(x["reference_id"], x["timeframe"], x["structure_level"], x["direction"]) for x in lines]

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        manifest = td / "manifest.json"
        diagnostic = td / "diagnostic.json"
        out = td / "out"
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
        assert index["selected_reference_ids"] == sorted(selected)
        assert index["reference_count"] == 4
        assert index["draw_row_count"] == 20  # 4 families x (TL,CH,2 edges,HL)

        csv_text = (out / "NVT9_0919_REFERENCE_DRAW.csv").read_text(encoding="utf-8")
        for rid in selected:
            assert f"{rid}-HL" in csv_text
            assert rid in csv_text

        print("NVT9_REFERENCE0919_BUILDER_SELFTEST_PASS")


if __name__ == "__main__":
    main()
