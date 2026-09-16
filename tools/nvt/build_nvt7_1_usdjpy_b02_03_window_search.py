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
from nvt.build_usdjpy_historical_review_bundle import (
    CORE_TIMEFRAMES,
    DEV_EXCLUDE_END,
    DEV_EXCLUDE_START,
    WINDOWS,
    frozen_summary,
    resolve_csv,
    timeframe_payload,
)


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def daily_candidates(h1_bars):
    by_day = {}
    for b in h1_bars:
        if DEV_EXCLUDE_START <= b.time <= DEV_EXCLUDE_END:
            continue
        by_day[b.time.date()] = b.time
    return sorted(by_day.values())


def count_at_or_before(bars, cutoff: datetime) -> int:
    return sum(1 for b in bars if b.time <= cutoff)


def eligible_cutoffs(all_bars):
    out = []
    for cutoff in daily_candidates(all_bars["H1"]):
        if all(count_at_or_before(all_bars[tf], cutoff) >= WINDOWS[tf] for tf in CORE_TIMEFRAMES):
            out.append(cutoff)
    return out


def summary_at(symbol: str, tf: str, bars, cutoff: datetime):
    frozen = [b for b in bars if b.time <= cutoff]
    return frozen_summary(symbol, tf, frozen)


def cand(summary: dict, key: str) -> dict:
    return summary.get(key) or {}


def same_direction_reanchor(prev_h1: dict, cur_h1: dict) -> list[dict]:
    changes = []
    for key in ("baseline_large", "baseline_mid"):
        old = cand(prev_h1, key)
        new = cand(cur_h1, key)
        if not old or not new:
            continue
        if old.get("candidate_id") == new.get("candidate_id"):
            continue
        if old.get("direction") != new.get("direction"):
            continue
        old_slope = old.get("slope_per_second")
        new_slope = new.get("slope_per_second")
        relation = None
        if old_slope is not None and new_slope is not None:
            if abs(new_slope) < abs(old_slope):
                relation = "NEW_GENTLER"
            elif abs(new_slope) > abs(old_slope):
                relation = "NEW_STEEPER"
            else:
                relation = "SAME_ABS_SLOPE"
        changes.append({
            "layer": key,
            "old_id": old.get("candidate_id"),
            "new_id": new.get("candidate_id"),
            "direction": new.get("direction"),
            "slope_relation": relation,
            "old_slope_per_second": old_slope,
            "new_slope_per_second": new_slope,
        })
    return changes


def evenly_pick(items, count):
    if len(items) <= count:
        return list(items)
    if count <= 1:
        return [items[len(items) // 2]]
    idxs = []
    for i in range(count):
        idx = round(i * (len(items) - 1) / (count - 1))
        if idx not in idxs:
            idxs.append(idx)
    return [items[i] for i in idxs]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Find future-hidden USDJPY H1 B02_03 analogue review candidates using a backward-only daily window. "
            "The window is a retrieval heuristic only, not a market-rule threshold."
        )
    )
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--batch01", required=True)
    ap.add_argument("--batch02", required=True)
    ap.add_argument("--strict-batch03", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--lookback-snapshots", type=int, default=5)
    ap.add_argument("--max-cases", type=int, default=6)
    args = ap.parse_args()

    batch01 = load_json(args.batch01)
    batch02 = load_json(args.batch02)
    strict = load_json(args.strict_batch03)
    if batch01.get("schema") != "nvt8h-usdjpy-historical-review-bundle/0.2":
        raise ValueError("unexpected Batch01 schema")
    if batch02.get("schema") != "nvt7.1-usdjpy-targeted-historical-review/0.1":
        raise ValueError("unexpected Batch02 schema")
    if strict.get("schema") != "nvt7.1-b02-03-analogue-search/0.1":
        raise ValueError("unexpected strict Batch03 schema")

    excluded_cutoffs = {c.get("cutoff") for c in batch01.get("cases") or []}
    excluded_cutoffs |= {c.get("cutoff") for c in batch02.get("cases") or []}
    excluded_cutoffs |= {c.get("cutoff") for c in strict.get("cases") or []}

    input_dir = Path(args.input_dir)
    paths = {tf: resolve_csv(input_dir, tf) for tf in WINDOWS}
    all_bars = {tf: load_ohlc_csv(path) for tf, path in paths.items()}
    cutoffs = eligible_cutoffs(all_bars)

    rows = []
    prev = None
    for cutoff in cutoffs:
        summaries = {tf: summary_at(args.symbol, tf, all_bars[tf], cutoff) for tf in CORE_TIMEFRAMES}
        h1 = summaries["H1"]
        large = cand(h1, "baseline_large")
        mid = cand(h1, "baseline_mid")
        reanchors = same_direction_reanchor(prev["summaries"]["H1"], h1) if prev else []
        disagreement = (
            h1.get("active_leg") == "FALLING"
            and large.get("direction") == "RISING"
            and mid.get("direction") == "RISING"
        )
        rows.append({
            "cutoff": cutoff,
            "cutoff_iso": cutoff.isoformat(),
            "summaries": summaries,
            "previous_daily_cutoff": prev["cutoff_iso"] if prev else None,
            "reanchors": reanchors,
            "mechanical_disagreement": disagreement,
        })
        prev = rows[-1]

    candidates = []
    n = max(1, args.lookback_snapshots)
    for i, row in enumerate(rows):
        if row["cutoff_iso"] in excluded_cutoffs:
            continue
        if not row["mechanical_disagreement"]:
            continue

        history = rows[max(0, i - n): i + 1]
        rising_reanchors = []
        for h in history:
            for ch in h["reanchors"]:
                if ch.get("direction") == "RISING":
                    rising_reanchors.append({
                        "event_cutoff": h["cutoff_iso"],
                        **ch,
                    })

        gentler = [x for x in rising_reanchors if x.get("slope_relation") == "NEW_GENTLER"]
        tier = "A_WINDOWED_REANCHOR" if rising_reanchors else "B_DISAGREEMENT_ONLY"
        score = 2 + (2 if rising_reanchors else 0) + (1 if gentler else 0)
        candidates.append({
            **row,
            "retrieval_tier": tier,
            "analogue_score": score,
            "lookback_rising_reanchors": rising_reanchors,
            "lookback_gentler_rising_reanchors": gentler,
        })

    # Prefer candidates with a recent prior/current rising re-anchor, but if none exist,
    # return disagreement-only cases so ChatGPT can still inspect the user-semantic structure.
    tier_a = [r for r in candidates if r["retrieval_tier"] == "A_WINDOWED_REANCHOR"]
    pool = tier_a if tier_a else candidates
    pool.sort(key=lambda r: (r["analogue_score"], r["cutoff"]), reverse=True)
    selected = evenly_pick(pool, max(1, args.max_cases))
    selected.sort(key=lambda r: r["cutoff"])

    cases = []
    for i, row in enumerate(selected, 1):
        cutoff = row["cutoff"]
        cases.append({
            "case_id": f"USDJPY_NVT71_B03B_{i:02d}",
            "cutoff": row["cutoff_iso"],
            "previous_daily_cutoff": row["previous_daily_cutoff"],
            "future_bars_included": False,
            "known_teacher_answer": None,
            "review_mode": "CHATGPT_FIRST_USER_ADJUDICATION_ONLY_WHEN_NEEDED",
            "retrieval_tier": row["retrieval_tier"],
            "analogue_score": row["analogue_score"],
            "mechanical_evidence": {
                "h1_active_leg": row["summaries"]["H1"].get("active_leg"),
                "h1_large_direction": cand(row["summaries"]["H1"], "baseline_large").get("direction"),
                "h1_mid_direction": cand(row["summaries"]["H1"], "baseline_mid").get("direction"),
                "lookback_rising_reanchors": row["lookback_rising_reanchors"],
                "lookback_gentler_rising_reanchors": row["lookback_gentler_rising_reanchors"],
            },
            "timeframes": {
                tf: timeframe_payload(args.symbol, tf, all_bars[tf], cutoff)
                for tf in WINDOWS
            },
            "user_semantic_questions_not_preanswered": {
                "range_not_h1_rising_before_structural_high_break": None,
                "provisional_tl_drawable_before_break": None,
                "structural_high_break_promotes_importance": None,
                "second_valid_low_at_mid_dow_upper_hl_confirms_large_dow_tl": None,
                "notes": None,
            },
        })

    report = {
        "schema": "nvt7.1-b02-03-window-analogue-search/0.2",
        "status": "RESEARCH_ONLY_CANDIDATE_SEARCH",
        "phase": "NVT7.1_BATCH03B_B02_03_BACKWARD_WINDOW_SEARCH",
        "symbol_scope": "USDJPY_ONLY",
        "timeframe": "H1",
        "strict_batch03_candidate_count": strict.get("candidate_count_before_sampling"),
        "selection_policy": {
            "future_hidden": True,
            "exclude_development_video_window": [DEV_EXCLUDE_START.isoformat(), DEV_EXCLUDE_END.isoformat()],
            "exclude_batch01_batch02_and_strict_batch03_cutoffs": True,
            "current_cutoff_requirement": "H1 active_leg FALLING while Large/Mid are RISING",
            "preferred_context": "at least one same-direction RISING re-anchor in current/prior backward-only daily snapshots",
            "lookback_snapshots": n,
            "lookback_is_retrieval_heuristic_not_market_rule": True,
            "fallback_if_no_windowed_reanchor": "return disagreement-only candidates for visual/user-semantic review",
            "max_cases": args.max_cases,
        },
        "candidate_count_before_sampling": len(candidates),
        "tier_a_windowed_reanchor_count": len(tier_a),
        "selected_case_count": len(cases),
        "cases": cases,
        "guardrails": [
            "Backward-window retrieval is not semantic sequence detection.",
            "The lookback length is a search heuristic, not an NVT market-rule threshold.",
            "Do not infer the small-Dow or mid-Dow HL levels from this proxy alone.",
            "Do not infer the red-circle structural-high breakout from this proxy alone.",
            "Do not invent numeric breakout/reaction tolerances.",
            "Do not change frozen NVT7 or Production from this output.",
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
        "tier_a_windowed_reanchor_count": len(tier_a),
        "selected_case_count": len(cases),
        "output": str(out),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
