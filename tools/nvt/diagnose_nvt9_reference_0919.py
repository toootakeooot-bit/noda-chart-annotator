from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.geometry import build_channel_candidates, select_large_mid
from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import (
    TFS,
    rebuild_timeframe_baseline_0919_from_bars,
    safe_symbol_filename,
    structural_event_end_indices,
)
from live_draw.turn_detector import detect_turns

CUTOFF = datetime.fromisoformat("2026-09-19T00:00:00")
TOL = 1e-10


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def eqf(a, b, tol=TOL) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tol)


def pivot_kind(ref: dict) -> str:
    return "LOW" if ref["direction"] == "RISING" else "HIGH"


def pivot_match(p, kind: str, when: str, price: float) -> bool:
    return p.kind == kind and p.time.isoformat() == when and eqf(p.price, price)


def candidate_anchor_match(c, ref: dict) -> bool:
    return (
        c.direction == ref["direction"]
        and c.anchor1.time.isoformat() == ref["anchor1_time"]
        and eqf(c.anchor1.price, ref["anchor1_price"])
        and c.anchor2.time.isoformat() == ref["anchor2_time"]
        and eqf(c.anchor2.price, ref["anchor2_price"])
    )


def candidate_geometry_match(c, ref: dict) -> bool:
    return candidate_anchor_match(c, ref) and eqf(c.ch_offset, ref["ch_offset"]) and eqf(c.zone_width, ref["zone_width"])


def state_geometry_match(item: dict | None, ref: dict) -> bool:
    if not item:
        return False
    return (
        item.get("direction") == ref["direction"]
        and item.get("anchor1_time") == ref["anchor1_time"]
        and eqf(item.get("anchor1_price"), ref["anchor1_price"])
        and item.get("anchor2_time") == ref["anchor2_time"]
        and eqf(item.get("anchor2_price"), ref["anchor2_price"])
        and eqf(item.get("ch_offset"), ref["ch_offset"])
        and eqf(item.get("zone_width"), ref["zone_width"])
    )


def geom_summary(item: dict | None) -> dict | None:
    if not item:
        return None
    return {
        "line_id": item.get("line_id"),
        "direction": item.get("direction"),
        "anchor1_time": item.get("anchor1_time"),
        "anchor1_price": item.get("anchor1_price"),
        "anchor2_time": item.get("anchor2_time"),
        "anchor2_price": item.get("anchor2_price"),
        "ch_offset": item.get("ch_offset"),
        "zone_width": item.get("zone_width"),
        "generation": item.get("generation"),
        "status": item.get("status"),
    }


def first_geometry_diffs(item: dict | None, ref: dict) -> list[str]:
    if not item:
        return ["presence"]
    diffs = []
    for field in ("direction", "anchor1_time", "anchor2_time"):
        if item.get(field) != ref[field]:
            diffs.append(field)
    for field in ("anchor1_price", "anchor2_price", "ch_offset", "zone_width"):
        if not eqf(item.get(field), ref[field]):
            diffs.append(field)
    return diffs


def state_locations(state: dict, ref: dict) -> list[dict]:
    found = []
    for slot_key, slot in state.get("slots", {}).items():
        for role in ("current", "previous"):
            item = slot.get(role)
            if state_geometry_match(item, ref):
                found.append({"slot": slot_key, "role": role.upper(), "line": geom_summary(item)})
        for i, item in enumerate(slot.get("history") or []):
            if state_geometry_match(item, ref):
                found.append({"slot": slot_key, "role": f"HISTORY[{i}]", "line": geom_summary(item)})
    return found


def preview_selected_geometry(preview_audit: dict | None, tf: str) -> list[dict]:
    if not preview_audit:
        return []
    out = []
    for row in (preview_audit.get("source_selection") or {}).get(tf, []) or []:
        out.append({
            "line_id": row.get("line_id"),
            "structure_level": row.get("structure_level"),
            "direction": row.get("direction"),
            "anchor1_time": row.get("anchor1_time"),
            "anchor1_price": row.get("anchor1_price"),
            "anchor2_time": row.get("anchor2_time"),
            "anchor2_price": row.get("anchor2_price"),
            "ch_offset": row.get("ch_offset"),
            "zone_width": row.get("zone_width"),
        })
    return out


def preview_match(rows: list[dict], ref: dict) -> bool:
    return any(state_geometry_match(row, ref) for row in rows)


def scan_selected_events(bars, symbol: str, tf: str, refs: list[dict]) -> dict[str, list[dict]]:
    wanted = {r["reference_id"]: r for r in refs}
    hits = {rid: [] for rid in wanted}
    for end_index in structural_event_end_indices(bars):
        prefix = bars[:end_index + 1]
        turns = detect_turns(prefix)
        candidates = build_channel_candidates(prefix, turns.pivots)
        large, mid, _ = select_large_mid(symbol, tf, candidates)
        for level, selected in (("LARGE_DOW", large), ("MID_DOW", mid)):
            if selected is None:
                continue
            for rid, ref in wanted.items():
                if candidate_geometry_match(selected.candidate, ref):
                    hits[rid].append({
                        "closed_bar_index": end_index,
                        "closed_bar_time": prefix[-1].time.isoformat(),
                        "selected_as": level,
                        "candidate_id": selected.candidate.id_key,
                    })
    return hits


def classify(
    *,
    a1_ok: bool,
    a2_ok: bool,
    anchor_candidates: list,
    geometry_candidates: list,
    selected_hits: list[dict],
    expected_level: str,
    lifecycle_locations: list[dict],
    current_match: bool,
    display_match: bool | None,
) -> tuple[str, str]:
    if not a1_ok or not a2_ok:
        return "A_PIVOT", "One or both frozen 09/19 anchors are no longer present as confirmed pivots in the current replay input."
    if not anchor_candidates:
        return "B_CANDIDATE_PAIR", "Both pivots exist, but the exact anchor pair is rejected before becoming a TL candidate."
    if not geometry_candidates:
        return "B_CANDIDATE_GEOMETRY", "The anchor pair exists as a candidate, but CH/zone geometry differs from the frozen 09/19 line."
    expected_hits = [x for x in selected_hits if x["selected_as"] == expected_level]
    if not expected_hits:
        other = sorted({x["selected_as"] for x in selected_hits})
        if other:
            return "C_SELECTOR_LEVEL", f"The exact candidate is selected, but as {other} instead of {expected_level}."
        return "C_SELECTOR", "The exact frozen candidate exists but never wins the selector at the expected structural level."
    if not current_match:
        if lifecycle_locations:
            return "D_LIFECYCLE_REPLACED", "The frozen candidate was selected/promoted, but later lifecycle updates replaced it before the cutoff."
        return "D_LIFECYCLE", "The frozen candidate won the selector but is not the current line at the cutoff."
    if display_match is False:
        return "E_DISPLAY_SELECTION", "The frozen line is current in lifecycle state, but the TF-map visibility selector displays a different family."
    return "MATCH_THROUGH_E", "Frozen 09/19 geometry survives Pivot, Candidate, Selector, Lifecycle, and display selection."


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnose where each frozen 09/19 line diverges in the current replay.")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--preview-audit", default="")
    ap.add_argument("--symbol", default="USDJPY#")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    refdoc = load_json(Path(args.reference))
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    preview_audit = load_json(Path(args.preview_audit)) if args.preview_audit and Path(args.preview_audit).exists() else None

    refs_by_tf = {tf: [] for tf in TFS}
    for ref in refdoc["lines"]:
        refs_by_tf[ref["timeframe"]].append(ref)

    results = []
    input_coverage = {}

    for tf in TFS:
        src = input_dir / f"NVT_{safe_symbol_filename(args.symbol)}_{tf}.csv"
        if not src.exists():
            for ref in refs_by_tf[tf]:
                results.append({
                    "reference_id": ref["reference_id"],
                    "timeframe": tf,
                    "structure_level": ref["structure_level"],
                    "first_divergence_stage": "INPUT_MISSING",
                    "reason": str(src),
                })
            continue

        all_bars = load_ohlc_csv(src)
        bars = [b for b in all_bars if b.time < CUTOFF]
        input_coverage[tf] = {
            "source": str(src),
            "all_bar_count": len(all_bars),
            "replay_bar_count": len(bars),
            "first_replay_bar": bars[0].time.isoformat() if bars else None,
            "last_replay_bar": bars[-1].time.isoformat() if bars else None,
            "cutoff_exclusive": CUTOFF.isoformat(),
        }
        if len(bars) < 3:
            continue

        turns = detect_turns(bars)
        candidates = build_channel_candidates(bars, turns.pivots)
        selected_hits = scan_selected_events(bars, args.symbol, tf, refs_by_tf[tf])
        state, replay_audit = rebuild_timeframe_baseline_0919_from_bars(
            bars, args.symbol, tf, include_selector_trace=True
        )
        preview_rows = preview_selected_geometry(preview_audit, tf)

        for ref in refs_by_tf[tf]:
            kind = pivot_kind(ref)
            a1_matches = [p for p in turns.pivots if pivot_match(p, kind, ref["anchor1_time"], ref["anchor1_price"])]
            a2_matches = [p for p in turns.pivots if pivot_match(p, kind, ref["anchor2_time"], ref["anchor2_price"])]
            anchor_candidates = [c for c in candidates if candidate_anchor_match(c, ref)]
            geometry_candidates = [c for c in anchor_candidates if candidate_geometry_match(c, ref)]
            slot_key = f"{args.symbol}|{tf}|{ref['structure_level']}"
            current = (state.get("slots", {}).get(slot_key) or {}).get("current")
            locations = state_locations(state, ref)
            curr_match = state_geometry_match(current, ref)
            disp_match = preview_match(preview_rows, ref) if preview_audit is not None else None

            stage, reason = classify(
                a1_ok=bool(a1_matches),
                a2_ok=bool(a2_matches),
                anchor_candidates=anchor_candidates,
                geometry_candidates=geometry_candidates,
                selected_hits=selected_hits.get(ref["reference_id"], []),
                expected_level=ref["structure_level"],
                lifecycle_locations=locations,
                current_match=curr_match,
                display_match=disp_match,
            )

            candidate_evidence = []
            for c in anchor_candidates[:10]:
                candidate_evidence.append({
                    "candidate_id": c.id_key,
                    "ch_offset": float(c.ch_offset),
                    "zone_width": float(c.zone_width),
                    "turn_span": int(c.turn_span),
                    "tl_contacts": int(c.tl_contacts),
                    "ch_contacts": int(c.ch_contacts),
                    "unbroken_close": bool(c.unbroken_close),
                    "exact_reference_geometry": candidate_geometry_match(c, ref),
                })

            results.append({
                "reference_id": ref["reference_id"],
                "reference_no": ref["reference_no"],
                "timeframe": tf,
                "structure_level": ref["structure_level"],
                "reference_line_id": ref["line_id"],
                "reference_direction": ref["direction"],
                "reference_anchor1": {"time": ref["anchor1_time"], "price": ref["anchor1_price"]},
                "reference_anchor2": {"time": ref["anchor2_time"], "price": ref["anchor2_price"]},
                "A_pivot": {
                    "expected_kind": kind,
                    "anchor1_present": bool(a1_matches),
                    "anchor2_present": bool(a2_matches),
                    "anchor1_confirmed_by": a1_matches[0].confirmed_by_time.isoformat() if a1_matches else None,
                    "anchor2_confirmed_by": a2_matches[0].confirmed_by_time.isoformat() if a2_matches else None,
                    "confirmed_pivot_count": len(turns.pivots),
                },
                "B_candidate": {
                    "anchor_pair_candidate_count": len(anchor_candidates),
                    "exact_geometry_candidate_count": len(geometry_candidates),
                    "candidates": candidate_evidence,
                },
                "C_selector": {
                    "selected_event_count": len(selected_hits.get(ref["reference_id"], [])),
                    "selected_events": selected_hits.get(ref["reference_id"], [])[-10:],
                },
                "D_lifecycle": {
                    "expected_slot": slot_key,
                    "current_matches_reference": curr_match,
                    "current": geom_summary(current),
                    "current_differences": first_geometry_diffs(current, ref),
                    "reference_locations": locations,
                    "transition_count": replay_audit.get("transition_count"),
                },
                "E_display": {
                    "preview_audit_available": preview_audit is not None,
                    "source_tf_selected_rows": preview_rows,
                    "reference_selected_for_display": disp_match,
                },
                "first_divergence_stage": stage,
                "reason": reason,
            })

    stage_counts = {}
    for r in results:
        stage_counts[r["first_divergence_stage"]] = stage_counts.get(r["first_divergence_stage"], 0) + 1

    payload = {
        "schema": "nvt9-0919-reference-diagnostic/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_DIAGNOSTIC_COMPLETED",
        "symbol": args.symbol,
        "reference_source": str(args.reference),
        "cutoff_exclusive": CUTOFF.isoformat(),
        "input_coverage": input_coverage,
        "stage_order": ["A_PIVOT", "B_CANDIDATE_PAIR", "B_CANDIDATE_GEOMETRY", "C_SELECTOR", "C_SELECTOR_LEVEL", "D_LIFECYCLE", "D_LIFECYCLE_REPLACED", "E_DISPLAY_SELECTION", "MATCH_THROUGH_E"],
        "stage_counts": stage_counts,
        "results": sorted(results, key=lambda x: x.get("reference_no", 999)),
    }
    json_path = outdir / "NVT9_0919_REFERENCE_DIAGNOSTIC.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    txt = [
        "NVT9 09/19 REFERENCE DIAGNOSTIC",
        "Audit ID: ID10IQ200",
        f"status={payload['status']}",
        f"stage_counts={json.dumps(stage_counts, ensure_ascii=False)}",
        "",
        "INPUT COVERAGE",
    ]
    for tf in TFS:
        c = input_coverage.get(tf)
        if c:
            txt.append(f"  {tf}: bars={c['replay_bar_count']} first={c['first_replay_bar']} last={c['last_replay_bar']}")
    txt.append("")
    txt.append("REFERENCE RESULTS")
    for r in payload["results"]:
        txt.append(
            f"  {r['reference_id']} {r['timeframe']} {r['structure_level']} -> "
            f"{r['first_divergence_stage']} | {r['reason']}"
        )
        if "D_lifecycle" in r:
            current = r["D_lifecycle"].get("current")
            if current:
                txt.append(
                    f"    current={current.get('direction')} "
                    f"{current.get('anchor1_time')}->{current.get('anchor2_time')} "
                    f"line={current.get('line_id')}"
                )
    txt_path = outdir / "NVT9_0919_REFERENCE_DIAGNOSTIC.txt"
    txt_path.write_text("\n".join(txt), encoding="utf-8")

    print("\n".join(txt))
    print("")
    print(f"JSON: {json_path}")
    print(f"TXT:  {txt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
