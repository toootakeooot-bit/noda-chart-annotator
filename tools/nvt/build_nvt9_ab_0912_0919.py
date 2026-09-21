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
    rebuild_timeframe_direction_switch_experiment,
    safe_symbol_filename,
    validate_rebuilt_state,
)

CASES = ("2026-09-12", "2026-09-19")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _input_name(symbol: str, tf: str) -> str:
    return f"NVT_{safe_symbol_filename(symbol)}_{tf}.csv"


def _run_preview(state_path: Path, input_dir: Path, policy: Path, outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "nvt" / "build_nvt9_tf_mapped_preview.py"),
        "--state", str(state_path),
        "--policy", str(policy),
        "--input-dir", str(input_dir),
        "--input-prefix", "NVT",
        "--output-dir", str(outdir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"preview failed: exit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    audit_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json"
    return json.loads(audit_path.read_text(encoding="utf-8"))


def _selected_one(audit: dict, tf: str) -> dict:
    rows = audit["source_selection"].get(tf) or []
    if len(rows) != 1:
        raise ValueError(f"{tf}: expected exactly one selected source family, got {len(rows)}")
    return rows[0]


def _compare_tf(old_audit: dict, new_audit: dict, tf: str) -> dict:
    old = _selected_one(old_audit, tf)
    new = _selected_one(new_audit, tf)
    old_hl = old_audit["hl_candidates"][tf]
    new_hl = new_audit["hl_candidates"][tf]

    fields = (
        "direction",
        "anchor1_time",
        "anchor1_price",
        "anchor2_time",
        "anchor2_price",
        "ch_offset",
    )
    detail = {}
    for field in fields:
        ov = old[field]
        nv = new[field]
        same = ov == nv
        if field.endswith("_price") or field == "ch_offset":
            same = abs(float(ov) - float(nv)) <= 1e-10
        detail[field] = {"old": ov, "new": nv, "same": bool(same)}

    hl_detail = {
        "pivot_kind": {
            "old": old_hl["pivot_kind"],
            "new": new_hl["pivot_kind"],
            "same": old_hl["pivot_kind"] == new_hl["pivot_kind"],
        },
        "pivot_time": {
            "old": old_hl["pivot_time"],
            "new": new_hl["pivot_time"],
            "same": old_hl["pivot_time"] == new_hl["pivot_time"],
        },
        "pivot_price": {
            "old": float(old_hl["pivot_price"]),
            "new": float(new_hl["pivot_price"]),
            "same": abs(float(old_hl["pivot_price"]) - float(new_hl["pivot_price"])) <= 1e-10,
        },
    }

    geometry_same = all(x["same"] for x in detail.values())
    hl_same = all(x["same"] for x in hl_detail.values())
    return {
        "timeframe": tf,
        "geometry_same": geometry_same,
        "hl_same": hl_same,
        "all_same": geometry_same and hl_same,
        "geometry": detail,
        "hl": hl_detail,
        "old_line_id": old["line_id"],
        "new_line_id": new["line_id"],
    }


EXPECTED_0919 = ROOT / "nvt" / "manifests" / "NVT9_USDJPY_0919_EXPECTED_LINES_V01.json"
EXPECTED_FIELDS = (
    "line_id", "structure_level", "generation", "status", "direction",
    "anchor1_time", "anchor1_price", "anchor2_time", "anchor2_price",
    "ch_offset", "zone_width", "selection_version",
)


def _current_lines(state: dict, symbol: str) -> dict[str, dict[str, dict]]:
    out = {tf: {} for tf in TFS}
    for slot in state.get("slots", {}).values():
        item = slot.get("current")
        if not item or item.get("symbol") != symbol:
            continue
        tf = item.get("timeframe")
        level = item.get("structure_level")
        if tf in out and level:
            out[tf][level] = item
    return out


def _same_expected_value(field: str, expected, actual) -> bool:
    if field in ("anchor1_price", "anchor2_price", "ch_offset", "zone_width"):
        return abs(float(expected) - float(actual)) <= 1e-10
    if field == "generation":
        return int(expected) == int(actual)
    return expected == actual


def _validate_expected_0919(state: dict, symbol: str) -> dict:
    expected = json.loads(EXPECTED_0919.read_text(encoding="utf-8"))
    actual = _current_lines(state, symbol)
    mismatches = []

    for tf in TFS:
        expected_rows = {
            row["structure_level"]: row
            for row in expected["expected_current_lines"].get(tf, [])
        }
        actual_rows = actual.get(tf, {})
        for level, erow in expected_rows.items():
            arow = actual_rows.get(level)
            if arow is None:
                mismatches.append({"timeframe": tf, "level": level, "field": "presence", "expected": "PRESENT", "actual": "MISSING"})
                continue
            for field in EXPECTED_FIELDS:
                ev = erow.get(field)
                av = arow.get(field)
                if not _same_expected_value(field, ev, av):
                    mismatches.append({"timeframe": tf, "level": level, "field": field, "expected": ev, "actual": av})
        for level in actual_rows:
            if level not in expected_rows:
                mismatches.append({"timeframe": tf, "level": level, "field": "presence", "expected": "ABSENT", "actual": "EXTRA"})

    return {
        "schema": "nvt9-0919-baseline-gate/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS" if not mismatches else "FAIL",
        "expected_manifest": str(EXPECTED_0919),
        "required_line_count": sum(len(v) for v in expected["expected_current_lines"].values()),
        "actual_line_count": sum(len(v) for v in actual.values()),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def _attach_line_ids_to_selector_traces(traces: dict, state: dict, symbol: str) -> dict:
    current = _current_lines(state, symbol)
    for tf, payload in traces.items():
        if not isinstance(payload, dict):
            continue
        trace = payload.get("selector_trace")
        if not isinstance(trace, dict):
            continue
        for level_key, trace_key in (("LARGE_DOW", "large"), ("MID_DOW", "mid")):
            decision = trace.get(trace_key)
            line = current.get(tf, {}).get(level_key)
            if isinstance(decision, dict) and line:
                decision["selected_line_id"] = line.get("line_id")
                decision["selected_generation"] = line.get("generation")
                decision["draw_audit_id"] = f"D-{tf}-{'LARGE' if level_key == 'LARGE_DOW' else 'MID'}"
    return traces


def build_case(*, symbol: str, case_date: str, input_dir: Path, policy: Path, outroot: Path) -> dict:
    cutoff = datetime.fromisoformat(case_date)
    case_root = outroot / case_date.replace("-", "")
    case_input = case_root / "input"
    case_input.mkdir(parents=True, exist_ok=True)

    old_states = []
    new_states = []
    replay_meta = {}
    selector_traces = {}

    for tf in TFS:
        src = input_dir / _input_name(symbol, tf)
        if not src.exists():
            raise ValueError(f"missing deep-history input: {src}")
        all_bars = load_ohlc_csv(src)
        bars = [b for b in all_bars if b.time < cutoff]
        if len(bars) < 3:
            raise ValueError(f"{tf}: insufficient bars before {cutoff.isoformat()}")

        dst = case_input / _input_name(symbol, tf)
        write_ohlc_csv(dst, bars)

        old_state, old_tf_audit = rebuild_timeframe_baseline_0919_from_bars(bars, symbol, tf)
        selector_traces[tf] = old_tf_audit.pop("final_selector_audit", None)
        new_state, new_tf_audit = rebuild_timeframe_direction_switch_experiment(bars, symbol, tf)
        old_states.append(old_state)
        new_states.append(new_state)

        replay_meta[tf] = {
            "bar_count": len(bars),
            "first_bar": bars[0].time.isoformat(),
            "last_bar": bars[-1].time.isoformat(),
            "cutoff_exclusive": cutoff.isoformat(),
            "old": old_tf_audit,
            "new": new_tf_audit,
        }

    old_merged = merge_rebuilt_states(old_states)
    new_merged = merge_rebuilt_states(new_states)
    old_validation = validate_rebuilt_state(old_merged, symbol)
    new_validation = validate_rebuilt_state(new_merged, symbol)

    selector_traces = _attach_line_ids_to_selector_traces(selector_traces, old_merged, symbol)
    selector_trace_path = case_root / "OLD" / "NVT9_SELECTOR_TRACE.json"
    _write_json(selector_trace_path, {
        "schema": "nvt9-selector-trace-bundle/1.0",
        "audit_id": "ID10IQ200",
        "case_date": case_date,
        "cutoff_exclusive": cutoff.isoformat(),
        "symbol": symbol,
        "selection_semantics_changed": False,
        "timeframes": selector_traces,
    })
    expected_0919 = _validate_expected_0919(old_merged, symbol) if case_date == "2026-09-19" else None

    old_state_path = case_root / "OLD" / "state.json"
    new_state_path = case_root / "NEW" / "state.json"
    _write_json(old_state_path, old_merged)
    _write_json(new_state_path, new_merged)

    old_preview_dir = case_root / "OLD" / "output"
    new_preview_dir = case_root / "NEW" / "output"
    old_preview = _run_preview(old_state_path, case_input, policy, old_preview_dir)
    new_preview = _run_preview(new_state_path, case_input, policy, new_preview_dir)

    comparisons = {tf: _compare_tf(old_preview, new_preview, tf) for tf in ("D1", "H4", "H1", "M15")}

    return {
        "schema": "nvt9-ab-case/1.0",
        "audit_id": "ID10IQ200",
        "case_date": case_date,
        "cutoff_exclusive": cutoff.isoformat(),
        "symbol": symbol,
        "old_mode": "FROZEN_0919_BASELINE_EMULATION",
        "new_mode": "DIRECTION_SWITCH_ACTIVE_N_V0_2_REGIME_GATED",
        "candidate_geometry_changed": False,
        "plan_b_changed": False,
        "color_policy_changed": False,
        "old_state_validation": old_validation,
        "new_state_validation": new_validation,
        "replay": replay_meta,
        "comparison": comparisons,
        "all_timeframes_same": all(x["all_same"] for x in comparisons.values()),
        "expected_0919_baseline_gate": expected_0919,
        "selector_trace_json": str(selector_trace_path),
        "old_preview_csv": str(old_preview_dir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"),
        "new_preview_csv": str(new_preview_dir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="NVT9 OLD vs direction-switch ACTIVE-N A/B audit")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--symbol", default="USDJPY#")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    outroot = Path(args.output_dir)
    policy = Path(args.policy)

    results = []
    for case_date in CASES:
        result = build_case(symbol=args.symbol, case_date=case_date, input_dir=input_dir, policy=policy, outroot=outroot)
        _write_json(outroot / case_date.replace("-", "") / "AB_CASE_AUDIT.json", result)
        results.append(result)
        print(f"AB CASE PASS {case_date}: same={result['all_timeframes_same']}", flush=True)

    by_date = {x["case_date"]: x for x in results}
    regression_0919 = by_date["2026-09-19"]["all_timeframes_same"]
    baseline_gate = by_date["2026-09-19"]["expected_0919_baseline_gate"]
    baseline_match = baseline_gate is not None and baseline_gate.get("status") == "PASS"

    summary = {
        "schema": "nvt9-ab-summary/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_AB_BUILD" if baseline_match else "FAIL_0919_BASELINE_MISMATCH",
        "baseline_branch": "baseline/nvt9-0919-approved",
        "baseline_commit": "436a17a74919353351675921c11e3bf080ea07a3",
        "new_mode": "DIRECTION_SWITCH_ACTIVE_N_V0_2_REGIME_GATED",
        "color_policy": "UNCHANGED_FROM_0919",
        "plan_b": "UNCHANGED",
        "cases": {
            x["case_date"]: {
                "all_timeframes_same": x["all_timeframes_same"],
                "comparison": x["comparison"],
                "old_preview_csv": x["old_preview_csv"],
                "new_preview_csv": x["new_preview_csv"],
                "selector_trace_json": x["selector_trace_json"],
                "expected_0919_baseline_gate": x["expected_0919_baseline_gate"],
            }
            for x in results
        },
        "baseline_0919_expected_gate": baseline_gate,
        "regression_0919": {
            "exact_geometry_and_hl_match": regression_0919,
            "decision": "SAFE_TO_VISUALLY_REVIEW_0912_NEW" if regression_0919 else "DO_NOT_PROMOTE_NEW_YET_0919_CHANGED",
        },
    }
    _write_json(outroot / "AB_0912_0919_SUMMARY.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if baseline_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
