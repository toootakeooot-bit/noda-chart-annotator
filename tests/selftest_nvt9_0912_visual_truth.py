from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "tools" / "nvt" / "verify_nvt9_0912_visual_truth.py"
TRUTH = ROOT / "nvt" / "manifests" / "NVT9_0912_VISUAL_TRUTH_V01.json"

HEADER = [
    "object_id","symbol","timeframe","structure_level","role",
    "t1","p1","t2","p2","generation_role","generation","status","extent",
]


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        overlay_audit = root / "overlay.json"
        overlay_csv = root / "overlay.csv"
        base_audit = root / "base.json"
        base_csv = root / "base.csv"

        overlay_audit.write_text(json.dumps({
            "d1_visual_truth": {
                "status": "BUILT",
                "anchor1": {"kind": "LOW", "time": "2026-02-05T00:00:00", "price": 150.0},
                "anchor2": {"kind": "LOW", "time": "2026-04-28T00:00:00", "price": 154.0},
                "tl_break_time": "2026-08-01T00:00:00",
                "lifecycle_status": "REFERENCE_RETAINED_BROKEN",
                "resolved_truth": {
                    "anchor_selection": "PAIRWISE_OUTERMOST_WICK_ENVELOPE",
                    "formation_wick_breach_count": 0,
                    "formation_wick_contact_count": 4,
                    "formation_mean_wick_gap": 0.25
                },
            }
        }), encoding="utf-8")
        base_audit.write_text(json.dumps({
            "suppressed_source_selections": [
                {"source_tf": "H1", "direction": "FALLING"},
                {"source_tf": "D1", "direction": "RISING"},
            ]
        }), encoding="utf-8")

        write_csv(overlay_csv, [
            ["X0912-D1-APPROVED-01-TL","USDJPY#","D1","D1_USER_APPROVED_REFERENCE","APPROVED_TL",
             "2026.02.05 00:00:00","150","2026.09.11 00:00:00","160","EXPERIMENTAL","1","REFERENCE_RETAINED_BROKEN","RAY_RIGHT"],
            ["X0912-D1-APPROVED-01-CH","USDJPY#","D1","D1_USER_APPROVED_REFERENCE","APPROVED_CH",
             "2026.02.05 00:00:00","155","2026.09.11 00:00:00","165","EXPERIMENTAL","1","REFERENCE_RETAINED_BROKEN","RAY_RIGHT"],
            ["X0912-D1-APPROVED-01-HL","USDJPY#","D1","D1_USER_APPROVED_REFERENCE","APPROVED_HL",
             "2026.03.20 00:00:00","160","2026.09.11 00:00:00","160","EXPERIMENTAL","1","REFERENCE_RETAINED_BROKEN","RAY_RIGHT"],
        ])
        write_csv(base_csv, [
            ["B1","USDJPY#","M15","MID_DOW","TL",
             "2026.09.08 00:00:00","153","2026.09.11 23:45:00","154","SOURCE","1","CURRENT","RAY_RIGHT"],
        ])

        proc = subprocess.run([
            sys.executable, str(VERIFY),
            "--visual-truth", str(TRUTH),
            "--overlay-audit", str(overlay_audit),
            "--overlay-csv", str(overlay_csv),
            "--base-audit", str(base_audit),
            "--base-csv", str(base_csv),
        ], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        report = json.loads((root / "NVT9_0912_VISUAL_TRUTH_VERIFY.json").read_text(encoding="utf-8"))
        assert report["status"] == "PASS_0912_VISUAL_TRUTH"
        assert report["lifecycle_status"] == "REFERENCE_RETAINED_BROKEN"
        assert report["d1_anchor_selection"] == "PAIRWISE_OUTERMOST_WICK_ENVELOPE"
        assert report["formation_wick_breach_count"] == 0

        # Deliberately move A1 outside the approved yellow-circle window:
        # verifier must fail rather than announce READY.
        bad = json.loads(overlay_audit.read_text(encoding="utf-8"))
        bad["d1_visual_truth"]["anchor1"]["time"] = "2025-04-04T00:00:00"
        overlay_audit.write_text(json.dumps(bad), encoding="utf-8")
        bad_proc = subprocess.run([
            sys.executable, str(VERIFY),
            "--visual-truth", str(TRUTH),
            "--overlay-audit", str(overlay_audit),
            "--overlay-csv", str(overlay_csv),
            "--base-audit", str(base_audit),
            "--base-csv", str(base_csv),
        ], capture_output=True, text=True)
        assert bad_proc.returncode != 0
        assert "outside approved yellow-circle window" in (bad_proc.stdout + bad_proc.stderr)

        # Restore A1 and deliberately report a wick breach: verifier must fail.
        wick_bad = json.loads(overlay_audit.read_text(encoding="utf-8"))
        wick_bad["d1_visual_truth"]["anchor1"]["time"] = "2026-02-05T00:00:00"
        wick_bad["d1_visual_truth"]["resolved_truth"]["formation_wick_breach_count"] = 1
        overlay_audit.write_text(json.dumps(wick_bad), encoding="utf-8")
        wick_proc = subprocess.run([
            sys.executable, str(VERIFY),
            "--visual-truth", str(TRUTH),
            "--overlay-audit", str(overlay_audit),
            "--overlay-csv", str(overlay_csv),
            "--base-audit", str(base_audit),
            "--base-csv", str(base_csv),
        ], capture_output=True, text=True)
        assert wick_proc.returncode != 0
        assert "formation wick breach" in (wick_proc.stdout + wick_proc.stderr)

    print("NVT9_0912_VISUAL_TRUTH_SELFTEST_PASS")


if __name__ == "__main__":
    main()
