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
        "decision_hl_time": item.get("decision_hl_time"),
        "decision_hl_price": item.get("decision_hl_price"),
        "decision_hl_kind": item.get("decision_hl_kind"),
        "hl_break_time": item.get("hl_break_time"),
        "hl_break_mode": item.get("hl_break_mode"),
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


def projected_channel(item: dict, at: datetime) -> tuple[float, float]:
    t1 = datetime.fromisoformat(item["anchor1_time"])
    t2 = datetime.fromisoformat(item["anchor2_time"])
    p1 = float(item["anchor1_price"])
    p2 = float(item["anchor2_price"])
    sec = (t2 - t1).total_seconds()
    if sec == 0:
        return p1, p1 + float(item["ch_offset"])
    slope = (p2 - p1) / sec
    tl = p1 + slope * (at - t1).total_seconds()
    return tl, tl + float(item["ch_offset"])


def channel_distance(price: float, tl: float, ch: float) -> float:
    lo, hi = sorted((tl, ch))
    if lo <= price <= hi:
        return 0.0
    return min(abs(price - lo), abs(price - hi))


def replay_stage_snapshot(bars, symbol: str, tf: str, refs: list[dict]) -> dict:
    """Evaluate a fixed bar window against frozen references."""
    turns = detect_turns(bars)
    candidates = build_channel_candidates(bars, turns.pivots)
    hits = scan_selected_events(bars, symbol, tf, refs)
    state, audit = rebuild_timeframe_baseline_0919_from_bars(
        bars, symbol, tf, include_selector_trace=True
    )
    out = {}
    for ref in refs:
        kind = pivot_kind(ref)
        a1 = [p for p in turns.pivots if pivot_match(p, kind, ref["anchor1_time"], ref["anchor1_price"])]
        a2 = [p for p in turns.pivots if pivot_match(p, kind, ref["anchor2_time"], ref["anchor2_price"])]
        anchor_candidates = [c for c in candidates if candidate_anchor_match(c, ref)]
        geometry_candidates = [c for c in anchor_candidates if candidate_geometry_match(c, ref)]
        slot_key = f"{symbol}|{tf}|{ref['structure_level']}"
        current = (state.get("slots", {}).get(slot_key) or {}).get("current")
        exact_candidate = geometry_candidates[0] if geometry_candidates else (anchor_candidates[0] if anchor_candidates else None)
        reference_candidate = None
        if exact_candidate is not None:
            reference_candidate = {
                "candidate_id": exact_candidate.id_key,
                "direction": exact_candidate.direction,
                "turn_span": int(exact_candidate.turn_span),
                "tl_contacts": int(exact_candidate.tl_contacts),
                "ch_contacts": int(exact_candidate.ch_contacts),
                "unbroken_close": bool(exact_candidate.unbroken_close),
                "ch_offset": float(exact_candidate.ch_offset),
                "zone_width": float(exact_candidate.zone_width),
                "decision_hl_kind": exact_candidate.decision_hl.kind if exact_candidate.decision_hl else None,
                "decision_hl_time": exact_candidate.decision_hl.time.isoformat() if exact_candidate.decision_hl else None,
                "decision_hl_price": float(exact_candidate.decision_hl.price) if exact_candidate.decision_hl else None,
                "hl_break_time": exact_candidate.hl_break_time.isoformat() if exact_candidate.hl_break_time else None,
                "hl_break_mode": exact_candidate.hl_break_mode,
                "exact_reference_geometry": candidate_geometry_match(exact_candidate, ref),
            }
        out[ref["reference_id"]] = {
            "bar_count": len(bars),
            "first_bar": bars[0].time.isoformat() if bars else None,
            "last_bar": bars[-1].time.isoformat() if bars else None,
            "confirmed_pivot_count": len(turns.pivots),
            "anchor1_present": bool(a1),
            "anchor2_present": bool(a2),
            "anchor_pair_candidate_count": len(anchor_candidates),
            "exact_geometry_candidate_count": len(geometry_candidates),
            "reference_candidate": reference_candidate,
            "selected_event_count": len(hits.get(ref["reference_id"], [])),
            "selected_events": hits.get(ref["reference_id"], [])[-10:],
            "current_matches_reference": state_geometry_match(current, ref),
            "current": geom_summary(current),
            "current_differences": first_geometry_diffs(current, ref),
            "transition_count": audit.get("transition_count"),
        }
    # Reproduce the approved 09/19 source-family display selection:
    # CURRENT only, one nearest family per source TF, LARGE wins only on equal distance.
    latest_time = bars[-1].time if bars else None
    latest_close = float(bars[-1].close) if bars else None
    display_candidates = []
    if latest_time is not None:
        for level in ("LARGE_DOW", "MID_DOW"):
            slot_key = f"{symbol}|{tf}|{level}"
            current = (state.get("slots", {}).get(slot_key) or {}).get("current")
            if not current:
                continue
            tl, ch = projected_channel(current, latest_time)
            display_candidates.append({
                "level": level,
                "line_id": current.get("line_id"),
                "distance_to_channel": channel_distance(latest_close, tl, ch),
                "projected_tl": tl,
                "projected_ch": ch,
                "current": geom_summary(current),
            })
    display_candidates.sort(key=lambda x: (
        x["distance_to_channel"],
        0 if x["level"] == "LARGE_DOW" else 1,
        x["line_id"] or "",
    ))
    display_selected = display_candidates[0] if display_candidates else None

    # Independently reproduce the approved 09/19 display decision from the
    # frozen CURRENT references themselves. This is the authoritative visual
    # restoration path even when today's replay code no longer reconstructs
    # the same lifecycle current.
    frozen_display_candidates = []
    if latest_time is not None:
        for ref in refs:
            tl, ch = projected_channel(ref, latest_time)
            frozen_display_candidates.append({
                "reference_id": ref["reference_id"],
                "level": ref["structure_level"],
                "distance_to_channel": channel_distance(latest_close, tl, ch),
                "projected_tl": tl,
                "projected_ch": ch,
            })
    frozen_display_candidates.sort(key=lambda x: (
        x["distance_to_channel"],
        0 if x["level"] == "LARGE_DOW" else 1,
        x["reference_id"],
    ))
    frozen_display_selected = frozen_display_candidates[0] if frozen_display_candidates else None

    final_audit = audit.get("final_selector_audit") or {}
    trace = final_audit.get("selector_trace") or {}
    for ref in refs:
        row = out[ref["reference_id"]]
        level_key = "large" if ref["structure_level"] == "LARGE_DOW" else "mid"
        level_reason = final_audit.get("large_reason") if level_key == "large" else final_audit.get("mid_reason")
        decision = trace.get(level_key) or {}
        catalog = trace.get("candidate_catalog") or []
        reference_catalog_rows = []
        ref_candidate = row.get("reference_candidate") or {}
        for cat in catalog:
            if cat.get("native_candidate_id") != ref_candidate.get("candidate_id"):
                continue
            if not eqf(cat.get("ch_offset"), ref.get("ch_offset")):
                continue
            if not eqf(cat.get("zone_width"), ref.get("zone_width")):
                continue
            reference_catalog_rows.append(cat)
        reference_catalog = reference_catalog_rows[0] if reference_catalog_rows else None

        row["reference_candidate_audit"] = reference_catalog
        row["selector_reason"] = level_reason
        row["selector_trace_decision"] = decision
        row["replay_display_candidates"] = [
            {
                "level": x["level"],
                "line_id": x["line_id"],
                "distance_to_channel": x["distance_to_channel"],
                "projected_tl": x["projected_tl"],
                "projected_ch": x["projected_ch"],
            }
            for x in display_candidates
        ]
        row["replay_display_selected_level"] = display_selected["level"] if display_selected else None
        row["replay_display_selected_line_id"] = display_selected["line_id"] if display_selected else None
        row["replay_display_selected_matches_reference"] = (
            display_selected is not None
            and display_selected["level"] == ref["structure_level"]
            and state_geometry_match(display_selected["current"], ref)
        )
        row["frozen_display_candidates"] = frozen_display_candidates
        row["display_selected"] = (
            frozen_display_selected is not None
            and frozen_display_selected["reference_id"] == ref["reference_id"]
        )
        row["selector_reason_applies_to_reference"] = bool(row["current_matches_reference"])
        if not row["selector_reason_applies_to_reference"]:
            row["selector_reason_status"] = "HISTORICAL_SELECTOR_REASON_NOT_REPRODUCED_BY_CURRENT_600BAR_REPLAY"
        else:
            row["selector_reason_status"] = "REPRODUCED_600BAR_SELECTOR_REASON"
        if row["display_selected"]:
            row["display_reason"] = "FROZEN_0919_CURRENT_NEAREST_FAMILY"
            row["display_reason_detail"] = {
                "latest_closed_bar_time": latest_time.isoformat(),
                "latest_close": latest_close,
                "distance_to_channel": frozen_display_selected["distance_to_channel"],
                "tie_break": "LARGE_DOW_ONLY_WHEN_DISTANCE_EQUAL",
            }
        else:
            row["display_reason"] = "NOT_SELECTED_FOR_FROZEN_0919_DISPLAY"

    return out


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
    historical_input_reference = refdoc.get("historical_input_reference") or {}
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
        production_600_bars = bars[-600:] if len(bars) >= 600 else bars
        production_600 = replay_stage_snapshot(production_600_bars, args.symbol, tf, refs_by_tf[tf])
        hist = historical_input_reference.get(tf) or {}
        first_replay = bars[0].time.isoformat() if bars else None
        last_replay = bars[-1].time.isoformat() if bars else None
        known_hist_first = hist.get("first_bar")
        known_hist_count = hist.get("bar_count")
        known_hist_last = hist.get("last_closed_bar")
        input_coverage[tf] = {
            "source": str(src),
            "all_bar_count": len(all_bars),
            "replay_bar_count": len(bars),
            "first_replay_bar": first_replay,
            "last_replay_bar": last_replay,
            "cutoff_exclusive": CUTOFF.isoformat(),
            "historical_first_bar": known_hist_first,
            "historical_bar_count": known_hist_count,
            "historical_last_closed_bar": known_hist_last,
            "first_bar_same_as_historical": (first_replay == known_hist_first) if known_hist_first else None,
            "bar_count_same_as_historical": (len(bars) == int(known_hist_count)) if known_hist_count is not None else None,
            "last_bar_same_as_historical": (last_replay == known_hist_last) if known_hist_last else None,
            "production_600_bar_count": len(production_600_bars),
            "production_600_first_bar": production_600_bars[0].time.isoformat() if production_600_bars else None,
            "production_600_last_bar": production_600_bars[-1].time.isoformat() if production_600_bars else None,
            "input_window_changed": (
                (known_hist_first is not None and first_replay != known_hist_first)
                or (known_hist_count is not None and len(bars) != int(known_hist_count))
                or (known_hist_last is not None and last_replay != known_hist_last)
            ),
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
                "production_600_replay": production_600.get(ref["reference_id"]),
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

    production_600_display_selected_refs = [
        r["reference_id"]
        for r in results
        if (r.get("production_600_replay") or {}).get("display_selected") is True
    ]

    prod600_matches = [
        r for r in results
        if (r.get("production_600_replay") or {}).get("current_matches_reference") is True
    ]
    deep_matches = [
        r for r in results
        if r.get("first_divergence_stage") == "MATCH_THROUGH_E"
    ]
    if len(prod600_matches) == len(results) and len(deep_matches) < len(results):
        root_cause_status = "ROOT_CAUSE_INPUT_HORIZON_CONFIRMED"
    elif len(prod600_matches) > len(deep_matches):
        root_cause_status = "INPUT_HORIZON_STRONGLY_SUPPORTED"
    else:
        root_cause_status = "INPUT_HORIZON_NOT_SUFFICIENT_ALONE"

    payload = {
        "schema": "nvt9-0919-reference-diagnostic/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_DIAGNOSTIC_COMPLETED",
        "root_cause_status": root_cause_status,
        "production_600_reference_match_count": len(prod600_matches),
        "production_600_display_selected_refs": production_600_display_selected_refs,
        "deep_reference_match_count": len(deep_matches),
        "symbol": args.symbol,
        "reference_source": str(args.reference),
        "cutoff_exclusive": CUTOFF.isoformat(),
        "input_coverage": input_coverage,
        "input_window_changed_timeframes": [tf for tf, row in input_coverage.items() if row.get("input_window_changed")],
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
        f"root_cause_status={root_cause_status}",
        f"production_600_reference_match_count={len(prod600_matches)}/{len(results)}",
        f"production_600_display_selected_refs={','.join(production_600_display_selected_refs)}",
        f"deep_reference_match_count={len(deep_matches)}/{len(results)}",
        f"stage_counts={json.dumps(stage_counts, ensure_ascii=False)}",
        "",
        "INPUT COVERAGE",
    ]
    for tf in TFS:
        c = input_coverage.get(tf)
        if c:
            txt.append(
                f"  {tf}: bars={c['replay_bar_count']} first={c['first_replay_bar']} last={c['last_replay_bar']} "
                f"| historical_first={c.get('historical_first_bar')} historical_count={c.get('historical_bar_count')} "
                f"| window_changed={c.get('input_window_changed')}"
            )
    txt.append("")
    txt.append("REFERENCE RESULTS")
    for r in payload["results"]:
        p600 = r.get("production_600_replay") or {}
        txt.append(
            f"  {r['reference_id']} {r['timeframe']} {r['structure_level']} | "
            f"600bar_match={p600.get('current_matches_reference')} | "
            f"display_selected={p600.get('display_selected')} | "
            f"deep_first_divergence={r['first_divergence_stage']} | {r['reason']}"
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
