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
from live_draw.normal_run import TFS, normal_input_name
from live_draw.turn_detector import detect_turns

LEVELS = ("LARGE_DOW", "MID_DOW")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def geometry_from_state(item: dict | None) -> dict | None:
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


def geometry_from_selected(selected) -> dict | None:
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
        "candidate_id": c.id_key,
        "selection_version": selected.selection_version,
    }


def compare_geometry(a: dict | None, b: dict | None, tol: float = 1e-10) -> tuple[bool, list[str]]:
    if a is None or b is None:
        return a is None and b is None, ([] if a is None and b is None else ["presence"])
    diffs: list[str] = []
    for k in ("direction", "anchor1_time", "anchor2_time"):
        if a.get(k) != b.get(k):
            diffs.append(k)
    for k in ("anchor1_price", "anchor2_price", "ch_offset", "zone_width"):
        try:
            same = math.isclose(float(a.get(k)), float(b.get(k)), rel_tol=0.0, abs_tol=tol)
        except Exception:
            same = False
        if not same:
            diffs.append(k)
    return not diffs, diffs


def research_line_state(symbol: str, tf: str, level: str, selected) -> dict | None:
    if selected is None:
        return None
    c = selected.candidate
    return {
        "line_id": f"NVT9_RESEARCH_{symbol}_{tf}_{level}_FULL_HISTORY",
        "symbol": symbol,
        "timeframe": tf,
        "structure_level": level,
        "generation": 0,
        "status": "ACTIVE",
        "direction": c.direction,
        "anchor1_time": c.anchor1.time.isoformat(),
        "anchor1_price": float(c.anchor1.price),
        "anchor2_time": c.anchor2.time.isoformat(),
        "anchor2_price": float(c.anchor2.price),
        "ch_offset": float(c.ch_offset),
        "zone_width": float(c.zone_width),
        "selection_version": selected.selection_version,
        "created_at": "RESEARCH_ONLY_FULL_HISTORY_SELECTOR",
        "replaced_at": None,
        "replacement_line_id": None,
        "research_candidate_id": c.id_key,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compare published Normal Run current geometry with direct full-history selector output."
    )
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--state", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    symbol = args.symbol.strip()
    state_path = Path(args.state)
    input_dir = Path(args.input_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    if not state_path.exists():
        print(json.dumps({"status": "FAIL", "reason": "state_not_found", "path": str(state_path)}, ensure_ascii=False))
        return 2

    live_state = load_json(state_path)
    audit_rows = []
    research_slots = {}
    missing_inputs = []
    mismatch_count = 0

    for tf in TFS:
        src = input_dir / normal_input_name(symbol, tf)
        if not src.exists():
            missing_inputs.append(str(src))
            continue

        bars = load_ohlc_csv(src)
        turns = detect_turns(bars)
        candidates = build_channel_candidates(bars, turns.pivots)
        large, mid, classifier = select_large_mid(symbol, tf, candidates)
        selected_by_level = {"LARGE_DOW": large, "MID_DOW": mid}

        for level in LEVELS:
            selected = selected_by_level[level]
            direct_geom = geometry_from_selected(selected)
            slot_key = f"{symbol}|{tf}|{level}"
            live_slot = live_state.get("slots", {}).get(slot_key, {})
            live_current = live_slot.get("current")
            live_geom = geometry_from_state(live_current)
            same, diffs = compare_geometry(live_geom, direct_geom)
            if not same:
                mismatch_count += 1

            audit_rows.append({
                "timeframe": tf,
                "structure_level": level,
                "same_geometry": same,
                "differences": diffs,
                "live_current_line_id": live_current.get("line_id") if live_current else None,
                "live_current": live_geom,
                "full_history_current": direct_geom,
                "full_history_candidate_count": len(candidates),
                "full_history_confirmed_turn_count": len(turns.pivots),
                "classifier": classifier,
            })

            research_current = research_line_state(symbol, tf, level, selected)
            if research_current is not None:
                research_slots[slot_key] = {
                    "current": research_current,
                    "previous": None,
                    "history": [],
                }

    if missing_inputs:
        status = "FAIL_INPUT_MISSING"
    elif mismatch_count:
        status = "MISMATCH_FOUND_USE_RESEARCH_STATE"
    else:
        status = "MATCH_LIVE_CURRENT_EQUALS_FULL_HISTORY"

    research_state = {
        "schema": "nvt9-full-history-research-state/0.1",
        "status": "RESEARCH_ONLY",
        "symbol": symbol,
        "source_live_state": str(state_path),
        "selector_semantics": "DIRECT_FULL_HISTORY_CURRENT",
        "slots": research_slots,
        "production_writeback": False,
        "snapshot_writeback": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }

    audit = {
        "schema": "nvt9-normal-vs-full-history-audit/0.1",
        "status": status,
        "audit_id": "ID10IQ200",
        "symbol": symbol,
        "source_live_state": str(state_path),
        "input_dir": str(input_dir),
        "comparison_count": len(audit_rows),
        "mismatch_count": mismatch_count,
        "missing_inputs": missing_inputs,
        "comparisons": audit_rows,
        "finding": (
            "Published Normal Run current geometry differs from the direct full-history selector. "
            "Cross-TF ownership research must use the research full-history state until this integration discrepancy is resolved."
            if mismatch_count else
            "Published Normal Run current geometry matches direct full-history selector output."
        ),
        "production_changed": False,
        "renderer_changed": False,
        "snapshot_changed": False,
        "nca_draw_writeback": False,
    }

    audit_path = outdir / "NVT9_USDJPY_NORMAL_VS_FULL_HISTORY_0919.json"
    state_out = outdir / "NVT9_USDJPY_FULL_HISTORY_RESEARCH_STATE_0919.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    state_out.write_text(json.dumps(research_state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": status,
        "comparison_count": len(audit_rows),
        "mismatch_count": mismatch_count,
        "audit": str(audit_path),
        "research_state": str(state_out),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 2 if missing_inputs else 0


if __name__ == "__main__":
    raise SystemExit(main())
