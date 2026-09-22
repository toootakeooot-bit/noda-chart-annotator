from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "nvt" / "build_nvt9_reference_0912.py"
OVERLAY = ROOT / "tools" / "nvt" / "build_nvt9_structural_overlay_0919.py"
VIEWER = ROOT / "mt4" / "NCA_NVT9_AB_View.mq4"
FREEZE = ROOT / "nvt" / "manifests" / "NVT9_0919_VISUAL_AUDIT_FREEZE_V01.json"


def main() -> None:
    b = BUILDER.read_text(encoding="utf-8")
    assert 'default="2026-09-12T00:00:00"' in b
    assert 'eligible[-600:]' in b
    assert '"window_policy": "LAST_600_CLOSED_BARS_PER_TIMEFRAME"' in b
    assert '"future_bars_used": False' in b

    o = OVERLAY.read_text(encoding="utf-8")
    assert 'ap.add_argument("--cutoff"' in o
    assert 'ap.add_argument("--case-tag"' in o
    assert 'f"X{case_tag}-H1-CONT-01-TL"' in o
    assert 'f"X{case_tag}-D1-CONT-01-TL"' in o

    v = VIEWER.read_text(encoding="utf-8")
    assert 'HistoryCase = CASE_20260912' in v
    assert r'nvt9_reference_0912\\\\base\\\\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv' in v
    assert r'nvt9_reference_0912\\\\NVT9_0919_STRUCTURAL_OVERLAY.csv' in v
    assert 'ShowCurrentStructuralOverlayOn0912Old = true' in v
    assert 'StringFind(n, XPREFIX, 0) == 0' in v

    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "FROZEN_VISUAL_AUDIT_COMPLETE"
    assert freeze["scope"]["production_promotion"] is False
    assert freeze["continuation_policy"]["downstream_cases_must_not_silently_redefine_0919"] is True

    print("NVT9_0912_CURRENT_PACKAGE_SELFTEST_PASS")


if __name__ == "__main__":
    main()
