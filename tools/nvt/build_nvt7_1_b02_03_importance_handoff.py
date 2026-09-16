from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "pass": bool(passed), "detail": detail}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build research-only B02_03 line-importance/confirmation handoff from targeted historical bundle plus user adjudication."
    )
    ap.add_argument("--targeted-bundle", required=True)
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    bundle = load_json(args.targeted_bundle)
    adj = load_json(args.adjudication)

    if bundle.get("schema") != "nvt7.1-usdjpy-targeted-historical-review/0.1":
        raise ValueError("unexpected targeted historical review schema")
    if adj.get("schema") != "nvt7.1-usdjpy-b02-03-user-adjudication/0.1":
        raise ValueError("unexpected B02_03 adjudication schema")

    cases = {c.get("case_id"): c for c in bundle.get("cases") or []}
    case = cases.get("USDJPY_NVT71_B02_03")
    if not case:
        raise ValueError("USDJPY_NVT71_B02_03 not found in targeted bundle")

    h1 = ((case.get("timeframes") or {}).get("H1") or {}).get("analysis") or {}
    large = h1.get("baseline_large") or {}
    mid = h1.get("baseline_mid") or {}
    a = adj.get("adjudication") or {}

    required_phases = [
        "PROVISIONAL_DRAWABLE",
        "IMPORTANT_CANDIDATE",
        "CURRENT_CONFIRMED_LARGE_DOW_TL",
    ]

    checks = [
        check(
            "cutoff_matches",
            case.get("cutoff") == adj.get("cutoff"),
            f"bundle={case.get('cutoff')} adjudication={adj.get('cutoff')}",
        ),
        check(
            "future_hidden",
            case.get("future_bars_included") is False,
            "Historical adjudication must remain future-hidden.",
        ),
        check(
            "mechanical_large_mid_are_rising",
            large.get("direction") == "RISING" and mid.get("direction") == "RISING",
            "B02_03 deliberately tests that mechanical Large/Mid RISING is not sufficient to declare user-semantic H1 rising.",
        ),
        check(
            "pre_break_state_is_range_not_rising",
            a.get("pre_break_direction_state") == "RANGE_NOT_H1_RISING",
            "The user adjudication explicitly inserts a range/not-yet-rising state before structural-high breakout.",
        ),
        check(
            "mechanical_direction_decoupled",
            a.get("mechanical_large_mid_rising_is_not_sufficient_for_user_direction_state") is True,
            "Mechanical selector direction and user-semantic direction state must remain separate.",
        ),
        check(
            "pre_break_tl_is_provisional",
            (a.get("tl_before_resume") or {}).get("drawable") is True
            and (a.get("tl_before_resume") or {}).get("important") is False
            and (a.get("tl_before_resume") or {}).get("phase") == "PROVISIONAL_DRAWABLE",
            "The cyan line can exist before breakout without being important/current.",
        ),
        check(
            "breakout_promotes_importance",
            (a.get("tl_after_resume") or {}).get("promotion_trigger") == "RED_CIRCLE_STRUCTURAL_HIGH_BREAK"
            and (a.get("tl_after_resume") or {}).get("phase") == "IMPORTANT_CANDIDATE"
            and (a.get("tl_after_resume") or {}).get("important") is True,
            "Structural-high breakout promotes the drawable line to an important candidate.",
        ),
        check(
            "second_low_confirms_large_dow_tl",
            (a.get("large_dow_tl_confirmation") or {}).get("requires_second_valid_low") is True
            and (a.get("large_dow_tl_confirmation") or {}).get("second_low_context")
            == "REACTION_AT_MID_DOW_HORIZONTAL_LEVEL_YELLOW_UPPER"
            and (a.get("large_dow_tl_confirmation") or {}).get("phase_after_confirmation")
            == "CURRENT_CONFIRMED_LARGE_DOW_TL",
            "Large-Dow current TL is confirmed only after the post-break second valid low at the mid-Dow upper HL.",
        ),
        check(
            "no_numeric_threshold_invented",
            (a.get("rising_resume_trigger") or {}).get("numeric_price_locked") is False,
            "This evidence does not lock an arbitrary breakout buffer or exact price threshold.",
        ),
        check(
            "research_only",
            adj.get("production_writeback") is False
            and adj.get("normal_run_modified") is False
            and adj.get("mt4_object_writeback") is False,
            "B02_03 importance candidate must remain isolated from Production Normal Run and MT4 drawing.",
        ),
    ]

    failures = [c for c in checks if not c["pass"]]

    report = {
        "schema": "nvt7.1-b02-03-line-importance-handoff/0.1",
        "status": "PASS_CONTRACTS" if not failures else "FAIL_CONTRACTS",
        "phase": "NVT7.1_B02_03_LINE_IMPORTANCE_CONFIRMATION",
        "symbol_scope": "USDJPY_ONLY",
        "timeframe": "H1",
        "evidence_class": "USER_OPERATIONAL_EVIDENCE",
        "case_id": case.get("case_id"),
        "cutoff": case.get("cutoff"),
        "observed_mechanical_state": {
            "active_leg": h1.get("active_leg"),
            "large_direction": large.get("direction"),
            "large_id": large.get("candidate_id"),
            "mid_direction": mid.get("direction"),
            "mid_id": mid.get("candidate_id"),
        },
        "research_state_machine": {
            "direction_state_before_break": "RANGE_NOT_H1_RISING",
            "line_phases": required_phases,
            "transitions": [
                {
                    "from": "RANGE_NOT_H1_RISING + PROVISIONAL_DRAWABLE",
                    "event": "BREAK_ABOVE_STRUCTURAL_HIGH_RED_CIRCLE",
                    "to": "RISING_RESUMED + IMPORTANT_CANDIDATE",
                },
                {
                    "from": "RISING_RESUMED + IMPORTANT_CANDIDATE",
                    "event": "SECOND_VALID_LOW_REACTS_AT_MID_DOW_UPPER_HL",
                    "to": "CURRENT_CONFIRMED_LARGE_DOW_TL",
                },
            ],
            "dimensions_kept_separate": [
                "DRAWABILITY",
                "IMPORTANCE_CONFIRMATION",
                "VISIBILITY",
                "DECISION_OWNERSHIP",
                "DIRECTION_STATE",
            ],
        },
        "checks": checks,
        "failure_checks": failures,
        "all_contracts_pass": not failures,
        "interpretation": (
            "PASS_CONTRACTS confirms that the B02_03 user adjudication can be represented without forcing mechanical Large/Mid RISING to equal user-semantic H1 rising. "
            "It validates a research state model only; it does not validate numeric thresholds, teacher ground truth, or Production promotion."
        ),
        "still_unfixed": [
            "Exact objective extraction of the small-Dow and mid-Dow horizontal levels.",
            "Exact objective identification of the red-circle structural-high breakout point.",
            "Breakout tolerance/buffer.",
            "Objective second-low reaction tolerance at the mid-Dow upper HL.",
            "Generalization beyond this USDJPY H1 evidence case.",
        ],
        "recommended_next_research_action": (
            "Search additional future-hidden USDJPY H1 cases for the same sequence: range -> provisional drawable TL -> structural-high breakout -> important line -> second-low confirmation. "
            "Do not amend frozen NVT7 or Production until repeated evidence exists."
        ),
        "production_promotion_ready": False,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "output": str(out),
        "check_count": len(checks),
        "failure_count": len(failures),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
