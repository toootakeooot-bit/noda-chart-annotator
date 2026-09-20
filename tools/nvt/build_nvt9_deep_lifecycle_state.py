from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.geometry import build_channel_candidates, select_large_mid
from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import TFS, merge_rebuilt_states, rebuild_timeframe_from_csv, safe_symbol_filename
from live_draw.turn_detector import detect_turns

LEVELS = ("LARGE_DOW", "MID_DOW")


def geom_state(item: dict | None) -> dict | None:
    if item is None:
        return None
    return {
        "direction": item.get("direction"),
        "anchor1_time": item.get("anchor1_time"),
        "anchor1_price": float(item.get("anchor1_price")),
        "anchor2_time": item.get("anchor2_time"),
        "anchor2_price": float(item.get("anchor2_price")),
        "ch_offset": float(item.get("ch_offset")),
        "zone_width": float(item.get("zone_width")),
    }


def geom_selected(selected) -> dict | None:
    if selected is None:
        return None
    c = selected.candidate
    return {
        "direction": c.direction,
        "anchor1_time": c.anchor1.time.isoformat(),
        "anchor1_price": float(c.anchor1.price),
        "anchor2_time": c.anchor2.time.isoformat(),
        "anchor2_price": float(c.anchor2.price),
        "ch_offset": float(c.ch_offset),
        "zone_width": float(c.zone_width),
    }


def same_geom(a: dict | None, b: dict | None, tol: float = 1e-10) -> tuple[bool, list[str]]:
    if a is None or b is None:
        return a is None and b is None, ([] if a is None and b is None else ["presence"])
    diffs = []
    for k in ("direction", "anchor1_time", "anchor2_time"):
        if a.get(k) != b.get(k):
            diffs.append(k)
    for k in ("anchor1_price", "anchor2_price", "ch_offset", "zone_width"):
        if not math.isclose(float(a.get(k)), float(b.get(k)), rel_tol=0.0, abs_tol=tol):
            diffs.append(k)
    return not diffs, diffs


def annotate_roles(state: dict) -> dict:
    out = json.loads(json.dumps(state))
    for slot in out.get("slots", {}).values():
        for role in ("current", "previous"):
            item = slot.get(role)
            if item:
                item["generation_role"] = role.upper()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build deep NVT lifecycle state (CURRENT + PREVIOUS) for NVT9 ownership research."
    )
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    symbol = args.symbol.strip()
    safe = safe_symbol_filename(symbol)
    input_dir = Path(args.input_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    rebuilt_states = []
    tf_audits = {}
    direct_checks = []
    missing = []

    for tf in TFS:
        src = input_dir / f"NVT_{safe}_{tf}.csv"
        print(f"[deep-lifecycle] {tf}: start {src.name}", flush=True)
        if not src.exists():
            missing.append(str(src))
            continue

        state, audit = rebuild_timeframe_from_csv(src, symbol, tf)
        rebuilt_states.append(state)
        tf_audits[tf] = audit
        print(
            f"[deep-lifecycle] {tf}: lifecycle PASS "
            f"bars={audit.get('closed_bars')} "
            f"events={audit.get('structural_event_count')} "
            f"prefixes={audit.get('evaluated_prefixes')} "
            f"transitions={audit.get('transition_count')}",
            flush=True,
        )

        print(f"[deep-lifecycle] {tf}: direct full-history verification start", flush=True)
        bars = load_ohlc_csv(src)
        turns = detect_turns(bars)
        candidates = build_channel_candidates(bars, turns.pivots)
        large, mid, classifier = select_large_mid(symbol, tf, candidates)
        direct = {"LARGE_DOW": large, "MID_DOW": mid}
        print(
            f"[deep-lifecycle] {tf}: direct verification "
            f"turns={len(turns.pivots)} candidates={len(candidates)}",
            flush=True,
        )

        for level in LEVELS:
            slot = state.get("slots", {}).get(f"{symbol}|{tf}|{level}", {})
            current = slot.get("current")
            same, diffs = same_geom(geom_state(current), geom_selected(direct[level]))
            direct_checks.append({
                "timeframe": tf,
                "structure_level": level,
                "same_current_as_direct_full_history": same,
                "differences": diffs,
                "lifecycle_current_line_id": current.get("line_id") if current else None,
                "lifecycle_current": geom_state(current),
                "direct_full_history_current": geom_selected(direct[level]),
                "direct_candidate_count": len(candidates),
                "direct_confirmed_turn_count": len(turns.pivots),
                "classifier": classifier,
            })

    if missing:
        status = "FAIL_INPUT_MISSING"
        merged = {"schema": "nca-live-state/1.0", "slots": {}}
    else:
        merged = annotate_roles(merge_rebuilt_states(rebuilt_states))
        mismatch = [x for x in direct_checks if not x["same_current_as_direct_full_history"]]
        status = "PASS_DEEP_LIFECYCLE_STATE" if not mismatch else "BLOCKED_LIFECYCLE_CURRENT_MISMATCH"

    mismatch_count = sum(1 for x in direct_checks if not x["same_current_as_direct_full_history"])

    payload = {
        **merged,
        "research_schema": "nvt9-deep-lifecycle-state/0.1",
        "research_status": status,
        "audit_id": "ID10IQ200",
        "symbol": symbol,
        "source": "NVT_DEEP_HISTORY",
        "current_previous_semantics": "FULL_HISTORY_LIFECYCLE_REBUILD",
        "production_writeback": False,
        "snapshot_writeback": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }
    audit_payload = {
        "schema": "nvt9-deep-lifecycle-audit/0.1",
        "status": status,
        "audit_id": "ID10IQ200",
        "symbol": symbol,
        "missing_inputs": missing,
        "current_direct_check_count": len(direct_checks),
        "current_direct_mismatch_count": mismatch_count,
        "current_direct_checks": direct_checks,
        "timeframe_lifecycle_audits": tf_audits,
        "production_changed": False,
        "renderer_changed": False,
        "snapshot_changed": False,
        "nca_draw_writeback": False,
    }

    state_path = outdir / "NVT9_USDJPY_DEEP_LIFECYCLE_STATE_0919.json"
    audit_path = outdir / "NVT9_USDJPY_DEEP_LIFECYCLE_AUDIT_0919.json"
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_path.write_text(json.dumps(audit_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": status,
        "current_direct_mismatch_count": mismatch_count,
        "state": str(state_path),
        "audit": str(audit_path),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if status == "PASS_DEEP_LIFECYCLE_STATE" else 5


if __name__ == "__main__":
    raise SystemExit(main())
