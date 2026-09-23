from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_stage1_gate", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def good_line(tf: str, line_id: str, classification: str = "LOCAL_OWNED_DISTINCT") -> dict:
    owner_tf = tf
    if classification == "PARENT_OWNED_SAME_FAMILY":
        owner_tf = "D1" if tf == "H4" else "H4" if tf == "H1" else "H1"
    return {
        "line_id": line_id,
        "timeframe": tf,
        "generation_role": "CURRENT",
        "structure_level": "MID_DOW",
        "match_status": "EXACT_UNIQUE",
        "ownership_evidence": {
            "classification": classification,
            "owner_tf": owner_tf,
            "owner_confirmed": True,
            "ownership_ambiguous": False,
            "parent_family_unresolved": False,
        },
        "quality_audit": {
            "Quality": "GOOD",
            "AuditReadiness": "READY",
            "OwnershipReadiness": "PASS",
            "reasons": [],
        },
    }


def good_history() -> dict:
    return {
        "schema": "nvt9-tl-quality-history-replay/1.0",
        "status": "PARTIAL_REAL_HISTORY_REPLAY_COMPLETE",
        "teacher_cases": [
            {"case_id": "GT_0004"},
            {"case_id": "GT_0005"},
            {"case_id": "GT_0006"},
            {"case_id": "GT_0007"},
        ],
        "user_adjudication_0905_transition": {
            "case_id": "USER_0905_TRANSITION",
            "exact_anchor_geometry_locked": True,
        },
        "unresolved_evidence_gaps": [],
        "superseded_or_conflicting_history": [
            {"status": "SUPERSEDED", "older_interpretation": "NO_LINE"}
        ],
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    mod = load_module(repo / "tools" / "nvt" / "evaluate_nvt9_tl_quality_stage1_gate.py")

    joined = {
        "schema": "nvt9-tl-quality-ownership-join/1.0",
        "status": "PASS_OWNERSHIP_JOIN",
        "timeframes": {
            "D1": {"lines": [good_line("D1", "D1_A", "ROOT_LOCAL_OWNED")]},
            "H4": {"lines": [good_line("H4", "H4_A", "PARENT_OWNED_SAME_FAMILY")]},
            "H1": {"lines": [good_line("H1", "H1_A", "LOCAL_OWNED_DISTINCT")]},
            "M15": {"lines": [good_line("M15", "M15_A", "LOCAL_OWNED_DISTINCT")]},
        },
    }

    passed = mod.evaluate(
        ownership_join=joined,
        history_replay=good_history(),
        all_generations=False,
    )
    assert passed["status"] == "PASS_STAGE1_READY_FOR_STAGE2_DESIGN"
    assert passed["stage2_design_eligible"] is True
    assert passed["automatic_reselection_enabled"] is False
    assert passed["target_line_count"] == 4
    assert passed["ready_line_count"] == 4
    assert passed["blocked_line_count"] == 0
    assert passed["history_gate"]["ready"] is True

    # Ambiguous ownership blocks even if Quality was accidentally GOOD upstream.
    blocked_ownership = {
        **joined,
        "timeframes": {
            **joined["timeframes"],
            "H4": {"lines": [good_line("H4", "H4_A", "AMBIGUOUS_KEEP_VISIBLE")]},
        },
    }
    blocked_ownership["timeframes"]["H4"]["lines"][0]["ownership_evidence"].update({
        "owner_confirmed": False,
        "ownership_ambiguous": True,
    })
    blocked_ownership["timeframes"]["H4"]["lines"][0]["quality_audit"]["OwnershipReadiness"] = "HOLD"
    blocked = mod.evaluate(
        ownership_join=blocked_ownership,
        history_replay=good_history(),
        all_generations=False,
    )
    assert blocked["status"] == "BLOCKED_STAGE1"
    assert blocked["stage2_design_eligible"] is False
    assert blocked["blocked_line_count"] == 1
    codes = {
        f["code"]
        for line in blocked["lines"]
        for f in line["failures"]
    }
    assert "OWNERSHIP_NOT_PASS" in codes
    assert "OWNER_NOT_CONFIRMED" in codes
    assert "OWNERSHIP_AMBIGUOUS" in codes

    # Exact higher owner is insufficient for Stage-2 when the parent-family identity is unresolved.
    parent_open = {
        **joined,
        "timeframes": {
            **joined["timeframes"],
            "H1": {"lines": [good_line("H1", "H1_A", "HIGHER_TF_OWNER_PARENT_UNRESOLVED")]},
        },
    }
    parent_open["timeframes"]["H1"]["lines"][0]["ownership_evidence"].update({
        "owner_tf": "H4",
        "owner_confirmed": True,
        "ownership_ambiguous": False,
        "parent_family_unresolved": True,
    })
    parent_block = mod.evaluate(
        ownership_join=parent_open,
        history_replay=good_history(),
        all_generations=False,
    )
    assert parent_block["status"] == "BLOCKED_STAGE1"
    assert any(
        f["code"] == "PARENT_FAMILY_UNRESOLVED"
        for line in parent_block["lines"]
        for f in line["failures"]
    )

    # Candidate join ambiguity blocks Stage-2 even when the selected canonical variant was deterministic.
    candidate_open = {
        **joined,
        "timeframes": {
            **joined["timeframes"],
            "M15": {"lines": [good_line("M15", "M15_A")]},
        },
    }
    candidate_open["timeframes"]["M15"]["lines"][0]["match_status"] = "EXACT_AMBIGUOUS"
    candidate_block = mod.evaluate(
        ownership_join=candidate_open,
        history_replay=good_history(),
        all_generations=False,
    )
    assert candidate_block["status"] == "BLOCKED_STAGE1"
    assert any(
        f["code"] == "CANDIDATE_JOIN_NOT_EXACT_UNIQUE"
        for line in candidate_block["lines"]
        for f in line["failures"]
    )

    # 09/05 semantic-only adjudication remains a hard history gate until exact replay geometry is locked.
    hist = good_history()
    hist["user_adjudication_0905_transition"]["exact_anchor_geometry_locked"] = False
    hist["unresolved_evidence_gaps"] = [
        "0905 H1/M15 NO-LINE transition exact anchors remain unfrozen."
    ]
    history_block = mod.evaluate(
        ownership_join=joined,
        history_replay=hist,
        all_generations=False,
    )
    assert history_block["status"] == "BLOCKED_STAGE1"
    assert history_block["blocked_line_count"] == 0
    assert history_block["history_gate"]["ready"] is False
    hcodes = {x["code"] for x in history_block["history_gate"]["failures"]}
    assert "0905_EXACT_GEOMETRY_NOT_LOCKED" in hcodes
    assert "HISTORY_EVIDENCE_GAPS_REMAIN" in hcodes

    # PREVIOUS/HISTORY rows are excluded by default.
    with_previous = {
        **joined,
        "timeframes": {
            "D1": {
                "lines": [
                    good_line("D1", "D1_A", "ROOT_LOCAL_OWNED"),
                    {
                        **good_line("D1", "D1_PREV", "ROOT_LOCAL_OWNED"),
                        "generation_role": "PREVIOUS",
                        "match_status": "NOT_FOUND",
                    },
                ]
            },
            **{k: v for k, v in joined["timeframes"].items() if k != "D1"},
        },
    }
    current_only = mod.evaluate(
        ownership_join=with_previous,
        history_replay=good_history(),
        all_generations=False,
    )
    assert current_only["status"] == "PASS_STAGE1_READY_FOR_STAGE2_DESIGN"
    assert current_only["skipped_line_count"] == 1

    all_gen = mod.evaluate(
        ownership_join=with_previous,
        history_replay=good_history(),
        all_generations=True,
    )
    assert all_gen["status"] == "BLOCKED_STAGE1"

    # Determinism.
    again = mod.evaluate(
        ownership_join=joined,
        history_replay=good_history(),
        all_generations=False,
    )
    assert passed == again

    print("NVT9 TL QUALITY STAGE1 GATE SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
