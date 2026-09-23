from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("nvt9_0905_exact_replay", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def cand(candidate_id: str, *, unbroken: bool = True) -> dict:
    return {
        "candidate_id": candidate_id,
        "direction": "FALLING",
        "anchor1": {
            "kind": "HIGH",
            "time": "2026-07-30T16:00:00",
            "price": 162.954,
            "confirmed_by_time": "2026-07-31T16:00:00",
            "retracement": 0.38,
        },
        "anchor2": {
            "kind": "HIGH",
            "time": "2026-09-02T04:00:00",
            "price": 160.387,
            "confirmed_by_time": "2026-09-03T04:00:00",
            "retracement": 0.38,
        },
        "decision_hl": {
            "kind": "LOW",
            "time": "2026-08-03T00:00:00",
            "price": 157.0,
            "confirmed_by_time": "2026-08-04T00:00:00",
            "retracement": 0.38,
        },
        "hl_break_time": "2026-08-04T04:00:00",
        "hl_break_mode": "CLOSED_BAR_CLOSE_PROVISIONAL",
        "unbroken_close": unbroken,
        "turn_span": 9,
        "tl_contacts": 3,
        "ch_contacts": 4,
        "ch_offset": -4.0,
        "zone_width": 0.1,
    }


def base_tf() -> dict:
    return {
        "future_bars_used": False,
        "pre_cutoff_last_bar": "2026-09-04T20:00:00",
        "pre_cutoff_fingerprint_sha256": "a" * 64,
        "rolling_window_fingerprint_sha256": "b" * 64,
        "history_reference_used": False,
        "history_reference_forbidden_by_explicit_break": False,
        "history_current_candidate_match_count": 1,
    }


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    mod = load_module(repo / "tools" / "nvt" / "build_nvt9_0905_transition_exact_replay.py")
    cutoff = datetime.fromisoformat("2026-09-05T00:00:00")

    h4 = base_tf()
    h4.update({
        "effective_state": "TRANSITION_NO_TL",
        "effective_reason_code": "OLD_TL_BROKEN_NO_UNBROKEN_REPLACEMENT_N",
        "history_reference_forbidden_by_explicit_break": True,
        "rolling_transition": {
            "state": "TRANSITION_NO_TL",
            "reason_code": "OLD_TL_BROKEN_NO_UNBROKEN_REPLACEMENT_N",
            "broken_candidate": cand("FALLING:H4:BROKEN", unbroken=False),
            "break_time": "2026-09-04T12:00:00",
        },
    })
    h1 = base_tf()
    h1.update({
        "effective_state": "NEW_ACTIVE",
        "effective_reason_code": "NEW_N_STRUCTURE_CONFIRMED_AND_HL_BROKEN",
        "effective_candidate": cand("FALLING:H1:ACTIVE", unbroken=True),
        "rolling_transition": {
            "state": "NEW_ACTIVE",
            "reason_code": "NEW_N_STRUCTURE_CONFIRMED_AND_HL_BROKEN",
        },
    })

    passed = mod.evaluate_transition_lock(h4, h1, cutoff)
    assert passed["status"] == "PASS_0905_TRANSITION_EXACT_REPLAY"
    assert passed["transition_exact_geometry_locked"] is True
    assert passed["teacher_ground_truth_exact_anchors_locked"] is False
    assert not passed["failed_checks"]

    # H4 must prove an actual prior TL break, not merely absence of an activated N.
    h4_no_break = dict(h4)
    h4_no_break["rolling_transition"] = {
        "state": "TRANSITION_NO_TL",
        "reason_code": "NO_ACTIVATED_N_STRUCTURE_YET",
        "broken_candidate": None,
        "break_time": None,
    }
    blocked = mod.evaluate_transition_lock(h4_no_break, h1, cutoff)
    assert blocked["status"] == "BLOCKED_0905_TRANSITION_EXACT_REPLAY"
    assert blocked["transition_exact_geometry_locked"] is False
    assert any(x["name"] == "H4_EXPLICIT_BROKEN_PRIOR_TL" for x in blocked["failed_checks"])

    # A retained H1 reference is acceptable only when it is exact, matched and unbroken.
    h1_retained = base_tf()
    h1_retained.update({
        "effective_state": "REFERENCE_RETAINED",
        "effective_reason_code": "FULL_PRE_CUTOFF_HISTORY_RETAINS_UNBROKEN_REFERENCE",
        "effective_candidate": cand("FALLING:H1:RETAINED", unbroken=True),
        "history_reference_used": True,
        "history_current_candidate_match_count": 1,
        "rolling_transition": {
            "state": "TRANSITION_NO_TL",
            "reason_code": "NO_ACTIVATED_N_STRUCTURE_YET",
        },
    })
    retained = mod.evaluate_transition_lock(h4, h1_retained, cutoff)
    assert retained["transition_exact_geometry_locked"] is True

    h1_retained["effective_candidate"]["unbroken_close"] = False
    retained_bad = mod.evaluate_transition_lock(h4, h1_retained, cutoff)
    assert retained_bad["transition_exact_geometry_locked"] is False
    assert any(x["name"] == "H1_RETAINED_REFERENCE_UNBROKEN" for x in retained_bad["failed_checks"])

    # Lookahead must hard-block the lock.
    h1_future = dict(h1)
    h1_future["future_bars_used"] = True
    future_bad = mod.evaluate_transition_lock(h4, h1_future, cutoff)
    assert future_bad["transition_exact_geometry_locked"] is False
    assert any(x["name"] == "H1_NO_LOOKAHEAD" for x in future_bad["failed_checks"])

    print("NVT9 0905 EXACT TRANSITION REPLAY SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
