from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_full_history", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    mod = load_module(repo / "tools" / "nvt" / "audit_nvt9_normal_vs_full_history.py")

    a = {
        "direction": "RISING",
        "anchor1_time": "2026-01-01T00:00:00",
        "anchor1_price": 100.0,
        "anchor2_time": "2026-01-02T00:00:00",
        "anchor2_price": 101.0,
        "ch_offset": 2.0,
        "zone_width": 0.1,
    }
    b = dict(a)
    same, diffs = mod.compare_geometry(a, b)
    assert same is True
    assert diffs == []

    b["direction"] = "FALLING"
    b["anchor2_time"] = "2026-01-03T00:00:00"
    same, diffs = mod.compare_geometry(a, b)
    assert same is False
    assert "direction" in diffs
    assert "anchor2_time" in diffs

    same, diffs = mod.compare_geometry(None, None)
    assert same is True and diffs == []

    same, diffs = mod.compare_geometry(a, None)
    assert same is False and diffs == ["presence"]

    print("NVT9 NORMAL VS FULL-HISTORY AUDIT SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
