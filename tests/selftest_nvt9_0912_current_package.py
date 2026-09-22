from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "nvt" / "build_nvt9_reference_0912.py"
OVERLAY = ROOT / "tools" / "nvt" / "build_nvt9_structural_overlay_0919.py"
VIEWER = ROOT / "mt4" / "NCA_NVT9_AB_View.mq4"
FREEZE = ROOT / "nvt" / "manifests" / "NVT9_0919_VISUAL_AUDIT_FREEZE_V01.json"
TRUTH = ROOT / "nvt" / "manifests" / "NVT9_0912_VISUAL_TRUTH_V01.json"
VERIFY = ROOT / "tools" / "nvt" / "verify_nvt9_0912_visual_truth.py"


def main() -> None:
    b = BUILDER.read_text(encoding="utf-8")
    assert 'default="2026-09-12T00:00:00"' in b
    assert 'eligible[-600:]' in b
    assert '"window_policy": "LAST_600_CLOSED_BARS_PER_TIMEFRAME"' in b
    assert '"future_bars_used": False' in b
    assert '"--fallback-previous-source-tf", "H4"' in b
    assert '"--main-roles-only-source-tf", "H4"' in b
    assert '"--main-roles-only-source-tf", "M15"' in b
    assert '"--allow-empty-source-tf", "H4"' not in b
    assert '"--suppress-selected-source-direction", "H1:FALLING"' in b
    assert '"--suppress-selected-source-direction", "D1:RISING"' in b
    assert '"empty_source_policy": "FAIL_IF_CURRENT_AND_RETAINED_PREVIOUS_ARE_BOTH_MISSING"' in b
    assert '"retained_reference_policy": "H4_CURRENT_ABSENT_THEN_PREVIOUS_REFERENCE_RETAINED"' in b
    assert '"source_suppression_policy": "REMOVE_SOURCE_AND_ALL_PLAN_B_COPIES_NO_REPLACEMENT"' in b

    o = OVERLAY.read_text(encoding="utf-8")
    assert 'ap.add_argument("--cutoff"' in o
    assert 'ap.add_argument("--case-tag"' in o
    assert 'f"X{case_tag}-H1-CONT-01-TL"' in o
    assert 'f"X{case_tag}-D1-CONT-01-TL"' in o
    assert 'f"X{case_tag}-D1-MAJOR-01-TL"' in o
    assert 'f"X{case_tag}-D1-MAJOR-01-HL"' in o
    assert 'f"X{case_tag}-D1-APPROVED-01-TL"' in o
    assert 'D1_USER_APPROVED_YELLOW_CIRCLE_LOW_PAIR' in o
    assert 'ap.add_argument("--visual-truth")' in o

    v = VIEWER.read_text(encoding="utf-8")
    assert 'HistoryCase = CASE_20260912' in v
    assert r'nvt9_reference_0912\\base\\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv' in v
    assert r'nvt9_reference_0912\\NVT9_0919_STRUCTURAL_OVERLAY.csv' in v
    assert 'ShowCurrentStructuralOverlayOn0912Old = true' in v
    assert 'StringFind(n, XPREFIX, 0) == 0' in v
    assert '09/12 NO-LINE accepted' in v
    assert '[D1 MAJOR TL]' in v
    assert '[D1 MAJOR HL]' in v
    assert '[D1 APPROVED TL]' in v
    assert '[D1 APPROVED HL]' in v
    assert 'input bool AuditDeleteAllChartObjects = false;' in v
    assert 'DeleteHistoricalSystemObjects' in v
    assert 'else if(isolate0912) DeleteHistoricalSystemObjects(chartId);' in v
    assert 'drawT2 = cutoff' not in v
    assert 'PREVIOUS' in v
    assert 'SOURCE_TF_RETAINED_PREVIOUS_FALLBACK' not in v
    assert 'approvedReference' in v
    assert 'OBJPROP_RAY_RIGHT,approvedReference' in v

    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    assert truth["status"] == "ACTIVE_USER_ANNOTATED_TRUTH"
    assert truth["approved_families"][0]["truth_id"] == "VT0912-D1-001"
    assert truth["approved_families"][0]["geometry_policy"]["rule"] == "OUTERMOST_RISING_SUPPORT_NO_FORMATION_WICK_BREACH"
    assert truth["approved_families"][0]["anchor1"]["selection"] == "PAIRWISE_OUTERMOST_WICK_ENVELOPE"
    assert truth["render_contract"]["future_bars_used_for_selection"] is False
    assert truth["render_contract"]["extend_selected_reference_geometry_beyond_cutoff"] is True
    assert truth["render_contract"]["projection_mode"] == "RAY_RIGHT_FROM_PRE_CUTOFF_ANCHORS"
    verify_text = VERIFY.read_text(encoding="utf-8")
    assert "PASS_0912_VISUAL_TRUTH" in verify_text
    assert "formation_wick_breach_count" in verify_text
    assert "PAIRWISE_OUTERMOST_WICK_ENVELOPE" in verify_text
    assert "D1 anchor1 outside approved yellow-circle window" in verify_text
    assert "H4 retained reference missing" in verify_text
    assert "M15 historical family must keep main TL/CH only" in verify_text

    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "FROZEN_VISUAL_AUDIT_COMPLETE"
    assert freeze["scope"]["production_promotion"] is False
    assert freeze["continuation_policy"]["downstream_cases_must_not_silently_redefine_0919"] is True

    print("NVT9_0912_CURRENT_PACKAGE_SELFTEST_PASS")


if __name__ == "__main__":
    main()
