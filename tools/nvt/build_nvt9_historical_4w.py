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
    rebuild_timeframe_from_bars,
    safe_symbol_filename,
    validate_rebuilt_state,
)

DEFAULT_CASE_DATES = ("2026-08-22", "2026-08-29", "2026-09-05", "2026-09-12")


def _case_key(case_date: str) -> str:
    return case_date.replace("-", "")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def input_name(symbol: str, tf: str, prefix: str) -> str:
    return f"{prefix}_{safe_symbol_filename(symbol)}_{tf}.csv"


def build_case(*, symbol: str, case_date: str, input_dir: Path, input_prefix: str, history_root: Path, policy: Path, preview_builder: Path) -> dict:
    cutoff = datetime.fromisoformat(case_date)
    safe = safe_symbol_filename(symbol)
    case_key = _case_key(case_date)
    case_root = history_root / case_key
    case_input = case_root / "input"
    case_output = case_root / "output"
    case_input.mkdir(parents=True, exist_ok=True)
    case_output.mkdir(parents=True, exist_ok=True)

    rebuilt_states = []
    tf_meta = {}
    for tf in TFS:
        src = input_dir / input_name(symbol, tf, input_prefix)
        if not src.exists():
            raise ValueError(f"missing source input for {tf}: {src}")
        all_bars = load_ohlc_csv(src)
        bars = [b for b in all_bars if b.time < cutoff]
        if len(bars) < 3:
            raise ValueError(f"insufficient bars before cutoff: tf={tf} cutoff={case_date} bars={len(bars)}")
        if any(b.time >= cutoff for b in bars):
            raise AssertionError(f"future-leak filter failed for {tf}")

        dst = case_input / input_name(symbol, tf, input_prefix)
        write_ohlc_csv(dst, bars)
        tf_state, tf_audit = rebuild_timeframe_from_bars(bars, symbol, tf)
        rebuilt_states.append(tf_state)
        tf_meta[tf] = {
            "source_file": str(src),
            "replay_input": str(dst),
            "bar_count": len(bars),
            "first_bar_time": bars[0].time.isoformat(),
            "last_bar_time": bars[-1].time.isoformat(),
            "cutoff_exclusive": cutoff.isoformat(),
            "no_future_leak": bars[-1].time < cutoff,
            "structural_event_count": tf_audit["structural_event_count"],
            "transition_count": tf_audit["transition_count"],
        }

    merged = merge_rebuilt_states(rebuilt_states)
    validation = validate_rebuilt_state(merged, symbol)
    state_path = case_output / f"NORMAL_{safe}_live_state.json"
    _write_json(state_path, merged)

    cmd = [
        sys.executable, str(preview_builder),
        "--state", str(state_path),
        "--policy", str(policy),
        "--input-dir", str(case_input),
        "--input-prefix", input_prefix,
        "--output-dir", str(case_output),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"preview build failed for {case_date}: exit={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

    preview_audit_path = case_output / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json"
    preview_csv_path = case_output / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"
    preview_audit = json.loads(preview_audit_path.read_text(encoding="utf-8"))
    leak_problems = []
    for tf, info in preview_audit.get("latest_display_prices", {}).items():
        t = datetime.fromisoformat(info["time"])
        if t >= cutoff:
            leak_problems.append({"timeframe": tf, "latest_display_time": t.isoformat(), "cutoff": cutoff.isoformat()})
    if leak_problems:
        raise ValueError(f"historical preview future leakage: {leak_problems}")

    case_audit = {
        "schema": "nvt9-historical-replay-case/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_NO_FUTURE_LEAK",
        "symbol": symbol,
        "source_input_prefix": input_prefix,
        "case_label": case_date,
        "cutoff_exclusive": cutoff.isoformat(),
        "effective_market_point": "last available MT4 bar strictly before cutoff",
        "timeframes": tf_meta,
        "state_validation": validation,
        "preview_status": preview_audit.get("status"),
        "preview_csv": str(preview_csv_path),
        "preview_audit": str(preview_audit_path),
        "baseline_commit": "436a17a74919353351675921c11e3bf080ea07a3",
        "baseline_branch": "baseline/nvt9-0919-approved",
        "future_data_used": False,
    }
    _write_json(case_root / "CASE_AUDIT.json", case_audit)
    return case_audit


def main() -> int:
    ap = argparse.ArgumentParser(description="Build four no-lookahead NVT9 historical replay cases before the 2026-09-19 baseline.")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--input-prefix", default="NVT", choices=["NVT", "NORMAL"])
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--case-date", action="append", dest="case_dates")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    history_root = Path(args.output_dir)
    policy = Path(args.policy)
    preview_builder = ROOT / "tools" / "nvt" / "build_nvt9_tf_mapped_preview.py"
    case_dates = tuple(args.case_dates or DEFAULT_CASE_DATES)

    # Preflight: the short NormalRun export is intentionally not suitable for
    # multi-week replay. NVT deep-history input should reach before the oldest
    # case cutoff on every timeframe.
    oldest_cutoff = datetime.fromisoformat(min(case_dates))
    preflight = []
    for tf in TFS:
        src = input_dir / input_name(args.symbol, tf, args.input_prefix)
        if not src.exists():
            preflight.append({"timeframe": tf, "problem": "FILE_MISSING", "path": str(src)})
            continue
        bars = load_ohlc_csv(src)
        older = [b for b in bars if b.time < oldest_cutoff]
        if len(older) < 3:
            first = bars[0].time.isoformat() if bars else None
            last = bars[-1].time.isoformat() if bars else None
            preflight.append({
                "timeframe": tf,
                "problem": "INSUFFICIENT_HISTORY_BEFORE_OLDEST_CASE",
                "path": str(src),
                "first_bar": first,
                "last_bar": last,
                "bars_before_cutoff": len(older),
                "required_cutoff": oldest_cutoff.isoformat(),
            })
    if preflight:
        print(json.dumps({
            "status": "STOP_DEEP_HISTORY_REQUIRED",
            "message": (
                "Historical replay needs deep NVT history. "
                "Run NCA_NVT_HistoryExporter in MT4 once (BarsToExport=6000 or more), "
                "then rerun PREPARE_NVT9_HISTORY_AUDIT.cmd."
            ),
            "input_prefix": args.input_prefix,
            "input_dir": str(input_dir),
            "problems": preflight,
        }, ensure_ascii=False, indent=2))
        return 4

    results = []
    for case_date in case_dates:
        try:
            result = build_case(
                symbol=args.symbol,
                case_date=case_date,
                input_dir=input_dir,
                input_prefix=args.input_prefix,
                history_root=history_root,
                policy=policy,
                preview_builder=preview_builder,
            )
        except Exception as exc:
            print(json.dumps({
                "status": "HISTORY_CASE_BUILD_FAILED",
                "case_date": case_date,
                "error": str(exc),
            }, ensure_ascii=False, indent=2))
            return 5
        results.append(result)
        print(f"HISTORY CASE PASS: {case_date}", flush=True)

    summary = {
        "schema": "nvt9-historical-replay-summary/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_4W_NO_FUTURE_LEAK",
        "symbol": args.symbol,
        "source_input_prefix": args.input_prefix,
        "cases": [{"case_label": x["case_label"], "cutoff_exclusive": x["cutoff_exclusive"], "status": x["status"], "preview_csv": x["preview_csv"]} for x in results],
        "baseline_branch": "baseline/nvt9-0919-approved",
        "baseline_commit": "436a17a74919353351675921c11e3bf080ea07a3",
    }
    _write_json(history_root / "HISTORY_4W_SUMMARY.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
