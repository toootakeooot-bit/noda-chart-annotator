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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def cand_direction(summary: dict, key: str):
    c = summary.get(key)
    return c.get("direction") if c else None


def cand_id(summary: dict, key: str):
    c = summary.get(key)
    return c.get("candidate_id") if c else None


def cand_slope(summary: dict, key: str):
    c = summary.get(key)
    return c.get("slope_per_second") if c else None


def classify_patterns(cur: dict, prev: dict | None):
    patterns = []
    evidence = {}

    h1 = cur["H1"]
    h4 = cur["H4"]
    d1 = cur["D1"]

    h1_large_dir = cand_direction(h1, "baseline_large")
    h1_mid_dir = cand_direction(h1, "baseline_mid")

    if (
        h1.get("active_leg") == "FALLING"
        and h1_large_dir == "RISING"
        and h1_mid_dir == "RISING"
    ):
        patterns.append("BREAK_NOT_DIRECTION_FLIP_CANDIDATE")
        evidence["break_not_flip"] = {
            "h1_active_leg": h1.get("active_leg"),
            "h1_large_direction": h1_large_dir,
            "h1_mid_direction": h1_mid_dir,
        }

    if prev is not None:
        changes = []
        for key in ("baseline_large", "baseline_mid"):
            old_id = cand_id(prev["H1"], key)
            new_id = cand_id(h1, key)
            old_dir = cand_direction(prev["H1"], key)
            new_dir = cand_direction(h1, key)
            if old_id and new_id and old_id != new_id and old_dir == new_dir:
                old_slope = cand_slope(prev["H1"], key)
                new_slope = cand_slope(h1, key)
                slope_relation = None
                if old_slope is not None and new_slope is not None:
                    if abs(new_slope) < abs(old_slope):
                        slope_relation = "NEW_GENTLER"
                    elif abs(new_slope) > abs(old_slope):
                        slope_relation = "NEW_STEEPER"
                    else:
                        slope_relation = "SAME_ABS_SLOPE"
                changes.append({
                    "layer": key,
                    "old_id": old_id,
                    "new_id": new_id,
                    "direction": new_dir,
                    "old_slope_per_second": old_slope,
                    "new_slope_per_second": new_slope,
                    "slope_relation": slope_relation,
                })
        if changes:
            patterns.append("REFERENCE_REANCHOR_RETIRE_REVIEW_CANDIDATE")
            evidence["reanchor_retire"] = {"changes": changes}

    if (
        h1.get("active_leg") == "FALLING"
        and h4.get("active_leg") == "FALLING"
        and cand_direction(d1, "baseline_large") == "RISING"
    ):
        patterns.append("DECISION_OWNER_ESCALATION_CANDIDATE")
        evidence["decision_owner"] = {
            "h1_active_leg": h1.get("active_leg"),
            "h4_active_leg": h4.get("active_leg"),
            "d1_active_leg": d1.get("active_leg"),
            "d1_large_direction": cand_direction(d1, "baseline_large"),
            "d1_mid_direction": cand_direction(d1, "baseline_mid"),
        }

    return patterns, evidence


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
        description="Build NVT7.1 Batch02 targeted USDJPY historical cases for ChatGPT-first review."
    )
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--prior-bundle", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--per-pattern", type=int, default=4)
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    prior_path = Path(args.prior_bundle)
    prior = load_json(prior_path)
    if prior.get("schema") != "nvt8h-usdjpy-historical-review-bundle/0.2":
        raise ValueError("unexpected prior historical bundle schema")

    prior_cutoffs = {c.get("cutoff") for c in prior.get("cases") or []}

    paths = {tf: resolve_csv(input_dir, tf) for tf in WINDOWS}
    all_bars = {tf: load_ohlc_csv(path) for tf, path in paths.items()}
    cutoffs = eligible_cutoffs(all_bars)

    snapshots = []
    previous = None
    for cutoff in cutoffs:
        cur = {tf: summary_at(args.symbol, tf, all_bars[tf], cutoff) for tf in CORE_TIMEFRAMES}
        patterns, pattern_evidence = classify_patterns(cur, previous["summaries"] if previous else None)
        row = {
            "cutoff": cutoff,
            "cutoff_iso": cutoff.isoformat(),
            "summaries": cur,
            "target_patterns": patterns,
            "pattern_evidence": pattern_evidence,
            "previous_daily_cutoff": previous["cutoff_iso"] if previous else None,
        }
        snapshots.append(row)
        previous = row

    available = [
        row for row in snapshots
        if row["cutoff_iso"] not in prior_cutoffs and row["target_patterns"]
    ]

    pattern_names = [
        "BREAK_NOT_DIRECTION_FLIP_CANDIDATE",
        "REFERENCE_REANCHOR_RETIRE_REVIEW_CANDIDATE",
        "DECISION_OWNER_ESCALATION_CANDIDATE",
    ]
    selected = []
    seen = set()
    selection_counts = {}
    for pattern in pattern_names:
        bucket = [row for row in available if pattern in row["target_patterns"]]
        chosen = evenly_pick(bucket, max(1, args.per_pattern))
        selection_counts[pattern] = len(chosen)
        for row in chosen:
            if row["cutoff_iso"] not in seen:
                selected.append(row)
                seen.add(row["cutoff_iso"])

    selected.sort(key=lambda x: x["cutoff"])
    if not selected:
        raise ValueError("No targeted NVT7.1 supplemental USDJPY cases found outside Batch01 cutoffs.")

    cases = []
    for i, row in enumerate(selected, 1):
        cutoff = row["cutoff"]
        tf_payload = {
            tf: timeframe_payload(args.symbol, tf, all_bars[tf], cutoff)
            for tf in WINDOWS
        }
        cases.append({
            "case_id": f"USDJPY_NVT71_B02_{i:02d}",
            "cutoff": row["cutoff_iso"],
            "previous_daily_cutoff": row["previous_daily_cutoff"],
            "future_bars_included": False,
            "known_teacher_answer": None,
            "review_mode": "CHATGPT_FIRST_USER_ADJUDICATION_ONLY_WHEN_NEEDED",
            "target_patterns": row["target_patterns"],
            "pattern_evidence": row["pattern_evidence"],
            "timeframes": tf_payload,
            "review_questions": {
                "break_not_direction_flip": None,
                "reference_reanchor_retire": None,
                "decision_owner_escalation": None,
                "notes": None,
            },
        })

    report = {
        "schema": "nvt7.1-usdjpy-targeted-historical-review/0.1",
        "status": "RESEARCH_ONLY_REVIEW_BUNDLE",
        "phase": "NVT7.1_BATCH02_TARGETED_HISTORICAL_REVIEW",
        "symbol_scope": "USDJPY_ONLY",
        "evidence_target": "SUPPLEMENTAL_USER_OPERATIONAL_EVIDENCE",
        "source_prior_bundle": str(prior_path),
        "source_prior_cutoff_count": len(prior_cutoffs),
        "selection_policy": {
            "future_hidden": True,
            "cadence": "daily latest H1 bar",
            "exclude_development_video_window": [DEV_EXCLUDE_START.isoformat(), DEV_EXCLUDE_END.isoformat()],
            "exclude_batch01_cutoffs": True,
            "per_pattern_requested": args.per_pattern,
            "patterns": pattern_names,
            "pattern_selection_counts_before_dedup": selection_counts,
            "generated_unique_case_count": len(cases),
            "no_numeric_thresholds_invented": True,
        },
        "pattern_meaning": {
            "BREAK_NOT_DIRECTION_FLIP_CANDIDATE": "H1 local active leg FALLING while retained H1 Large/Mid structure remains RISING; review whether parent direction should stay unchanged.",
            "REFERENCE_REANCHOR_RETIRE_REVIEW_CANDIDATE": "Sequential daily H1 Large/Mid candidate identity changed without a direction change; review whether this is an interim redraw, broader replacement, retained reference, or retirement situation.",
            "DECISION_OWNER_ESCALATION_CANDIDATE": "H1 and H4 local active legs are FALLING while a rising D1 structural line remains; review whether decision ownership should escalate to D1 while lower-TF lines remain contextual.",
        },
        "review_protocol": [
            "ChatGPT reviews every generated case first.",
            "User is asked only where the three NVT7.1 contracts are genuinely ambiguous or high-impact.",
            "Do not convert mechanical pattern detection into a teacher answer.",
            "Do not tune numeric thresholds during a case; adjudicate first, aggregate later.",
        ],
        "cases": cases,
        "production_promotion_ready": False,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    pattern_case_counts = {
        pattern: sum(1 for case in cases if pattern in case["target_patterns"])
        for pattern in pattern_names
    }
    print(json.dumps({
        "status": "PASS",
        "output": str(out),
        "unique_case_count": len(cases),
        "pattern_case_counts": pattern_case_counts,
        "future_hidden": True,
        "batch01_cutoffs_excluded": True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
