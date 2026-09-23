from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.geometry import build_channel_candidates
from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import (
    rebuild_timeframe_baseline_0919_from_bars,
    rebuild_timeframe_from_bars,
    safe_symbol_filename,
)
from live_draw.tl_transition import resolve_tl_transition_state
from live_draw.turn_detector import detect_turns


def normalized_bar_fingerprint(bars) -> str:
    h = hashlib.sha256()
    for b in bars:
        row = (
            f"{b.time.isoformat()}|{float(b.open):.10f}|{float(b.high):.10f}|"
            f"{float(b.low):.10f}|{float(b.close):.10f}|{float(b.volume):.10f}\n"
        )
        h.update(row.encode("utf-8"))
    return h.hexdigest()


def current_line(state: dict[str, Any], symbol: str, timeframe: str, level: str = "LARGE_DOW") -> dict[str, Any] | None:
    slot = (state.get("slots") or {}).get(f"{symbol}|{timeframe}|{level}") or {}
    line = slot.get("current")
    return dict(line) if isinstance(line, dict) else None


def candidate_audit(candidate) -> dict[str, Any] | None:
    if candidate is None:
        return None
    return {
        "candidate_id": candidate.id_key,
        "direction": candidate.direction,
        "anchor1": {
            "kind": candidate.anchor1.kind,
            "time": candidate.anchor1.time.isoformat(),
            "price": float(candidate.anchor1.price),
            "confirmed_by_time": candidate.anchor1.confirmed_by_time.isoformat(),
            "retracement": float(candidate.anchor1.retracement),
        },
        "anchor2": {
            "kind": candidate.anchor2.kind,
            "time": candidate.anchor2.time.isoformat(),
            "price": float(candidate.anchor2.price),
            "confirmed_by_time": candidate.anchor2.confirmed_by_time.isoformat(),
            "retracement": float(candidate.anchor2.retracement),
        },
        "decision_hl": (
            {
                "kind": candidate.decision_hl.kind,
                "time": candidate.decision_hl.time.isoformat(),
                "price": float(candidate.decision_hl.price),
                "confirmed_by_time": candidate.decision_hl.confirmed_by_time.isoformat(),
                "retracement": float(candidate.decision_hl.retracement),
            }
            if candidate.decision_hl else None
        ),
        "hl_break_time": candidate.hl_break_time.isoformat() if candidate.hl_break_time else None,
        "hl_break_mode": candidate.hl_break_mode,
        "unbroken_close": bool(candidate.unbroken_close),
        "turn_span": int(candidate.turn_span),
        "tl_contacts": int(candidate.tl_contacts),
        "ch_contacts": int(candidate.ch_contacts),
        "ch_offset": float(candidate.ch_offset),
        "zone_width": float(candidate.zone_width),
    }


def geometry_matches_line(candidate, line: dict[str, Any] | None) -> bool:
    if candidate is None or not line:
        return False
    return (
        line.get("direction") == candidate.direction
        and line.get("anchor1_time") == candidate.anchor1.time.isoformat()
        and abs(float(line.get("anchor1_price")) - float(candidate.anchor1.price)) <= 1e-9
        and line.get("anchor2_time") == candidate.anchor2.time.isoformat()
        and abs(float(line.get("anchor2_price")) - float(candidate.anchor2.price)) <= 1e-9
    )


def match_line_candidate(line: dict[str, Any] | None, candidates) -> tuple[Any | None, int]:
    if not line:
        return None, 0
    matches = [c for c in candidates if geometry_matches_line(c, line)]
    matches.sort(key=lambda c: (
        abs(float(line.get("ch_offset", 0.0)) - float(c.ch_offset)),
        abs(float(line.get("zone_width", 0.0)) - float(c.zone_width)),
        c.id_key,
    ))
    return (matches[0] if matches else None), len(matches)


def build_timeframe_replay(
    *,
    input_csv: Path,
    symbol: str,
    timeframe: str,
    cutoff: datetime,
    rolling_bars: int,
) -> dict[str, Any]:
    all_bars = load_ohlc_csv(input_csv)
    eligible = [b for b in all_bars if b.time < cutoff]
    future = [b for b in all_bars if b.time >= cutoff]
    if len(eligible) < 3:
        raise ValueError(f"{timeframe}: insufficient pre-cutoff bars")
    window = eligible[-rolling_bars:] if len(eligible) > rolling_bars else eligible
    floor = window[0].time

    baseline_state, baseline_audit = rebuild_timeframe_baseline_0919_from_bars(
        window, symbol, timeframe
    )
    selected = current_line(baseline_state, symbol, timeframe, "LARGE_DOW")

    transition = resolve_tl_transition_state(
        eligible,
        symbol,
        timeframe,
        selected_state=selected,
        candidate_anchor_floor=floor,
    )

    history_state, history_audit = rebuild_timeframe_from_bars(
        eligible, symbol, timeframe
    )
    retained_line = current_line(history_state, symbol, timeframe, "LARGE_DOW")

    turns = detect_turns(eligible)
    all_candidates = build_channel_candidates(eligible, turns.pivots)
    retained_candidate, retained_match_count = match_line_candidate(retained_line, all_candidates)

    effective_state = transition.state
    effective_reason = transition.reason_code
    effective_candidate = transition.active_candidate
    retained_used = False

    if (
        transition.state == "TRANSITION_NO_TL"
        and transition.reason_code == "NO_ACTIVATED_N_STRUCTURE_YET"
        and retained_candidate is not None
        and bool(retained_candidate.unbroken_close)
    ):
        effective_state = "REFERENCE_RETAINED"
        effective_reason = "FULL_PRE_CUTOFF_HISTORY_RETAINS_UNBROKEN_REFERENCE"
        effective_candidate = retained_candidate
        retained_used = True

    # If the rolling window explicitly sees a broken old TL with no replacement,
    # historical retention is forbidden. This is the key 09/05 middle-state rule.
    retained_forbidden_by_break = (
        transition.state == "TRANSITION_NO_TL"
        and transition.reason_code == "OLD_TL_BROKEN_NO_UNBROKEN_REPLACEMENT_N"
    )

    return {
        "timeframe": timeframe,
        "input_csv": str(input_csv),
        "cutoff_exclusive": cutoff.isoformat(),
        "future_bars_used": False,
        "input_total_bar_count": len(all_bars),
        "pre_cutoff_bar_count": len(eligible),
        "excluded_future_bar_count": len(future),
        "pre_cutoff_first_bar": eligible[0].time.isoformat(),
        "pre_cutoff_last_bar": eligible[-1].time.isoformat(),
        "rolling_window_bar_count": len(window),
        "rolling_window_first_bar": window[0].time.isoformat(),
        "rolling_window_last_bar": window[-1].time.isoformat(),
        "rolling_window_policy": f"LAST_{rolling_bars}_PRE_CUTOFF_BARS",
        "selection_anchor_floor": floor.isoformat(),
        "pre_cutoff_fingerprint_sha256": normalized_bar_fingerprint(eligible),
        "rolling_window_fingerprint_sha256": normalized_bar_fingerprint(window),
        "baseline_selected_line": selected,
        "baseline_audit": {
            "status": baseline_audit.get("status"),
            "mode": baseline_audit.get("mode"),
            "transition_count": baseline_audit.get("transition_count"),
        },
        "rolling_transition": transition.to_audit_dict(),
        "history_current_line": retained_line,
        "history_current_candidate": candidate_audit(retained_candidate),
        "history_current_candidate_match_count": retained_match_count,
        "history_audit": {
            "status": history_audit.get("status"),
            "mode": history_audit.get("mode"),
            "closed_bars": history_audit.get("closed_bars"),
            "transition_count": history_audit.get("transition_count"),
            "last_structural_event_time": history_audit.get("last_structural_event_time"),
        },
        "effective_state": effective_state,
        "effective_reason_code": effective_reason,
        "effective_candidate": candidate_audit(effective_candidate),
        "history_reference_used": retained_used,
        "history_reference_forbidden_by_explicit_break": retained_forbidden_by_break,
        "detector_confirmed_pivot_count": len(turns.pivots),
        "full_pre_cutoff_candidate_count": len(all_candidates),
    }


def evaluate_transition_lock(h4: dict[str, Any], h1: dict[str, Any], cutoff: datetime) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    h4_roll = h4.get("rolling_transition") or {}
    h4_broken = h4_roll.get("broken_candidate")
    h4_break_time = h4_roll.get("break_time")
    add(
        "H4_TRANSITION_NO_TL",
        h4.get("effective_state") == "TRANSITION_NO_TL",
        f"effective_state={h4.get('effective_state')}",
    )
    add(
        "H4_EXPLICIT_BROKEN_PRIOR_TL",
        h4_roll.get("reason_code") == "OLD_TL_BROKEN_NO_UNBROKEN_REPLACEMENT_N"
        and isinstance(h4_broken, dict),
        f"reason={h4_roll.get('reason_code')} broken_candidate={bool(h4_broken)}",
    )
    h4_break_before_cutoff = False
    if h4_break_time:
        h4_break_before_cutoff = datetime.fromisoformat(h4_break_time) < cutoff
    add(
        "H4_BREAK_BEFORE_CUTOFF",
        h4_break_before_cutoff,
        f"break_time={h4_break_time} cutoff={cutoff.isoformat()}",
    )
    add(
        "H4_NO_RETAIN_AFTER_EXPLICIT_BREAK",
        h4.get("history_reference_used") is False
        and h4.get("history_reference_forbidden_by_explicit_break") is True,
        f"history_reference_used={h4.get('history_reference_used')}",
    )

    h1_state = h1.get("effective_state")
    h1_candidate = h1.get("effective_candidate")
    add(
        "H1_VALID_OWNER_FAMILY",
        h1_state in {"ACTIVE", "NEW_ACTIVE", "REFERENCE_RETAINED"} and isinstance(h1_candidate, dict),
        f"effective_state={h1_state} candidate={bool(h1_candidate)}",
    )
    add(
        "H1_EXACT_CANDIDATE_ID",
        bool((h1_candidate or {}).get("candidate_id")),
        f"candidate_id={(h1_candidate or {}).get('candidate_id')}",
    )
    add(
        "H1_CLOSED_BAR_HL_ACTIVATION",
        (
            h1_state == "REFERENCE_RETAINED"
            or str((h1_candidate or {}).get("hl_break_mode") or "").startswith("CLOSED_BAR_CLOSE")
        ),
        f"state={h1_state} hl_break_mode={(h1_candidate or {}).get('hl_break_mode')}",
    )
    if h1_state == "REFERENCE_RETAINED":
        add(
            "H1_RETAINED_REFERENCE_UNBROKEN",
            (h1_candidate or {}).get("unbroken_close") is True
            and h1.get("history_reference_used") is True
            and int(h1.get("history_current_candidate_match_count") or 0) >= 1,
            (
                f"unbroken={(h1_candidate or {}).get('unbroken_close')} "
                f"history_used={h1.get('history_reference_used')} "
                f"match_count={h1.get('history_current_candidate_match_count')}"
            ),
        )

    for tf_name, tf_payload in (("H4", h4), ("H1", h1)):
        add(
            f"{tf_name}_NO_LOOKAHEAD",
            tf_payload.get("future_bars_used") is False
            and datetime.fromisoformat(tf_payload["pre_cutoff_last_bar"]) < cutoff,
            f"last={tf_payload.get('pre_cutoff_last_bar')}",
        )
        add(
            f"{tf_name}_INPUT_FINGERPRINT_PRESENT",
            bool(tf_payload.get("pre_cutoff_fingerprint_sha256")),
            f"sha256={tf_payload.get('pre_cutoff_fingerprint_sha256')}",
        )

    passed = all(x["pass"] for x in checks)
    return {
        "status": "PASS_0905_TRANSITION_EXACT_REPLAY" if passed else "BLOCKED_0905_TRANSITION_EXACT_REPLAY",
        "transition_exact_geometry_locked": passed,
        "teacher_ground_truth_exact_anchors_locked": False,
        "scope": "H4/H1 transition-state geometry plus H1->M15 inheritance source",
        "checks": checks,
        "failed_checks": [x for x in checks if not x["pass"]],
        "display_contract": {
            "H4_display_owner_when_transition_no_tl": "D1",
            "M15_native_selector_enabled": False,
            "M15_display_owner": "H1",
            "M15_copy_without_reselection": True,
        },
        "guard": (
            "This lock certifies deterministic pre-cutoff transition replay only. "
            "It does not lock GT_0004 teacher D1 anchors or any separate teacher visual Ground Truth."
        ),
    }


def build_exact_replay(
    *,
    input_dir: Path,
    symbol: str,
    cutoff: datetime,
    rolling_bars: int = 600,
) -> dict[str, Any]:
    safe = safe_symbol_filename(symbol)
    tfs = {}
    for tf in ("H4", "H1"):
        src = input_dir / f"NVT_{safe}_{tf}.csv"
        if not src.exists():
            raise FileNotFoundError(src)
        tfs[tf] = build_timeframe_replay(
            input_csv=src,
            symbol=symbol,
            timeframe=tf,
            cutoff=cutoff,
            rolling_bars=rolling_bars,
        )

    lock = evaluate_transition_lock(tfs["H4"], tfs["H1"], cutoff)
    return {
        "schema": "nvt9-0905-transition-exact-replay/1.0",
        "audit_id": "ID10IQ200",
        "symbol": symbol,
        "case_date": "2026-09-05",
        "cutoff_exclusive": cutoff.isoformat(),
        "rolling_bars": rolling_bars,
        "status": lock["status"],
        "transition_exact_geometry_locked": lock["transition_exact_geometry_locked"],
        "teacher_ground_truth_exact_anchors_locked": False,
        "timeframes": tfs,
        "lock": lock,
        "production_writeback": False,
        "renderer_writeback": False,
        "mt4_object_writeback": False,
        "state_mutated": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Freeze and replay 09/05 H4/H1 transition state using only pre-cutoff NVT OHLC."
    )
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--cutoff", default="2026-09-05T00:00:00")
    ap.add_argument("--rolling-bars", type=int, default=600)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    cutoff = datetime.fromisoformat(args.cutoff)
    if cutoff != datetime.fromisoformat("2026-09-05T00:00:00"):
        raise ValueError("09/05 exact transition replay requires cutoff 2026-09-05T00:00:00")
    if args.rolling_bars < 3:
        raise ValueError("rolling-bars must be >= 3")

    result = build_exact_replay(
        input_dir=Path(args.input_dir),
        symbol=args.symbol.strip(),
        cutoff=cutoff,
        rolling_bars=args.rolling_bars,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "transition_exact_geometry_locked": result["transition_exact_geometry_locked"],
        "teacher_ground_truth_exact_anchors_locked": False,
        "h4_state": result["timeframes"]["H4"]["effective_state"],
        "h4_reason": result["timeframes"]["H4"]["effective_reason_code"],
        "h1_state": result["timeframes"]["H1"]["effective_state"],
        "h1_candidate_id": (
            (result["timeframes"]["H1"].get("effective_candidate") or {}).get("candidate_id")
        ),
        "failed_check_count": len(result["lock"]["failed_checks"]),
        "output": str(out),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0 if result["transition_exact_geometry_locked"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
