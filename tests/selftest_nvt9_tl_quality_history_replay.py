from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_history_replay", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    mod = load_module(repo / "tools" / "nvt" / "build_nvt9_tl_quality_history_replay.py")

    probe = {
        "cases": [
            {
                "case_id": "GT_0004",
                "mode": "TL_WINDOW_PROBE",
                "status": "PRESENT_WITHIN_WINDOWS",
                "timeframe": "D1",
                "eligible_candidate_count": 5688,
                "window_match_count": 1,
                "matches": [
                    {
                        "candidate_id": "RISING:2025-04-04T00:00:00:2025-09-09T00:00:00",
                        "direction": "RISING",
                        "anchor1": {
                            "kind": "LOW",
                            "time": "2025-04-04T00:00:00",
                            "price": 144.544,
                            "retracement": 0.38
                        },
                        "anchor2": {
                            "kind": "LOW",
                            "time": "2025-09-09T00:00:00",
                            "price": 146.302,
                            "retracement": 0.38
                        },
                        "turn_span": 10,
                        "tl_contacts": 2,
                        "unbroken_close": True
                    }
                ]
            },
            {
                "case_id": "GT_0005",
                "mode": "NO_LINE",
                "status": "NO_LINE_CONFIRMED_BY_TEACHER_EVIDENCE"
            },
            {
                "case_id": "GT_0006",
                "mode": "TL_WINDOW_PROBE",
                "status": "ABSENT_WITHIN_WINDOWS",
                "timeframe": "H1",
                "eligible_candidate_count": 685,
                "window_match_count": 0,
                "nearest_when_window_not_exact": [
                    {
                        "candidate_id": "FALLING:2026-07-31T16:00:00:2026-09-02T04:00:00",
                        "direction": "FALLING",
                        "anchor1": {
                            "kind": "HIGH",
                            "time": "2026-07-31T16:00:00",
                            "price": 160.533,
                            "retracement": 0.38
                        },
                        "anchor2": {
                            "kind": "HIGH",
                            "time": "2026-09-02T04:00:00",
                            "price": 160.387,
                            "retracement": 0.38
                        },
                        "turn_span": 13,
                        "tl_contacts": 2,
                        "unbroken_close": True
                    }
                ]
            }
        ]
    }

    cross = {
        "schema": "nvt9-cross-tf-review/0.2",
        "status": "PASS",
        "current_line_sets": {
            "D1": [
                {
                    "line_id": "D1_A",
                    "timeframe": "D1",
                    "structure_level": "LARGE_DOW",
                    "status": "ACTIVE",
                    "direction": "RISING",
                    "anchor1_time": "2025-01-01T00:00:00",
                    "anchor1_price": 140.0,
                    "anchor2_time": "2026-01-01T00:00:00",
                    "anchor2_price": 150.0,
                    "ch_offset": 2.0,
                    "zone_width": 0.2
                }
            ],
            "H4": [
                {
                    "line_id": "H4_A",
                    "timeframe": "H4",
                    "structure_level": "MID_DOW",
                    "status": "ACTIVE",
                    "direction": "FALLING",
                    "anchor1_time": "2026-07-01T00:00:00",
                    "anchor1_price": 160.0,
                    "anchor2_time": "2026-09-01T00:00:00",
                    "anchor2_price": 158.0,
                    "ch_offset": -2.0,
                    "zone_width": 0.1
                }
            ]
        },
        "0919_user_observation_hypotheses": [
            {"source_tf": "H4", "teacher_owner_candidate": "D1"}
        ]
    }

    strict = {
        "status": "PASS_STRICT_NVT8",
        "strict_nvt8_satisfied": True,
        "wrapper": {
            "final_state_rows": [
                {"line_id": "STRICT_OTHER", "structure_level": "LARGE_DOW"}
            ]
        }
    }

    user_0905 = json.loads(
        (repo / "nvt" / "adjudication" / "NVT9_USER_0905_TRANSITION_V01.json").read_text(encoding="utf-8")
    )

    result = mod.build_replay(
        gt_dir=repo / "nvt" / "ground_truth",
        teacher_anchor_probe=probe,
        cross_tf_0919=cross,
        strict_heldout_0919=strict,
        user_0905=user_0905,
    )

    assert result["status"] == "PARTIAL_REAL_HISTORY_REPLAY_COMPLETE"
    assert len(result["teacher_cases"]) == 4

    by_case = {x["case_id"]: x for x in result["teacher_cases"]}
    assert by_case["GT_0004"]["patterns"] == ["P16"]
    assert by_case["GT_0005"]["patterns"] == ["P17"]
    assert by_case["GT_0005"]["probe_conflict"]["status"] == "SUPERSEDED"
    assert by_case["GT_0006"]["patterns"] == ["P18", "P19"]
    assert by_case["GT_0007"]["patterns"] == ["P20"]

    candidate_by_case = {x["case_id"]: x for x in result["candidate_replays"]}
    assert candidate_by_case["GT_0004"]["audited_candidate_count"] == 1
    assert candidate_by_case["GT_0004"]["audits"][0]["Quality"] == "HOLD"
    assert candidate_by_case["GT_0006"]["audited_candidate_count"] == 1
    gt6 = candidate_by_case["GT_0006"]["audits"][0]
    assert gt6["Quality"] == "HOLD"
    assert any(r["pattern_id"] == "P19" for r in gt6["reasons"])

    r19 = result["replay_0919_current_lines"]
    assert r19["line_count"] == 2
    assert r19["strict_heldout_context"]["line_id_join_count"] == 0
    by_line = {x["TL_ID"]: x for x in r19["audits"]}
    assert by_line["D1_A"]["Quality"] == "HOLD"
    assert by_line["D1_A"]["AuditReadiness"] in {"PARTIAL", "INSUFFICIENT"}
    assert by_line["H4_A"]["Quality"] == "HOLD"
    assert by_line["H4_A"]["checks"]["Cross-TF"] == "HOLD"
    assert "P09" in by_line["H4_A"]["matched_patterns"] or any(
        r["pattern_id"] == "P09" for r in by_line["H4_A"]["reasons"]
    )

    assert result["user_adjudication_0905_transition"]["pattern_id"] == "P04"
    assert result["user_adjudication_0905_transition"]["exact_anchor_geometry_locked"] is False
    assert result["superseded_or_conflicting_history"]
    assert result["unresolved_evidence_gaps"]

    # A separately verified exact transition replay may satisfy the 09/05
    # geometry lock without mutating the original semantic adjudication file.
    transition_lock = {
        "schema": "nvt9-0905-transition-exact-replay/1.0",
        "case_date": "2026-09-05",
        "cutoff_exclusive": "2026-09-05T00:00:00",
        "status": "PASS_0905_TRANSITION_EXACT_REPLAY",
        "transition_exact_geometry_locked": True,
        "teacher_ground_truth_exact_anchors_locked": False,
        "lock": {
            "transition_exact_geometry_locked": True,
            "failed_checks": [],
        },
    }
    locked = mod.build_replay(
        gt_dir=repo / "nvt" / "ground_truth",
        teacher_anchor_probe=probe,
        cross_tf_0919=None,
        strict_heldout_0919=None,
        user_0905=user_0905,
        transition_lock_0905=transition_lock,
    )
    locked_transition = locked["user_adjudication_0905_transition"]
    assert locked_transition["exact_anchor_geometry_locked"] is True
    assert locked_transition["source_adjudication_exact_anchor_geometry_locked"] is False
    assert locked_transition["transition_exact_replay_lock_applied"] is True
    assert locked_transition["transition_exact_replay_status"] == "PASS_0905_TRANSITION_EXACT_REPLAY"
    assert locked["unresolved_evidence_gaps"] == []

    # A malformed or blocked artifact must not unlock the replay.
    bad_lock = dict(transition_lock)
    bad_lock["status"] = "BLOCKED_0905_TRANSITION_EXACT_REPLAY"
    bad_lock["transition_exact_geometry_locked"] = False
    blocked_lock = mod.build_replay(
        gt_dir=repo / "nvt" / "ground_truth",
        teacher_anchor_probe=probe,
        cross_tf_0919=None,
        strict_heldout_0919=None,
        user_0905=user_0905,
        transition_lock_0905=bad_lock,
    )
    assert blocked_lock["user_adjudication_0905_transition"]["exact_anchor_geometry_locked"] is False
    assert blocked_lock["user_adjudication_0905_transition"]["transition_exact_replay_lock_applied"] is False
    assert blocked_lock["unresolved_evidence_gaps"]

    again = mod.build_replay(
        gt_dir=repo / "nvt" / "ground_truth",
        teacher_anchor_probe=probe,
        cross_tf_0919=cross,
        strict_heldout_0919=strict,
        user_0905=user_0905,
    )
    assert result == again

    print("NVT9 TL QUALITY HISTORY REPLAY SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
