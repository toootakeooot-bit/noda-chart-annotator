from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tool = repo / "tools" / "nvt" / "validate_nvt9_plan_b_contract.py"
    contract = repo / "nvt" / "manifests" / "NVT9_PLAN_B_DISPLAY_CONTRACT_20260920.json"
    policy = repo / "nvt" / "manifests" / "NVT9_TF_DISPLAY_MAP_0919_V01.json"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        out = root / "pass.json"
        p = subprocess.run(
            [sys.executable, str(tool), "--contract", str(contract), "--policy", str(policy), "--output", str(out)],
            capture_output=True, text=True,
        )
        assert p.returncode == 0, p.stderr + p.stdout
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["status"] == "PASS_PLAN_B_CONTRACT"

        bad_policy = json.loads(policy.read_text(encoding="utf-8"))
        bad_policy["display_sources"] = {
            "D1": ["D1"],
            "H4": ["D1", "H4"],
            "H1": ["H4", "H1"],
            "M15": ["H1", "M15"]
        }
        bad = root / "bad.json"
        bad.write_text(json.dumps(bad_policy), encoding="utf-8")
        bad_out = root / "bad_out.json"
        p = subprocess.run(
            [sys.executable, str(tool), "--contract", str(contract), "--policy", str(bad), "--output", str(bad_out)],
            capture_output=True, text=True,
        )
        assert p.returncode == 9
        payload = json.loads(bad_out.read_text(encoding="utf-8"))
        assert payload["status"] == "FAIL_PLAN_B_CONTRACT"

    print("NVT9 PLAN B CONTRACT SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
