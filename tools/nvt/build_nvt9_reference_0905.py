from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.market_input import load_ohlc_csv, write_ohlc_csv
from live_draw.normal_run import (
    TFS,
    merge_rebuilt_states,
    rebuild_timeframe_baseline_0919_from_bars,
    rebuild_timeframe_from_bars,
    safe_symbol_filename,
    validate_rebuilt_state,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def input_name(symbol: str, tf: str) -> str:
    return f"NVT_{safe_symbol_filename(symbol)}_{tf}.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build no-lookahead 09/05 current audit package using 600-bar production horizon")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--reference-manifest", required=True)
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--cutoff", default="2026-09-05T00:00:00")
    args = ap.parse_args()

    cutoff = datetime.fromisoformat(args.cutoff)
    input_dir = Path(args.input_dir)
    outdir = Path(args.output_dir)
    policy = Path(args.policy)
    case_input = outdir / "input"
    transition_warmup_input = outdir / "transition_warmup_input"
    base_out = outdir / "base"
    case_input.mkdir(parents=True, exist_ok=True)
    transition_warmup_input.mkdir(parents=True, exist_ok=True)
    base_out.mkdir(parents=True, exist_ok=True)

    states = []
    transition_history_states = []
    transition_history_audits = {}
    coverage = {}
    traces = {}

    for tf in TFS:
        src = input_dir / input_name(args.symbol, tf)
        if not src.exists():
            raise ValueError(f"missing input: {src}")
        all_bars = load_ohlc_csv(src)
        eligible = [b for b in all_bars if b.time < cutoff]
        if len(eligible) < 3:
            raise ValueError(f"{tf}: insufficient bars before {cutoff.isoformat()}")
        bars = eligible[-600:] if len(eligible) >= 600 else eligible

        dst = case_input / input_name(args.symbol, tf)
        write_ohlc_csv(dst, bars)

        # Pre-cutoff-only detector warmup.  This file may include bars before
        # the 600-bar selection window, but the preview transition resolver is
        # required to reject any candidate whose A1/A2/Decision-HL predates
        # the 600-bar selection floor.
        warmup_dst = transition_warmup_input / input_name(args.symbol, tf)
        write_ohlc_csv(warmup_dst, eligible)

        state, audit = rebuild_timeframe_baseline_0919_from_bars(
            bars, args.symbol, tf, include_selector_trace=True
        )
        traces[tf] = audit.get("final_selector_audit")
        states.append(state)

        # Transition ownership must distinguish "no new TL in the current
        # 600-bar selection window" from "no valid lifecycle reference
        # existed at all".  Rebuild only H4/H1 chronologically from all
        # pre-cutoff bars so already-established lines can survive beyond the
        # rolling selection horizon.  No post-cutoff bar is present.
        if tf in {"H4", "H1"}:
            hist_state, hist_audit = rebuild_timeframe_from_bars(
                eligible, args.symbol, tf
            )
            transition_history_states.append(hist_state)
            transition_history_audits[tf] = {
                "status": hist_audit.get("status"),
                "mode": hist_audit.get("mode"),
                "closed_bars": hist_audit.get("closed_bars"),
                "transition_count": hist_audit.get("transition_count"),
                "last_structural_event_time": hist_audit.get("last_structural_event_time"),
                "full_history_detector": hist_audit.get("full_history_detector"),
                "last_event_geometry": hist_audit.get("last_event_geometry"),
                "first_bar": eligible[0].time.isoformat(),
                "last_bar": eligible[-1].time.isoformat(),
                "cutoff_exclusive": cutoff.isoformat(),
                "future_bars_used": False,
            }
        coverage[tf] = {
            "bar_count": len(bars),
            "first_bar": bars[0].time.isoformat(),
            "last_bar": bars[-1].time.isoformat(),
            "cutoff_exclusive": cutoff.isoformat(),
            "window_policy": "LAST_600_CLOSED_BARS_PER_TIMEFRAME",
            "transition_warmup_bar_count": len(eligible),
            "transition_warmup_first_bar": eligible[0].time.isoformat(),
            "transition_warmup_last_bar": eligible[-1].time.isoformat(),
            "transition_warmup_future_bars_used": False,
            "transition_warmup_selection_rule": "DETECTOR_INITIALIZATION_ONLY_CANDIDATE_ANCHORS_RESTRICTED_TO_600_BAR_WINDOW",
        }

    merged = merge_rebuilt_states(states)
    validation = validate_rebuilt_state(merged, args.symbol)
    state_path = outdir / "state.json"
    write_json(state_path, merged)

    transition_history_state = merge_rebuilt_states(transition_history_states)
    transition_history_state_path = outdir / "transition_history_state.json"
    write_json(transition_history_state_path, transition_history_state)
    write_json(
        outdir / "transition_history_audit.json",
        {
            "schema": "nvt9-0905-transition-history/1.0",
            "audit_id": "ID10IQ200",
            "cutoff_exclusive": cutoff.isoformat(),
            "future_bars_used": False,
            "purpose": "RETAIN_PREVIOUSLY_ESTABLISHED_TL_STATE_BEYOND_600_BAR_SELECTION_HORIZON",
            "timeframes": transition_history_audits,
        },
    )
    write_json(outdir / "selector_trace.json", {
        "schema": "nvt9-0905-current-selector-trace/1.0",
        "audit_id": "ID10IQ200",
        "cutoff_exclusive": cutoff.isoformat(),
        "symbol": args.symbol,
        "timeframes": traces,
    })

    cmd = [
        sys.executable,
        str(ROOT / "tools" / "nvt" / "build_nvt9_tf_mapped_preview.py"),
        "--state", str(state_path),
        "--policy", str(policy),
        "--input-dir", str(case_input),
        "--input-prefix", "NVT",
        "--transition-warmup-input-dir", str(transition_warmup_input),
        "--transition-history-state", str(transition_history_state_path),
        "--output-dir", str(base_out),
        "--fallback-previous-source-tf", "H4",
        "--fallback-previous-source-tf", "H1",
        "--fallback-reference-source-tf", "H4",
        "--fallback-reference-source-tf", "H1",
        "--fallback-reference-manifest", str(Path(args.reference_manifest)),
        "--allow-empty-source-tf", "H4",
        "--allow-empty-source-tf", "H1",
        "--main-roles-only-source-tf", "D1",
        "--main-roles-only-source-tf", "H4",
        "--main-roles-only-source-tf", "H1",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"preview failed exit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

    summary = {
        "schema": "nvt9-0905-current-package/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_0905_CURRENT_600BAR_BASE",
        "symbol": args.symbol,
        "cutoff_exclusive": cutoff.isoformat(),
        "window_policy": "LAST_600_CLOSED_BARS_PER_TIMEFRAME",
        "future_bars_used": False,
        "transition_warmup_policy": "PRE_CUTOFF_DETECTOR_INITIALIZATION_ONLY_IF_600_BAR_TRANSITION_PASS_HAS_ZERO_CANDIDATES",
        "transition_warmup_candidate_floor": "FIRST_BAR_OF_EACH_600_BAR_SELECTION_WINDOW",
        "transition_warmup_future_bars_used": False,
        "transition_history_policy": "FULL_PRE_CUTOFF_CHRONOLOGICAL_REPLAY_FOR_RETAINED_STATE_ONLY",
        "transition_history_future_bars_used": False,
        "transition_history_state_json": str(transition_history_state_path),
        "transition_history_audit_json": str(outdir / "transition_history_audit.json"),
        "allowed_empty_source_tfs": ["H4", "H1"],
        "fallback_previous_source_tfs": ["H4", "H1"],
        "fallback_reference_source_tfs": ["H4", "H1"],
        "fallback_reference_manifest": str(Path(args.reference_manifest)),
        "main_roles_only_source_tfs": ["D1", "H4", "H1"],
        "m15_native_selector_enabled": False,
        "m15_structural_owner": "H1",
        "m15_display_policy": "COPY_EXACT_H1_SELECTED_GEOMETRY_NO_RESELECTION",
        "suppressed_source_directions": {},
        "empty_source_policy": "ALLOW_H4_H1_NO_LINE_IF_CURRENT_PREVIOUS_AND_PRE_CUTOFF_REVALIDATED_REFERENCE_ARE_ALL_ABSENT",
        "retained_reference_policy": "H4_H1_CURRENT_THEN_PREVIOUS_THEN_FROZEN_REFERENCE_REVALIDATED_PRE_CUTOFF",
        "source_suppression_policy": "NO_0905_DATE_SPECIFIC_SUPPRESSION_BEFORE_VISUAL_ADJUDICATION",
        "production_changed": False,
        "state_validation": validation,
        "input_coverage": coverage,
        "state_json": str(state_path),
        "selector_trace_json": str(outdir / "selector_trace.json"),
        "base_preview_csv": str(base_out / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"),
    }
    write_json(outdir / "NVT9_0905_CURRENT_SUMMARY.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
