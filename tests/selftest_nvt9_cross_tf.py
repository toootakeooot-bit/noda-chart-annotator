from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def write_csv(path: Path, tf: str) -> None:
    rows = [
        ["2026-09-18 20:00:00", "100", "101", "99", "100.5", "1"],
        ["2026-09-18 23:00:00", "100.5", "102", "100", "101.5", "1"],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        w.writerows(rows)


def line(
    *,
    tf: str,
    line_id: str,
    direction: str,
    a1_time: str,
    a1_price: float,
    a2_time: str,
    a2_price: float,
    ch_offset: float,
) -> dict:
    return {
        "symbol": "USDJPY#",
        "timeframe": tf,
        "structure_level": "LARGE_DOW",
        "generation_role": "CURRENT",
        "line_id": line_id,
        "direction": direction,
        "anchor1_time": a1_time,
        "anchor1_price": a1_price,
        "anchor2_time": a2_time,
        "anchor2_price": a2_price,
        "ch_offset": ch_offset,
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tool = repo / "tools" / "nvt" / "build_cross_tf_review.py"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        input_dir = root / "input"
        output_dir = root / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        for tf in ("D1", "H4", "H1", "M15"):
            write_csv(input_dir / f"NORMAL_USDJPY#_{tf}.csv", tf)

        d1 = line(
            tf="D1",
            line_id="D1_A",
            direction="RISING",
            a1_time="2026-09-01T00:00:00",
            a1_price=100.0,
            a2_time="2026-09-10T00:00:00",
            a2_price=109.0,
            ch_offset=4.0,
        )
        h4 = line(
            tf="H4",
            line_id="H4_A",
            direction="RISING",
            a1_time="2026-09-01T00:00:00",
            a1_price=100.0,
            a2_time="2026-09-10T00:00:00",
            a2_price=109.0,
            ch_offset=3.0,
        )
        h1 = line(
            tf="H1",
            line_id="H1_A",
            direction="RISING",
            a1_time="2026-09-06T00:00:00",
            a1_price=104.5,
            a2_time="2026-09-10T00:00:00",
            a2_price=108.7,
            ch_offset=1.5,
        )
        m15 = line(
            tf="M15",
            line_id="M15_A",
            direction="FALLING",
            a1_time="2026-09-09T00:00:00",
            a1_price=110.0,
            a2_time="2026-09-10T00:00:00",
            a2_price=108.0,
            ch_offset=-0.8,
        )

        state = {
            "slots": {
                "d1": {"current": d1},
                "h4": {"current": h4},
                "h1": {"current": h1},
                "m15": {"current": m15},
            }
        }
        state_path = root / "state.json"
        state_path.write_text(json.dumps(state), encoding="utf-8")

        cmd = [
            sys.executable,
            str(tool),
            "--symbol",
            "USDJPY#",
            "--state",
            str(state_path),
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr + proc.stdout

        payload = json.loads(
            (output_dir / "NVT9_USDJPY_CROSS_TF_0919.json").read_text(encoding="utf-8")
        )
        assert payload["schema"] == "nvt9-cross-tf-review/0.2"
        assert payload["comparison_count"] == 3
        assert payload["production_changed"] is False
        assert payload["renderer_changed"] is False
        assert payload["snapshot_changed"] is False
        assert payload["nca_draw_writeback"] is False
        assert payload["classification_policy"]["numeric_threshold_frozen"] is False
        assert payload["classification_policy"]["time_span_threshold_frozen"] is False

        by_pair = {
            (x["parent_tf"], x["child_tf"]): x
            for x in payload["comparisons"]
        }

        d1_h4 = by_pair[("D1", "H4")]
        assert d1_h4["relation_without_threshold"] == "EXACT_GEOMETRY_SAME_FAMILY"
        assert d1_h4["parent_generation_role"] == "CURRENT"
        assert d1_h4["child_generation_role"] == "CURRENT"
        assert abs(d1_h4["child_span_over_parent_span"] - 1.0) < 1e-12

        h4_h1 = by_pair[("H4", "H1")]
        assert h4_h1["relation_without_threshold"] == "PENDING_TEACHER_CALIBRATION"
        assert 0.0 < h4_h1["child_span_over_parent_span"] < 1.0
        assert h4_h1["parent_anchor_span_hours"] > h4_h1["child_anchor_span_hours"]

        h1_m15 = by_pair[("H1", "M15")]
        assert h1_m15["direction_match"] is False
        assert h1_m15["relation_without_threshold"] == "DISTINCT_DIRECTION_EVIDENCE"

    print("NVT9 CROSS-TF SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
