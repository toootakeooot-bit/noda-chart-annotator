from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tool = repo / "tools" / "nvt" / "prepare_nvt9_v7_preview_ready.py"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        v6 = {
            "status": "PASS_V6_PREVIEW",
            "preview_snapshot": "preview.csv",
            "counts_after": {"D1": 16, "H4": 16, "H1": 14, "M15": 16},
            "suppressed_counts": {"H1": 2},
            "source_snapshot_modified": False,
            "production_renderer_modified": False,
            "nca_draw_writeback": False,
        }
        v5 = {"status": "PASS_V5"}
        v6p = root / "v6.json"
        v5p = root / "v5.json"
        out = root / "ready.json"
        v6p.write_text(json.dumps(v6), encoding="utf-8")
        v5p.write_text(json.dumps(v5), encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(tool), "--v6-audit", str(v6p),
             "--v5-regression", str(v5p), "--output", str(out)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["status"] == "READY_FOR_V7_MT4_PREVIEW"
        assert payload["renderer_prefix"] == "NVT9_PREVIEW__"
        assert payload["production_prefix"] == "NCA_DRAW__"
        assert payload["expected_renderer_rows"]["H1"] == 14
        assert payload["trade_authority"] is False

        v5p.write_text(json.dumps({"status": "FAIL_V5"}), encoding="utf-8")
        blocked = root / "blocked.json"
        proc = subprocess.run(
            [sys.executable, str(tool), "--v6-audit", str(v6p),
             "--v5-regression", str(v5p), "--output", str(blocked)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 7
        payload = json.loads(blocked.read_text(encoding="utf-8"))
        assert payload["status"] == "BLOCKED_V7"

    print("NVT9 V7 PREVIEW READY SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
