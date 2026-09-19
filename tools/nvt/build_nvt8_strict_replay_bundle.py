from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from live_draw.geometry import build_channel_candidates, select_large_mid
from live_draw.market_input import load_ohlc_csv
from live_draw.turn_detector import detect_turns

FROZEN_PATHS = [
    "tools/live_draw",
    "tools/nvt/structure_semantics.py",
    "tools/nvt/build_nvt7_1_semantic_freeze_candidate.py",
    "tools/nvt/run_nvt7_frozen_scope_regression.py",
]


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def safe_symbol(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", value.strip())


def parse_cutoff(value: str) -> datetime:
    return datetime.fromisoformat(value)


def pivot_dict(p):
    return {
        "kind": p.kind,
        "time": p.time.isoformat(),
        "price": p.price,
        "confirmed_by_time": p.confirmed_by_time.isoformat(),
        "retracement": p.retracement,
    }


def candidate_dict(c, large_id, mid_id):
    return {
        "candidate_id": c.id_key,
        "direction": c.direction,
        "anchor1": pivot_dict(c.anchor1),
        "anchor2": pivot_dict(c.anchor2),
        "ch_anchor": pivot_dict(c.ch_anchor),
        "slope_per_second": c.slope_per_second,
        "turn_span": c.turn_span,
        "tl_contacts": c.tl_contacts,
        "ch_contacts": c.ch_contacts,
        "unbroken_close": c.unbroken_close,
        "ch_offset": c.ch_offset,
        "zone_width": c.zone_width,
        "selected_as_large": c.id_key == large_id,
        "selected_as_mid": c.id_key == mid_id,
    }


def git_changed_frozen_paths(repo: Path, frozen_head: str) -> list[str]:
    cmd = ["git", "-C", str(repo), "diff", "--name-only", f"{frozen_head}..HEAD", "--", *FROZEN_PATHS]
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    return [line.strip() for line in out.splitlines() if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build strict NVT8 time-frozen replay bundle from fresh MT4 deep-history export.")
    ap.add_argument("--registry", required=True)
    ap.add_argument("--inspection-lock", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--broker-symbol", default="USDJPY#")
    args = ap.parse_args()

    registry = load_json(args.registry)
    lock = load_json(args.inspection_lock)
    repo = Path(args.repo)
    input_dir = Path(args.input_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if registry.get("schema") != "nvt8-teacher-event-registry/1.0":
        raise ValueError("unexpected teacher event registry schema")
    if registry.get("status") != "FROZEN_AFTER_HELD_OUT_REVIEW":
        raise ValueError("teacher event registry is not frozen")
    if lock.get("status") != "LOCKED_BEFORE_TEACHER_CONTENT_DECODE":
        raise ValueError("inspection lock missing/invalid")
    if registry.get("source_id") != lock.get("source_id"):
        raise ValueError("source_id mismatch between registry and lock")
    if registry.get("rule_tuning_after_teacher_review_allowed") is not False:
        raise ValueError("registry does not preserve no-tuning rule")

    frozen_head = lock.get("frozen_nvt_git_head")
    changed = git_changed_frozen_paths(repo, frozen_head)
    if changed:
        payload = {
            "schema": "nvt8-strict-replay-bundle/1.0",
            "status": "BLOCKED_FROZEN_ALGORITHM_CHANGED_AFTER_INSPECTION_LOCK",
            "source_id": registry.get("source_id"),
            "frozen_nvt_git_head": frozen_head,
            "changed_frozen_paths": changed,
            "production_writeback": False,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    cutoff_text = registry["market_cutoff_policy"]["requested_cutoff_broker_time"]
    cutoff = parse_cutoff(cutoff_text)
    broker_symbol = args.broker_symbol
    safe = safe_symbol(broker_symbol)
    timeframes = ["D1", "H4", "H1"]
    stale = []
    tf_payload = {}

    for tf in timeframes:
        src = input_dir / f"NVT_{safe}_{tf}.csv"
        if not src.exists():
            stale.append({"timeframe": tf, "reason": "MISSING_EXPORT", "path": str(src)})
            continue
        bars = load_ohlc_csv(src)
        frozen = [b for b in bars if b.time <= cutoff]
        if len(frozen) < 3:
            stale.append({"timeframe": tf, "reason": "INSUFFICIENT_BARS_AT_CUTOFF", "path": str(src)})
            continue

        effective = frozen[-1].time
        if effective.date().isoformat() < "2026-09-18":
            stale.append({
                "timeframe": tf,
                "reason": "STALE_EXPORT_BEFORE_HELD_OUT_WEEK",
                "effective_last_closed_bar": effective.isoformat(),
                "required_date_at_least": "2026-09-18",
            })
            continue

        turns = detect_turns(frozen)
        candidates = build_channel_candidates(frozen, turns.pivots)
        large, mid, classifier = select_large_mid(broker_symbol, tf, candidates)
        large_id = large.candidate.id_key if large else None
        mid_id = mid.candidate.id_key if mid else None

        recent_pivots = [pivot_dict(p) for p in turns.pivots if p.time >= datetime(2026, 8, 20)]
        recent_candidates = [
            candidate_dict(c, large_id, mid_id)
            for c in candidates
            if max(c.anchor1.time, c.anchor2.time, c.ch_anchor.time) >= datetime(2026, 8, 20)
        ]

        tf_payload[tf] = {
            "source_csv": str(src),
            "requested_cutoff": cutoff_text,
            "effective_last_closed_bar": effective.isoformat(),
            "first_bar": frozen[0].time.isoformat(),
            "frozen_bar_count": len(frozen),
            "excluded_future_bar_count": sum(1 for b in bars if b.time > cutoff),
            "look_ahead_guard": "PASS",
            "detector": {
                "version": turns.detector_version,
                "status": turns.status,
                "confirmed_turn_count": len(turns.pivots),
                "active_leg": turns.active_leg,
                "active_threshold": turns.active_threshold,
            },
            "candidate_count": len(candidates),
            "selected_large_candidate_id": large_id,
            "selected_mid_candidate_id": mid_id,
            "classifier_audit": classifier,
            "recent_pivots_since_2026_08_20": recent_pivots,
            "recent_candidates_since_2026_08_20": recent_candidates,
        }

    status = "REPLAY_BUNDLE_READY_FOR_HELDOUT_COMPARISON" if not stale and len(tf_payload) == 3 else "WAITING_FOR_FRESH_MT4_HISTORY_EXPORT"
    payload = {
        "schema": "nvt8-strict-replay-bundle/1.0",
        "status": status,
        "source_id": registry.get("source_id"),
        "teacher_event_registry_status": registry.get("status"),
        "teacher_scored_event_ids": registry.get("scored_event_ids"),
        "frozen_nvt_git_head": frozen_head,
        "current_git_head": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
        "frozen_algorithm_paths_unchanged": True,
        "frozen_algorithm_path_diff": [],
        "requested_cutoff_broker_time": cutoff_text,
        "broker_symbol": broker_symbol,
        "timeframes": tf_payload,
        "stale_or_missing": stale,
        "strict_teacher_comparison_executed": False,
        "rule_tuning_after_teacher_review_allowed": False,
        "production_promotion_ready": False,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": status,
        "output": str(out_path),
        "frozen_algorithm_paths_unchanged": True,
        "timeframes_ready": sorted(tf_payload),
        "stale_or_missing_count": len(stale),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0 if status == "REPLAY_BUNDLE_READY_FOR_HELDOUT_COMPARISON" else 3


if __name__ == "__main__":
    raise SystemExit(main())
