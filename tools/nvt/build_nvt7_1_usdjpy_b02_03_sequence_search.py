from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.market_input import load_ohlc_csv
from live_draw.turn_detector import detect_turns
from nvt.build_usdjpy_historical_review_bundle import (
    DEV_EXCLUDE_END,
    DEV_EXCLUDE_START,
    WINDOWS,
    resolve_csv,
    timeframe_payload,
)


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pivot_dict(p) -> dict:
    return {
        "kind": p.kind,
        "time": p.time.isoformat(),
        "price": p.price,
        "confirmed_by_time": p.confirmed_by_time.isoformat(),
        "retracement": p.retracement,
    }


def first_close_breakout(bars, start_time: datetime, level: float):
    for b in bars:
        if b.time <= start_time:
            continue
        if b.close > level:
            return b
    return None


def same_pivot(a, b) -> bool:
    return a.kind == b.kind and a.time == b.time and abs(a.price - b.price) < 1e-9


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Research-only broad B02_03 sequence retrieval. Finds H1 proxy sequences of "
            "confirmed low -> confirmed structural high -> later close breakout -> post-break confirmed higher low. "
            "This is retrieval only and does not claim to identify the user's small/mid-Dow HLs or red-circle point."
        )
    )
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--batch01", required=True)
    ap.add_argument("--batch02", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--max-cases", type=int, default=6)
    args = ap.parse_args()

    batch01 = load_json(args.batch01)
    batch02 = load_json(args.batch02)
    if batch01.get("schema") != "nvt8h-usdjpy-historical-review-bundle/0.2":
        raise ValueError("unexpected Batch01 schema")
    if batch02.get("schema") != "nvt7.1-usdjpy-targeted-historical-review/0.1":
        raise ValueError("unexpected Batch02 schema")

    input_dir = Path(args.input_dir)
    paths = {tf: resolve_csv(input_dir, tf) for tf in WINDOWS}
    all_bars = {tf: load_ohlc_csv(path) for tf, path in paths.items()}
    h1 = [b for b in all_bars["H1"] if b.time < DEV_EXCLUDE_START]
    turns = detect_turns(h1, retracement=0.38)
    pivots = turns.pivots

    prior_dates = {
        datetime.fromisoformat(c.get("cutoff")).date()
        for bundle in (batch01, batch02)
        for c in (bundle.get("cases") or [])
        if c.get("cutoff")
    }

    candidates = []
    seen = set()
    for hi_idx, high in enumerate(pivots):
        if high.kind != "HIGH":
            continue

        origin = None
        for j in range(hi_idx - 1, -1, -1):
            if pivots[j].kind == "LOW" and pivots[j].time < high.time:
                origin = pivots[j]
                break
        if origin is None:
            continue

        breakout = first_close_breakout(h1, high.confirmed_by_time, high.price)
        if breakout is None or breakout.time >= DEV_EXCLUDE_START:
            continue

        prebreak_lows = [
            p for p in pivots
            if p.kind == "LOW"
            and p.time > high.time
            and p.time < breakout.time
            and p.confirmed_by_time <= breakout.time
        ]

        second_low = None
        for p in pivots:
            if p.kind != "LOW":
                continue
            if p.time <= breakout.time:
                continue
            if p.confirmed_by_time >= DEV_EXCLUDE_START:
                continue
            if p.price <= origin.price:
                continue
            second_low = p
            break
        if second_low is None:
            continue

        cutoff = second_low.confirmed_by_time
        if DEV_EXCLUDE_START <= cutoff <= DEV_EXCLUDE_END:
            continue

        frozen_h1 = [b for b in h1 if b.time <= cutoff]
        frozen_pivots = detect_turns(frozen_h1, retracement=0.38).pivots
        if not any(same_pivot(p, high) for p in frozen_pivots):
            continue
        if not any(same_pivot(p, second_low) for p in frozen_pivots):
            continue

        key = (origin.time, high.time, breakout.time, second_low.time)
        if key in seen:
            continue
        seen.add(key)

        score = 2
        reasons = ["CLOSE_BREAKS_CONFIRMED_H1_HIGH", "POST_BREAK_CONFIRMED_LOW_ABOVE_ORIGIN_LOW"]
        if prebreak_lows:
            score += 1
            reasons.append("PRE_BREAK_PULLBACK_LOW_EXISTS")
        if cutoff.date() not in prior_dates:
            score += 1
            reasons.append("UNSEEN_CASE_DATE")

        candidates.append({
            "cutoff": cutoff,
            "score": score,
            "reasons": reasons,
            "origin_low": origin,
            "structural_high": high,
            "breakout_bar": breakout,
            "prebreak_lows": prebreak_lows,
            "second_low": second_low,
            "overlaps_prior_case_date": cutoff.date() in prior_dates,
        })

    candidates.sort(key=lambda x: (x["score"], x["cutoff"]), reverse=True)
    unseen = [c for c in candidates if not c["overlaps_prior_case_date"]]
    overlap = [c for c in candidates if c["overlaps_prior_case_date"]]
    selected = (unseen + overlap)[: max(1, args.max_cases)]
    selected.sort(key=lambda x: x["cutoff"])

    cases = []
    for i, c in enumerate(selected, 1):
        cutoff = c["cutoff"]
        cases.append({
            "case_id": f"USDJPY_NVT71_B03C_{i:02d}",
            "cutoff": cutoff.isoformat(),
            "future_bars_included": False,
            "known_teacher_answer": None,
            "review_mode": "CHATGPT_FIRST_USER_ADJUDICATION_ONLY_WHEN_NEEDED",
            "retrieval_score": c["score"],
            "retrieval_reasons": c["reasons"],
            "overlaps_prior_case_date": c["overlaps_prior_case_date"],
            "sequence_proxy": {
                "origin_low": pivot_dict(c["origin_low"]),
                "structural_high_proxy": pivot_dict(c["structural_high"]),
                "breakout_close_bar": {
                    "time": c["breakout_bar"].time.isoformat(),
                    "open": c["breakout_bar"].open,
                    "high": c["breakout_bar"].high,
                    "low": c["breakout_bar"].low,
                    "close": c["breakout_bar"].close,
                },
                "prebreak_confirmed_lows": [pivot_dict(p) for p in c["prebreak_lows"][-3:]],
                "post_break_second_low_proxy": pivot_dict(c["second_low"]),
            },
            "timeframes": {
                tf: timeframe_payload(args.symbol, tf, all_bars[tf], cutoff)
                for tf in WINDOWS
            },
            "user_semantic_questions_not_preanswered": {
                "is_pre_break_state_range_not_h1_rising": None,
                "is_line_drawable_but_only_provisional_before_break": None,
                "does_breakout_promote_line_importance": None,
                "does_post_break_low_confirm_large_dow_tl": None,
                "does_second_low_react_at_user_mid_dow_upper_hl": None,
                "notes": None,
            },
        })

    report = {
        "schema": "nvt7.1-b02-03-sequence-proxy-search/0.1",
        "status": "RESEARCH_ONLY_CANDIDATE_SEARCH",
        "phase": "NVT7.1_BATCH03C_B02_03_SEQUENCE_PROXY_SEARCH",
        "symbol_scope": "USDJPY_ONLY",
        "timeframe": "H1",
        "selection_policy": {
            "future_hidden": True,
            "development_video_window_excluded": [DEV_EXCLUDE_START.isoformat(), DEV_EXCLUDE_END.isoformat()],
            "mechanical_active_leg_not_required": True,
            "large_mid_direction_not_required": True,
            "same_day_reanchor_not_required": True,
            "proxy_sequence": [
                "confirmed H1 LOW origin",
                "confirmed H1 HIGH structural-high proxy",
                "later closed bar closes above that high",
                "later confirmed H1 LOW remains above origin low",
            ],
            "prebreak_pullback_low_is_bonus_not_requirement": True,
            "prior_case_dates_preferred_against_but_not_hard_excluded": True,
            "max_cases": args.max_cases,
        },
        "candidate_count_before_sampling": len(candidates),
        "unseen_date_candidate_count": len(unseen),
        "selected_case_count": len(cases),
        "cases": cases,
        "guardrails": [
            "This is a broad retrieval proxy, not the user's semantic Dow classification.",
            "Do not treat the confirmed-HIGH proxy as the red-circle point without review.",
            "Do not treat the post-break confirmed LOW proxy as the user's second valid low without review.",
            "Do not infer the small-Dow or mid-Dow horizontal levels from this search.",
            "Do not invent breakout buffers or reaction tolerances.",
            "Do not amend frozen NVT7 or Production from this output alone.",
        ],
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
        "status": "PASS" if cases else "PASS_NO_CASES",
        "candidate_count_before_sampling": len(candidates),
        "unseen_date_candidate_count": len(unseen),
        "selected_case_count": len(cases),
        "output": str(out),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
