from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_deep_lifecycle", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    mod = load_module(repo / "tools" / "nvt" / "build_nvt9_deep_lifecycle_state.py")

    a = {
        "direction": "RISING",
        "anchor1_time": "2025-01-01T00:00:00",
        "anchor1_price": 100.0,
        "anchor2_time": "2026-01-01T00:00:00",
        "anchor2_price": 110.0,
        "ch_offset": 3.0,
        "zone_width": 0.1,
    }
    b = dict(a)
    same, diffs = mod.same_geom(a, b)
    assert same and not diffs
    b["anchor1_price"] = 100.5
    same, diffs = mod.same_geom(a, b)
    assert not same and "anchor1_price" in diffs

    state = {
        "schema": "nca-live-state/1.0",
        "slots": {
            "USDJPY#|H1|LARGE_DOW": {
                "current": {"line_id": "C"},
                "previous": {"line_id": "P"},
                "history": [],
            }
        },
    }
    ann = mod.annotate_roles(state)
    slot = ann["slots"]["USDJPY#|H1|LARGE_DOW"]
    assert slot["current"]["generation_role"] == "CURRENT"
    assert slot["previous"]["generation_role"] == "PREVIOUS"

    print("NVT9 DEEP LIFECYCLE STATE SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
