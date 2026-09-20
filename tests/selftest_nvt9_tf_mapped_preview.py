from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def state_line(tf: str, level: str, gen: int, *, direction: str, p1: float, p2: float, offset: float) -> dict:
    return {
        "line_id": f"NCA_TEST_{tf}_{level}_G{gen}",
        "symbol": "USDJPY#",
        "timeframe": tf,
        "structure_level": level,
        "generation": gen,
        "status": "ACTIVE",
        "direction": direction,
        "anchor1_time": "2025-01-01T00:00:00",
        "anchor1_price": p1,
        "anchor2_time": "2026-01-01T00:00:00",
        "anchor2_price": p2,
        "ch_offset": offset,
        "zone_width": 0.1,
    }


def write_input(path: Path, close: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time","open","high","low","close","volume"])
        w.writerow(["2026-09-18 23:00:00", close, close + 0.2, close - 0.2, close, 1])


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tool = repo / "tools" / "nvt" / "build_nvt9_tf_mapped_preview.py"
    policy = repo / "nvt" / "manifests" / "NVT9_TF_DISPLAY_MAP_0919_V01.json"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        input_dir = root / "input"
        for tf in ("D1", "H4", "H1", "M15"):
            write_input(input_dir / f"NVT_USDJPY#_{tf}.csv", 156.8)

        slots = {
            "USDJPY#|D1|LARGE_DOW": {
                "previous": state_line("D1","LARGE_DOW",1,direction="FALLING",p1=165,p2=160,offset=-3),
                "current": state_line("D1","LARGE_DOW",2,direction="FALLING",p1=164,p2=158,offset=-2),
                "history": [],
            },
            "USDJPY#|D1|MID_DOW": {
                "previous": state_line("D1","MID_DOW",3,direction="FALLING",p1=163,p2=159,offset=-2),
                "current": state_line("D1","MID_DOW",4,direction="FALLING",p1=162,p2=157.2,offset=-1),
                "history": [],
            },
            "USDJPY#|H4|LARGE_DOW": {
                "previous": state_line("H4","LARGE_DOW",5,direction="RISING",p1=150,p2=155.9,offset=1.2),
                "current": state_line("H4","LARGE_DOW",6,direction="RISING",p1=151,p2=156.7,offset=1.0),
                "history": [],
            },
            "USDJPY#|H4|MID_DOW": {
                "previous": state_line("H4","MID_DOW",7,direction="RISING",p1=152,p2=156.1,offset=0.8),
                "current": state_line("H4","MID_DOW",8,direction="RISING",p1=153,p2=156.75,offset=0.6),
                "history": [],
            },
            "USDJPY#|H1|LARGE_DOW": {
                "previous": state_line("H1","LARGE_DOW",9,direction="RISING",p1=154,p2=156.2,offset=0.7),
                "current": state_line("H1","LARGE_DOW",10,direction="RISING",p1=155,p2=156.82,offset=0.5),
                "history": [],
            },
            "USDJPY#|H1|MID_DOW": {
                "previous": state_line("H1","MID_DOW",11,direction="RISING",p1=155,p2=156.4,offset=0.4),
                "current": state_line("H1","MID_DOW",12,direction="RISING",p1=155.5,p2=156.79,offset=0.3),
                "history": [],
            },
            "USDJPY#|M15|LARGE_DOW": {
                "previous": state_line("M15","LARGE_DOW",13,direction="FALLING",p1=158,p2=157.1,offset=-0.4),
                "current": state_line("M15","LARGE_DOW",14,direction="FALLING",p1=157.5,p2=156.85,offset=-0.3),
                "history": [],
            },
            "USDJPY#|M15|MID_DOW": {
                "previous": state_line("M15","MID_DOW",15,direction="FALLING",p1=157.2,p2=156.95,offset=-0.2),
                "current": state_line("M15","MID_DOW",16,direction="FALLING",p1=157.0,p2=156.81,offset=-0.15),
                "history": [],
            },
        }

        state = {
            "schema": "nca-live-state/1.0",
            "research_status": "PASS_DEEP_LIFECYCLE_STATE",
            "symbol": "USDJPY#",
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
                "--input-dir", str(input_dir),
                "--output-dir", str(out),
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout

        audit = json.loads(
            (out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json").read_text(encoding="utf-8")
        )
        assert audit["status"] == "PASS_TF_MAPPED_PREVIEW"
        assert audit["display_sources"]["H4"] == ["D1", "H4"]
        assert audit["display_sources"]["H1"] == ["H4", "H1"]
        assert audit["display_sources"]["M15"] == ["H1", "M15"]
        assert audit["selection_policy"]["near_price_family_count"] == 2
        assert audit["selection_policy"]["far_direction_context_max_families"] == 1
        assert audit["production_changed"] is False
        assert audit["production_renderer_changed"] is False
        assert audit["nca_draw_writeback"] is False

        selected = audit["selected_families"]
        for chart_tf in ("D1","H4","H1","M15"):
            assert 1 <= audit["selected_family_counts"][chart_tf] <= 3
        h4_sources = {x["source_tf"] for x in selected if x["display_tf"] == "H4"}
        assert "D1" in h4_sources
        assert "H4" in h4_sources
        assert any(
            x["display_tf"] == "H4" and x["display_reason"] == "NEAR_CURRENT_PRICE"
            for x in selected
        )
        m15_sources = {x["source_tf"] for x in selected if x["display_tf"] == "M15"}
        assert "H1" in m15_sources
        assert "M15" in m15_sources
        assert any(
            x["display_tf"] == "M15" and x["display_reason"] == "NEAR_CURRENT_PRICE"
            for x in selected
        )

        with (out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            rows = list(csv.DictReader(f))
        assert {r["timeframe"] for r in rows} == {"D1","H4","H1","M15"}
        assert any(r["timeframe"] == "H4" and "SRC_D1" in r["object_id"] for r in rows)
        assert any(r["timeframe"] == "H4" and "SRC_H4" in r["object_id"] for r in rows)
        assert any(r["timeframe"] == "M15" and "SRC_H1" in r["object_id"] for r in rows)
        assert any(r["timeframe"] == "M15" and "SRC_M15" in r["object_id"] for r in rows)

    print("NVT9 TF DISPLAY MAP SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
