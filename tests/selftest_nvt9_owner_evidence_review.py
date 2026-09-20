from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_owner_evidence", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    mod = load_module(repo / "tools" / "nvt" / "build_nvt9_owner_evidence_review.py")

    assert mod.same_parent_bar("H4", "2026-09-08T04:00:00", "2026-09-08T05:00:00")
    assert not mod.same_parent_bar("H4", "2026-09-08T04:00:00", "2026-09-08T08:00:00")
    assert mod.same_parent_bar("D1", "2026-09-08T00:00:00", "2026-09-08T04:00:00")
    assert not mod.same_parent_bar("H1", "2026-09-02T04:00:00", "2026-09-02T16:15:00")

    row = {
        "direction_match": True,
        "anchor2_price_diff": 0.0,
        "parent_tf": "H4",
        "_parent_anchor1_time": "2025-05-22T08:00:00",
        "_parent_anchor2_time": "2026-09-08T04:00:00",
        "_child_anchor1_time": "2025-10-01T00:00:00",
        "_child_anchor2_time": "2026-09-08T05:00:00",
        "child_span_over_parent_span": 0.72,
        "parent_generation_role": "CURRENT",
    }
    assert mod.evidence_class(row) == "SHARED_TERMINAL_PIVOT_NESTED_SCALE"

    retained = dict(row)
    retained["anchor2_price_diff"] = 0.7
    retained["_child_anchor2_time"] = "2026-09-02T16:15:00"
    retained["_parent_anchor2_time"] = "2026-09-02T04:00:00"
    retained["parent_generation_role"] = "PREVIOUS"
    assert mod.evidence_class(retained) == "SAME_DIRECTION_RETAINED_PARENT_REFERENCE"

    opposite = dict(row)
    opposite["direction_match"] = False
    assert mod.evidence_class(opposite) == "OPPOSITE_DIRECTION"

    print("NVT9 OWNER EVIDENCE REVIEW SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
