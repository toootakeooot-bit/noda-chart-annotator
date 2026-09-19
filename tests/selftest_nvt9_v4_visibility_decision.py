from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tool = repo / "tools" / "nvt" / "build_nvt9_v4_visibility_decision.py"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        adjudication = {
            "records": [
                {
                    "source_tf": "H1",
                    "line_id": "H1_A",
                    "classification": "PARENT_OWNED_SAME_FAMILY",
                    "structural_owner_tf": "H4",
                    "same_family_parent_id": "H4_A",
                },
                {
                    "source_tf": "M15",
                    "line_id": "M15_A",
                    "classification": "LOCAL_OWNED_DISTINCT",
                    "structural_owner_tf": "M15",
                    "same_family_parent_id": None,
                },
            ]
        }
        adjudication_path = root / "adj.json"
        adjudication_path.write_text(json.dumps(adjudication), encoding="utf-8")

        blocked_gate = root / "blocked_gate.json"
        blocked_gate.write_text(json.dumps({
            "status": "BLOCKED_V3_5",
            "unresolved": [{"source_tf": "H1", "line_id": "H1_A"}],
        }), encoding="utf-8")
        blocked_out = root / "blocked_out.json"
        proc = subprocess.run(
            [sys.executable, str(tool), "--gate", str(blocked_gate),
             "--adjudication", str(adjudication_path), "--output", str(blocked_out)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        payload = json.loads(blocked_out.read_text(encoding="utf-8"))
        assert payload["status"] == "BLOCKED_PENDING_V3_5"
        assert payload["v4_policy_selected"] is False

        pass_gate = root / "pass_gate.json"
        pass_gate.write_text(json.dumps({"status": "PASS_V3_5", "unresolved": []}), encoding="utf-8")
        pass_out = root / "pass_out.json"
        proc = subprocess.run(
            [sys.executable, str(tool), "--gate", str(pass_gate),
             "--adjudication", str(adjudication_path), "--output", str(pass_out)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        payload = json.loads(pass_out.read_text(encoding="utf-8"))
        assert payload["status"] == "READY_FOR_VISUAL_POLICY_SELECTION"
        assert payload["parent_owned_count"] == 1
        assert payload["local_owned_count"] == 1
        assert payload["legacy_h1_16_to_12_candidate"]["status"] == "SECONDARY_ONLY_PARENT_DUPLICATION_PRESENT"
        assert payload["v4_policy_selected"] is False

    print("NVT9 V4 VISIBILITY DECISION SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
