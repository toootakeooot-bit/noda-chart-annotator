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


def row(line_id: str, level: str, gen_role: str, gen: str, role: str) -> dict:
    return {
        "object_id": f"{line_id}__{role}",
        "symbol": "USDJPY#",
        "timeframe": "H1",
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


def write_preview(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    validator = repo / "tools" / "nvt" / "validate_nvt9_visibility_invariants.py"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pass_preview = root / "pass.csv"
        pass_rows = [
            row("LARGE_CURRENT", "LARGE_DOW", "CURRENT", "12", "TL"),
            row("LARGE_CURRENT", "LARGE_DOW", "CURRENT", "12", "CH"),
            row("LARGE_CURRENT", "LARGE_DOW", "CURRENT", "12", "TL_ZONE_EDGE"),
            row("LARGE_CURRENT", "LARGE_DOW", "CURRENT", "12", "CH_ZONE_EDGE"),
            row("LARGE_PREV", "LARGE_DOW", "PREVIOUS", "11", "TL"),
            row("LARGE_PREV", "LARGE_DOW", "PREVIOUS", "11", "CH"),
            row("MID_CURRENT", "MID_DOW", "CURRENT", "7", "TL"),
            row("MID_CURRENT", "MID_DOW", "CURRENT", "7", "CH"),
        ]
        write_preview(pass_preview, pass_rows)
        pass_json = root / "pass.json"
        proc = subprocess.run(
            [sys.executable, str(validator), "--preview", str(pass_preview), "--output", str(pass_json)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        payload = json.loads(pass_json.read_text(encoding="utf-8"))
        assert payload["status"] == "PASS_V5"
        assert not payload["failed_checks"]

        fail_preview = root / "fail.csv"
        fail_rows = [r for r in pass_rows if r["object_id"] != "LARGE_CURRENT__CH"]
        write_preview(fail_preview, fail_rows)
        fail_json = root / "fail.json"
        proc = subprocess.run(
            [sys.executable, str(validator), "--preview", str(fail_preview), "--output", str(fail_json)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 5
        payload = json.loads(fail_json.read_text(encoding="utf-8"))
        assert payload["status"] == "FAIL_V5"
        assert "large_current_ch_drawable" in payload["failed_checks"]

    print("NVT9 VISIBILITY INVARIANT SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
