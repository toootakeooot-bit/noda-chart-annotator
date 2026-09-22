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
        "decision_hl_time": "2025-06-01T00:00:00",
        "decision_hl_price": (156.0 if direction == "FALLING" else 158.0),
        "decision_hl_kind": ("LOW" if direction == "FALLING" else "HIGH"),
        "hl_break_time": "2026-02-01T00:00:00",
        "hl_break_mode": "CLOSED_BAR_CLOSE_PROVISIONAL",
    }


def write_input(path: Path, close: float) -> None:
    # Synthetic alternating structure with >38% closed-bar reactions so the
    # Turn detector produces confirmed pivots and an HL research candidate.
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ["2026-09-18 16:00:00", 156.0, 157.0, 155.0, 156.0, 1],
        ["2026-09-18 17:00:00", 156.0, 161.0, 156.0, 160.0, 1],
        ["2026-09-18 18:00:00", 160.0, 160.0, 158.0, 158.0, 1],
        ["2026-09-18 19:00:00", 158.0, 158.0, 154.0, 155.0, 1],
        ["2026-09-18 20:00:00", 155.0, 157.0, 155.0, 157.0, 1],
        ["2026-09-18 21:00:00", 157.0, 162.0, 157.0, 161.0, 1],
        ["2026-09-18 22:00:00", 161.0, 161.0, 158.0, 158.0, 1],
        ["2026-09-18 23:00:00", 158.0, 158.0, 153.0, close, 1],
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time","open","high","low","close","volume"])
        w.writerows(rows)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tool = repo / "tools" / "nvt" / "build_nvt9_tf_mapped_preview.py"
    policy = repo / "nvt" / "manifests" / "NVT9_TF_DISPLAY_MAP_0919_V01.json"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        input_dir = root / "input"
        for tf in ("D1", "H4", "H1", "M15"):
            write_input(input_dir / f"NVT_USDJPY#_{tf}.csv", 156.8)
            write_input(input_dir / f"NORMAL_USDJPY#_{tf}.csv", 156.8)

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
        assert audit["display_sources"]["D1"] == ["D1", "H4"]
        assert audit["display_sources"]["H4"] == ["H4", "H1"]
        assert audit["display_sources"]["H1"] == ["H1", "M15"]
        assert audit["display_sources"]["M15"] == ["M15"]
        assert audit["selection_policy"]["near_price_family_per_source_tf"] == 1
        assert audit["selection_policy"]["far_direction_context_max_families"] == 0
        assert audit["selection_policy"]["generation_scope"] == "CURRENT_ONLY"
        assert audit["hl_preview_policy"]["always_draw"] is True
        assert audit["hl_preview_policy"]["break_logic_applied"] is False
        assert audit["hl_preview_policy"]["retracement_38_role"] == "PIVOT_CONFIRMATION_ONLY_NOT_HL"
        assert set(audit["hl_candidates"]) == {"D1", "H4", "H1", "M15"}
        assert all(v["always_draw"] is True for v in audit["hl_candidates"].values())
        assert all(
            v["selection_rule"] == "SELECTED_TL_DECISION_HL"
            for v in audit["hl_candidates"].values()
        )
        assert all(
            v["retracement_38_role"] == "PIVOT_CONFIRMATION_ONLY_NOT_HL"
            for v in audit["hl_candidates"].values()
        )
        assert all(
            v["hl_break_mode"] == "CLOSED_BAR_CLOSE_PROVISIONAL"
            for v in audit["hl_candidates"].values()
        )
        assert audit["production_changed"] is False
        assert audit["production_renderer_changed"] is False
        assert audit["nca_draw_writeback"] is False

        selected = audit["selected_families"]
        assert audit["selected_family_counts"]["D1"] == 2
        assert audit["selected_family_counts"]["H4"] == 2
        assert audit["selected_family_counts"]["H1"] == 2
        assert audit["selected_family_counts"]["M15"] == 1
        assert audit["selected_source_counts"]["D1"] == {"D1": 1, "H4": 1}
        assert audit["selected_source_counts"]["H4"] == {"H4": 1, "H1": 1}
        assert audit["selected_source_counts"]["H1"] == {"H1": 1, "M15": 1}
        assert audit["selected_source_counts"]["M15"] == {"M15": 1}
        assert audit["source_presence_problems"] == []
        assert audit["source_to_display_tfs"]["H4"] == ["H4", "D1"]
        assert audit["source_to_display_tfs"]["H1"] == ["H1", "H4"]
        assert audit["source_to_display_tfs"]["M15"] == ["M15", "H1"]

        h4_source_sig = audit["source_selection"]["H4"][0]["geometry_signature"]
        h4_copies = [
            x for x in audit["selected_families"]
            if x["source_tf"] == "H4" and x["display_tf"] in {"H4", "D1"}
        ]
        assert len(h4_copies) == 2
        assert {tuple(x["geometry_signature"]) for x in h4_copies} == {tuple(h4_source_sig)}
        assert all(x["copied_without_reselection"] is True for x in h4_copies)
        assert all(x["generation_role"] == "CURRENT" for x in audit["selected_families"])
        d1_sources = {x["source_tf"] for x in selected if x["display_tf"] == "D1"}
        assert "D1" in d1_sources
        assert "H4" in d1_sources
        h4_sources = {x["source_tf"] for x in selected if x["display_tf"] == "H4"}
        assert "H4" in h4_sources
        assert "H1" in h4_sources
        assert all(
            x["display_reason"] == "SOURCE_TF_NEAREST_FAMILY"
            for x in selected
        )
        h1_sources = {x["source_tf"] for x in selected if x["display_tf"] == "H1"}
        assert "H1" in h1_sources
        assert "M15" in h1_sources
        m15_sources = {x["source_tf"] for x in selected if x["display_tf"] == "M15"}
        assert m15_sources == {"M15"}
        assert any(
            x["display_tf"] == "M15" and x["display_reason"] == "SOURCE_TF_NEAREST_FAMILY"
            for x in selected
        )

        csv_path = out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"
        raw = csv_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert raw.startswith(b"object_id,")
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert {r["timeframe"] for r in rows} == {"D1","H4","H1","M15"}
        assert any(r["timeframe"] == "D1" and r["object_id"].startswith("SRC_H4_DST_D1_") for r in rows)
        assert any(r["timeframe"] == "H4" and r["object_id"].startswith("SRC_H1_DST_H4_") for r in rows)
        assert any(r["timeframe"] == "H1" and r["object_id"].startswith("SRC_M15_DST_H1_") for r in rows)
        assert any(r["timeframe"] == "M15" and r["object_id"].startswith("SRC_M15_DST_M15_") for r in rows)
        hl_rows = [r for r in rows if r["role"] == "HL"]
        assert len(hl_rows) == 4
        assert {r["timeframe"] for r in hl_rows} == {"D1", "H4", "H1", "M15"}
        assert all(r["structure_level"] in {"HL_HIGH", "HL_LOW"} for r in hl_rows)
        assert all(float(r["p1"]) == float(r["p2"]) for r in hl_rows)
        for tf in ("D1", "H4", "H1", "M15"):
            tf_hl = [r for r in hl_rows if r["timeframe"] == tf]
            assert len(tf_hl) == 1
            expected_side = audit["hl_candidates"][tf]["pivot_kind"]
            assert tf_hl[0]["structure_level"] == f"HL_{expected_side}"
            assert tf_hl[0]["object_id"] == f"HL_{expected_side}_SRC_{tf}_DST_{tf}"
        assert audit["object_name_policy"]["max_full_object_name_length"] <= 63
        assert all(len("NVT9_TFMAP__" + r["object_id"]) <= 63 for r in rows)

        # Actual NormalRun live-state mode used by the local runner.
        normal_state = dict(state)
        normal_state.pop("research_status", None)
        normal_state_path = root / "normal_state.json"
        normal_state_path.write_text(json.dumps(normal_state), encoding="utf-8")
        normal_out = root / "normal_out"
        proc = subprocess.run(
            [
                sys.executable, str(tool),
                "--state", str(normal_state_path),
                "--policy", str(policy),
                "--input-dir", str(input_dir),
                "--input-prefix", "NORMAL",
                "--output-dir", str(normal_out),
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        normal_audit = json.loads(
            (normal_out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json").read_text(encoding="utf-8")
        )
        assert normal_audit["source_state_mode"] == "NORMAL_RUN_LIVE_STATE"
        assert normal_audit["input_prefix"] == "NORMAL"
        assert normal_audit["selection_policy"]["generation_scope"] == "CURRENT_ONLY"
        assert set(normal_audit["hl_candidates"]) == {"D1", "H4", "H1", "M15"}
        assert all(v["always_draw"] is True for v in normal_audit["hl_candidates"].values())
        assert normal_audit["hl_preview_policy"]["always_draw"] is True
        assert normal_audit["selected_source_counts"]["D1"] == {"D1": 1, "H4": 1}
        assert normal_audit["source_presence_problems"] == []

        # Historical NO-LINE contract: strict mode must still fail when a
        # source TF has no CURRENT family. Explicit research allow-mode may
        # accept exactly that TF without synthesizing a replacement line.
        no_line_state = json.loads(json.dumps(state))
        no_line_state["slots"]["USDJPY#|H4|LARGE_DOW"]["current"] = None
        no_line_state["slots"]["USDJPY#|H4|MID_DOW"]["current"] = None
        no_line_path = root / "no_line_state.json"
        no_line_path.write_text(json.dumps(no_line_state), encoding="utf-8")

        strict_out = root / "strict_no_line_out"
        strict_proc = subprocess.run(
            [
                sys.executable, str(tool),
                "--state", str(no_line_path),
                "--policy", str(policy),
                "--input-dir", str(input_dir),
                "--output-dir", str(strict_out),
            ],
            capture_output=True, text=True,
        )
        assert strict_proc.returncode != 0
        assert "source selection missing: H4 selected=0 expected=1" in (strict_proc.stderr + strict_proc.stdout)

        allowed_out = root / "allowed_no_line_out"
        allowed_proc = subprocess.run(
            [
                sys.executable, str(tool),
                "--state", str(no_line_path),
                "--policy", str(policy),
                "--input-dir", str(input_dir),
                "--output-dir", str(allowed_out),
                "--allow-empty-source-tf", "H4",
            ],
            capture_output=True, text=True,
        )
        assert allowed_proc.returncode == 0, allowed_proc.stderr + allowed_proc.stdout
        allowed_audit = json.loads(
            (allowed_out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json").read_text(encoding="utf-8")
        )
        assert allowed_audit["status"] == "PASS_TF_MAPPED_PREVIEW"
        assert allowed_audit["allow_empty_source_tfs"] == ["H4"]
        assert allowed_audit["empty_source_tfs"] == ["H4"]
        assert allowed_audit["source_selection"]["H4"] == []
        assert "H4" not in allowed_audit["hl_candidates"]
        assert allowed_audit["source_presence_problems"] == []
        assert allowed_audit["selection_policy"]["empty_source_semantics"] == "NO_LINE_NO_SYNTHETIC_FALLBACK"
        assert not any(x["source_tf"] == "H4" for x in allowed_audit["selected_families"])

        # Explicit source-direction suppression removes the selected source,
        # its source HL, and every Plan-B copy without selecting a replacement.
        suppress_state = json.loads(json.dumps(state))
        suppress_state["slots"]["USDJPY#|H1|LARGE_DOW"]["current"]["direction"] = "FALLING"
        suppress_state["slots"]["USDJPY#|H1|MID_DOW"]["current"]["direction"] = "FALLING"
        suppress_path = root / "suppress_state.json"
        suppress_path.write_text(json.dumps(suppress_state), encoding="utf-8")
        suppress_out = root / "suppress_out"
        suppress_proc = subprocess.run(
            [
                sys.executable, str(tool),
                "--state", str(suppress_path),
                "--policy", str(policy),
                "--input-dir", str(input_dir),
                "--output-dir", str(suppress_out),
                "--suppress-selected-source-direction", "H1:FALLING",
            ],
            capture_output=True, text=True,
        )
        assert suppress_proc.returncode == 0, suppress_proc.stderr + suppress_proc.stdout
        suppress_audit = json.loads(
            (suppress_out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json").read_text(encoding="utf-8")
        )
        assert suppress_audit["source_selection"]["H1"] == []
        assert suppress_audit["suppressed_source_selections"][0]["source_tf"] == "H1"
        assert suppress_audit["suppressed_source_selections"][0]["direction"] == "FALLING"
        assert "H1" not in suppress_audit["hl_candidates"]
        assert suppress_audit["source_presence_problems"] == []
        assert not any(x["source_tf"] == "H1" for x in suppress_audit["selected_families"])
        assert suppress_audit["selection_policy"]["suppressed_source_semantics"] == "REMOVE_SOURCE_AND_ALL_PLAN_B_COPIES_NO_REPLACEMENT"

    print("NVT9 TF DISPLAY MAP SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
