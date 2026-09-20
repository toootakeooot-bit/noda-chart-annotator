from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def state_line(tf: str, level: str, gen: int) -> dict:
    return {
        "line_id": f"NCA_TEST_{tf}_{level}_G{gen}",
        "symbol": "USDJPY#",
        "timeframe": tf,
        "structure_level": level,
        "generation": gen,
        "status": "ACTIVE",
        "direction": "RISING",
        "anchor1_time": "2025-01-01T00:00:00",
        "anchor1_price": 100.0,
        "anchor2_time": "2026-01-01T00:00:00",
        "anchor2_price": 110.0,
        "ch_offset": 3.0,
        "zone_width": 0.1,
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tool = repo / "tools" / "nvt" / "build_nvt9_tf_mapped_preview.py"
    policy = repo / "nvt" / "manifests" / "NVT9_TF_DISPLAY_MAP_0919_V01.json"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        slots = {}
        gen = 1
        for tf in ("D1", "H4", "H1", "M15"):
            for level in ("LARGE_DOW", "MID_DOW"):
                slots[f"USDJPY#|{tf}|{level}"] = {
                    "previous": state_line(tf, level, gen),
                    "current": state_line(tf, level, gen + 1),
                    "history": [],
                }
                gen += 2

        state = {
            "schema": "nca-live-state/1.0",
            "research_status": "PASS_DEEP_LIFECYCLE_STATE",
            "slots": slots,
        }
        state_path = root / "state.json"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        out = root / "out"

        proc = subprocess.run(
            [
                sys.executable, str(tool),
                "--state", str(state_path),
                "--policy", str(policy),
                "--output-dir", str(out),
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout

        audit = json.loads(
            (out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json").read_text(encoding="utf-8")
        )
        assert audit["status"] == "PASS_TF_MAPPED_PREVIEW"
        assert audit["display_row_counts"] == {"H4": 16, "H1": 16, "M15": 16}
        assert audit["suppressed_source_row_counts"] == {"M15": 16}
        assert audit["row_count"] == 48
        assert audit["production_changed"] is False
        assert audit["production_renderer_changed"] is False
        assert audit["nca_draw_writeback"] is False

        with (out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = list(csv.DictReader(f))
        assert {r["timeframe"] for r in rows} == {"H4", "H1", "M15"}
        assert not any("SRC_M15" in r["object_id"] for r in rows)
        assert all(r["object_id"].startswith("TFMAP__SRC_") for r in rows)
        assert sum(1 for r in rows if r["timeframe"] == "H4" and "SRC_D1" in r["object_id"]) == 16
        assert sum(1 for r in rows if r["timeframe"] == "H1" and "SRC_H4" in r["object_id"]) == 16
        assert sum(1 for r in rows if r["timeframe"] == "M15" and "SRC_H1" in r["object_id"]) == 16

    print("NVT9 TF DISPLAY MAP SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
