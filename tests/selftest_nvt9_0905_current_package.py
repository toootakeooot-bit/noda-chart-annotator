from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "nvt" / "build_nvt9_reference_0905.py"
VERIFY = ROOT / "tools" / "nvt" / "verify_nvt9_0905_previsual.py"
TRUTH = ROOT / "nvt" / "manifests" / "NVT9_0905_VISUAL_TRUTH_V01.json"
VIEWER = ROOT / "mt4" / "NCA_NVT9_AB_View.mq4"
RUN = ROOT / "setup" / "run_nvt9_reference_0905.ps1"
CMD = ROOT / "setup" / "PREPARE_NVT9_REFERENCE_0905.cmd"


def main() -> None:
    b = BUILDER.read_text(encoding="utf-8")
    assert 'default="2026-09-05T00:00:00"' in b
    assert 'eligible[-600:]' in b
    assert '"future_bars_used": False' in b
    assert '"--fallback-previous-source-tf", "H4"' in b
    assert '"--fallback-reference-source-tf", "H4"' in b
    assert '"--allow-empty-source-tf", "H4"' in b
    assert '"--main-roles-only-source-tf", "H4"' in b
    assert '"--main-roles-only-source-tf", "M15"' in b
    assert '--suppress-selected-source-direction' not in b
    assert '"suppressed_source_directions": {}' in b
    assert '"NO_0905_DATE_SPECIFIC_SUPPRESSION_BEFORE_VISUAL_ADJUDICATION"' in b

    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    assert truth["case_date"] == "2026-09-05"
    assert truth["status"] == "PROVISIONAL_CARRY_FORWARD_RULES_PENDING_0905_VISUAL_AUDIT"
    assert truth["approved_families"][0]["truth_id"] == "VT0905-D1-001"
    assert truth["approved_families"][0]["geometry_policy"]["rule"] == "OUTERMOST_RISING_SUPPORT_NO_FORMATION_WICK_BREACH"
    assert truth["render_contract"]["selection_cutoff_exclusive"] == "2026-09-05T00:00:00"
    assert truth["render_contract"]["future_bars_used_for_selection"] is False
    assert truth["render_contract"]["extend_selected_reference_geometry_beyond_cutoff"] is True

    v = VIEWER.read_text(encoding="utf-8")
    assert 'CASE_20260905 = 0' in v
    assert 'HistoryCase = CASE_20260905' in v
    assert r'nvt9_reference_0905\\base\\NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv' in v
    assert r'nvt9_reference_0905\\NVT9_0919_STRUCTURAL_OVERLAY.csv' in v
    assert 'StringToTime("2026.09.05 00:00")' in v
    assert 'IsDedicatedReferenceCase()' in v

    verify = VERIFY.read_text(encoding="utf-8")
    assert "PASS_0905_PREVISUAL_NO_LOOKAHEAD" in verify
    assert "PENDING_USER_0905_SCREENSHOT" in verify
    assert "09/05 D1 approved TL has formation wick breach" in verify
    assert "09/05 H4 frozen reference was not revalidated" in verify

    run = RUN.read_text(encoding="utf-8")
    assert "2026-09-05T00:00:00" in run
    assert "build_nvt9_reference_0905.py" in run
    assert "--case-tag '0905'" in run
    assert "verify_nvt9_0905_previsual.py" in run
    assert "READY - 09/05 FIRST VISUAL AUDIT" in run

    assert "run_nvt9_reference_0905.ps1" in CMD.read_text(encoding="utf-8")

    print("NVT9_0905_CURRENT_PACKAGE_SELFTEST_PASS")


if __name__ == "__main__":
    main()
