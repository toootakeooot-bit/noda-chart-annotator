from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "nvt"))

from live_draw.geometry import build_channel_candidates, select_large_mid
from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import TFS, safe_symbol_filename
from live_draw.turn_detector import detect_turns
from nvt.tl_quality_auditor import audit_line


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pivot_dict(pivot) -> dict[str, Any]:
    return {
        "kind": pivot.kind,
        "bar_index": int(pivot.bar_index),
        "time": pivot.time.isoformat(),
        "price": float(pivot.price),
        "confirmed_by_index": int(pivot.confirmed_by_index),
        "confirmed_by_time": pivot.confirmed_by_time.isoformat(),
        "retracement": float(pivot.retracement),
        "pivot_valid": True,
        "closed_bar_confirmed": True,
    }


def candidate_dict(candidate) -> dict[str, Any]:
    break_mode = candidate.hl_break_mode
    break_by_close = isinstance(break_mode, str) and break_mode.startswith("CLOSED_BAR_CLOSE")
    return {
        "candidate_id": candidate.id_key,
        "direction": candidate.direction,
        "anchor1": pivot_dict(candidate.anchor1),
        "anchor2": pivot_dict(candidate.anchor2),
        "decision_hl": pivot_dict(candidate.decision_hl) if candidate.decision_hl else None,
        "hl_break_time": candidate.hl_break_time.isoformat() if candidate.hl_break_time else None,
        "hl_break_mode": break_mode,
        "break_by_close": bool(break_by_close),
        "slope_per_second": float(candidate.slope_per_second),
        "turn_span": int(candidate.turn_span),
        "tl_contacts": int(candidate.tl_contacts),
        "ch_contacts": int(candidate.ch_contacts),
        "unbroken_close": bool(candidate.unbroken_close),
        "ch_anchor": pivot_dict(candidate.ch_anchor),
        "ch_offset": float(candidate.ch_offset),
        "zone_width": float(candidate.zone_width),
    }


def same_state_geometry(line: dict[str, Any], candidate, tol: float = 1e-9) -> bool:
    if str(line.get("direction")) != str(candidate.direction):
        return False
    if line.get("anchor1_time") != candidate.anchor1.time.isoformat():
        return False
    if line.get("anchor2_time") != candidate.anchor2.time.isoformat():
        return False
    try:
        if not math.isclose(float(line.get("anchor1_price")), float(candidate.anchor1.price), rel_tol=0.0, abs_tol=tol):
            return False
        if not math.isclose(float(line.get("anchor2_price")), float(candidate.anchor2.price), rel_tol=0.0, abs_tol=tol):
            return False
    except (TypeError, ValueError):
        return False
    return True


def candidate_distance(line: dict[str, Any], candidate) -> tuple[float, float, int, str]:
    ch = abs(float(line.get("ch_offset", 0.0)) - float(candidate.ch_offset))
    zone = abs(float(line.get("zone_width", 0.0)) - float(candidate.zone_width))
    return (ch, zone, -int(candidate.turn_span), candidate.id_key)


def selected_candidate_id(selected) -> str | None:
    return selected.candidate.id_key if selected is not None else None


def collect_line_rows(state: dict[str, Any], symbol: str, timeframe: str, include_history: bool) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for slot_key, slot in (state.get("slots") or {}).items():
        if not isinstance(slot, dict):
            continue
        for role in ("current", "previous"):
            item = slot.get(role)
            if not isinstance(item, dict):
                continue
            if item.get("symbol") != symbol or item.get("timeframe") != timeframe:
                continue
            rows.append((role.upper(), item))
        if include_history:
            for index, item in enumerate(slot.get("history") or []):
                if not isinstance(item, dict):
                    continue
                if item.get("symbol") != symbol or item.get("timeframe") != timeframe:
                    continue
                rows.append((f"HISTORY_{index:04d}", item))
    rows.sort(key=lambda x: (
        str(x[1].get("structure_level") or ""),
        str(x[1].get("line_id") or ""),
        x[0],
    ))
    return rows


def selector_evidence(level: str, canonical_id: str | None, large, mid, classifier: dict[str, Any]) -> dict[str, Any]:
    direct = large if level == "LARGE_DOW" else mid if level == "MID_DOW" else None
    direct_id = selected_candidate_id(direct)
    reason = classifier.get("large_reason") if level == "LARGE_DOW" else classifier.get("mid_reason")
    return {
        "candidate_present": canonical_id is not None,
        "direct_selected_candidate_id": direct_id,
        "selector_match": (canonical_id == direct_id) if canonical_id is not None and direct_id is not None else None,
        "reason": reason,
        "selection_scope": "FULL_HISTORY_DIRECT_SELECTOR",
        "note": (
            "Direct selector match is authoritative for the current full-history selection only. "
            "Previous/history lifecycle rows may legitimately differ because they were selected at earlier prefixes."
        ),
    }


def audit_record_from_match(
    *,
    line: dict[str, Any],
    role: str,
    candidate,
    level: str,
    selector: dict[str, Any],
) -> dict[str, Any]:
    c = candidate_dict(candidate)
    break_by_close = bool(c["break_by_close"])
    record = {
        "line_id": line.get("line_id"),
        "direction": line.get("direction"),
        "source_tf": line.get("timeframe"),
        "owner_tf": line.get("timeframe"),
        "structure_level": level,
        "anchor1": c["anchor1"],
        "anchor2": c["anchor2"],
        "turn_span": c["turn_span"],
        "tl_contacts": c["tl_contacts"],
        "ch_contacts": c["ch_contacts"],
        "slope_per_second": c["slope_per_second"],
        "unbroken_close": c["unbroken_close"],
        "ch_offset": c["ch_offset"],
        "zone_width": c["zone_width"],
        "candidate": {
            "candidate_present": True,
            "candidate_id": c["candidate_id"],
        },
        "selector": selector,
        "structure": {
            "hl_exists": c["decision_hl"] is not None,
            "n_pattern_confirmed": c["decision_hl"] is not None,
            "dow_confirmed": c["decision_hl"] is not None and break_by_close,
            "hl_break": c["hl_break_time"] is not None,
            "break_by_close": break_by_close,
            "activated_on_wick_only": False if break_by_close else None,
        },
        "lifecycle_evidence": {
            "state": role,
        },
        "matched_patterns": ["P07"] if break_by_close else [],
    }
    return record


def build_timeframe_evidence(
    *,
    state: dict[str, Any],
    symbol: str,
    timeframe: str,
    input_csv: Path,
    include_history: bool,
) -> dict[str, Any]:
    bars = load_ohlc_csv(input_csv)
    turns = detect_turns(bars)
    candidates = build_channel_candidates(bars, turns.pivots)
    large, mid, classifier = select_large_mid(symbol, timeframe, candidates)

    rows = collect_line_rows(state, symbol, timeframe, include_history)
    evidence_rows: list[dict[str, Any]] = []

    for role, line in rows:
        matches = [c for c in candidates if same_state_geometry(line, c)]
        matches.sort(key=lambda c: candidate_distance(line, c))
        canonical = matches[0] if matches else None
        level = str(line.get("structure_level") or "")
        canonical_id = canonical.id_key if canonical is not None else None
        selector = selector_evidence(level, canonical_id, large, mid, classifier)

        row: dict[str, Any] = {
            "line_id": line.get("line_id"),
            "symbol": symbol,
            "timeframe": timeframe,
            "structure_level": level,
            "generation_role": role,
            "line_status": line.get("status"),
            "match_status": (
                "EXACT_UNIQUE" if len(matches) == 1
                else "EXACT_AMBIGUOUS" if len(matches) > 1
                else "NOT_FOUND"
            ),
            "candidate_match_count": len(matches),
            "state_geometry": {
                "direction": line.get("direction"),
                "anchor1_time": line.get("anchor1_time"),
                "anchor1_price": line.get("anchor1_price"),
                "anchor2_time": line.get("anchor2_time"),
                "anchor2_price": line.get("anchor2_price"),
                "ch_offset": line.get("ch_offset"),
                "zone_width": line.get("zone_width"),
                "decision_hl_time": line.get("decision_hl_time"),
                "decision_hl_price": line.get("decision_hl_price"),
                "decision_hl_kind": line.get("decision_hl_kind"),
                "hl_break_time": line.get("hl_break_time"),
                "hl_break_mode": line.get("hl_break_mode"),
            },
            "candidate": candidate_dict(canonical) if canonical is not None else None,
            "candidate_variants": [candidate_dict(c) for c in matches[:5]],
            "selector_evidence": selector,
        }

        if canonical is not None:
            state_hl_time = line.get("decision_hl_time")
            state_break_time = line.get("hl_break_time")
            candidate_hl_time = canonical.decision_hl.time.isoformat() if canonical.decision_hl else None
            candidate_break_time = canonical.hl_break_time.isoformat() if canonical.hl_break_time else None
            row["state_candidate_consistency"] = {
                "decision_hl_time_same": state_hl_time in {None, candidate_hl_time},
                "hl_break_time_same": state_break_time in {None, candidate_break_time},
                "ch_offset_abs_diff": abs(float(line.get("ch_offset", 0.0)) - float(canonical.ch_offset)),
                "zone_width_abs_diff": abs(float(line.get("zone_width", 0.0)) - float(canonical.zone_width)),
            }
            audit_record = audit_record_from_match(
                line=line,
                role=role,
                candidate=canonical,
                level=level,
                selector=selector,
            )
            # Selector match is only a hard line-level signal for CURRENT rows.
            if role != "CURRENT":
                audit_record["selector"]["selector_match"] = None
            row["quality_audit"] = audit_line(audit_record)
        else:
            row["state_candidate_consistency"] = None
            row["quality_audit"] = {
                "schema": "nvt9-tl-quality-audit/1.0",
                "TL_ID": line.get("line_id"),
                "Quality": "HOLD",
                "Confidence": "HIGH",
                "AuditReadiness": "INSUFFICIENT",
                "missing_evidence": ["Pivot", "Structure", "HL Break"],
                "cause_layer": "CANDIDATE_GENERATION",
                "checks": {
                    "Pivot": "UNKNOWN",
                    "Anchor": "PASS",
                    "Structure": "UNKNOWN",
                    "HL Break": "UNKNOWN",
                    "Geometry": "UNKNOWN",
                    "Outer/Inner": "UNKNOWN",
                    "Cross-TF": "PASS",
                    "History Match": "UNKNOWN",
                },
                "matched_patterns": [],
                "reasons": [
                    {
                        "pattern_id": None,
                        "layer": "CANDIDATE_GENERATION",
                        "reason_code": "STATE_CANDIDATE_JOIN_NOT_FOUND",
                        "disposition": "HOLD",
                        "message": "State TL geometry could not be joined to a full-history candidate; do not infer invalidity from the missing join alone.",
                    }
                ],
            }

        evidence_rows.append(row)

    return {
        "timeframe": timeframe,
        "input_csv": str(input_csv),
        "closed_bar_count": len(bars),
        "confirmed_pivot_count": len(turns.pivots),
        "candidate_count": len(candidates),
        "direct_large_candidate_id": selected_candidate_id(large),
        "direct_mid_candidate_id": selected_candidate_id(mid),
        "classifier": classifier,
        "line_count": len(evidence_rows),
        "matched_line_count": sum(1 for row in evidence_rows if row["candidate_match_count"] > 0),
        "unmatched_line_count": sum(1 for row in evidence_rows if row["candidate_match_count"] == 0),
        "lines": evidence_rows,
    }


def build_evidence(
    *,
    state: dict[str, Any],
    symbol: str,
    input_dir: Path,
    input_prefix: str,
    include_history: bool,
) -> dict[str, Any]:
    safe = safe_symbol_filename(symbol)
    timeframes: dict[str, Any] = {}
    missing_inputs: list[str] = []

    for tf in TFS:
        src = input_dir / f"{input_prefix}_{safe}_{tf}.csv"
        if not src.exists():
            missing_inputs.append(str(src))
            continue
        timeframes[tf] = build_timeframe_evidence(
            state=state,
            symbol=symbol,
            timeframe=tf,
            input_csv=src,
            include_history=include_history,
        )

    lines = [
        row
        for tf_payload in timeframes.values()
        for row in tf_payload.get("lines", [])
    ]
    quality_counts: dict[str, int] = {}
    readiness_counts: dict[str, int] = {}
    match_counts: dict[str, int] = {}
    for row in lines:
        quality = row["quality_audit"].get("Quality")
        readiness = row["quality_audit"].get("AuditReadiness")
        status = row.get("match_status")
        quality_counts[quality] = quality_counts.get(quality, 0) + 1
        readiness_counts[readiness] = readiness_counts.get(readiness, 0) + 1
        match_counts[status] = match_counts.get(status, 0) + 1

    status = "PASS_AUDIT_EVIDENCE" if not missing_inputs else "PARTIAL_INPUT_MISSING"
    return {
        "schema": "nvt9-tl-audit-evidence/1.0",
        "status": status,
        "audit_id": "ID10IQ200",
        "symbol": symbol,
        "input_prefix": input_prefix,
        "include_history": include_history,
        "production_writeback": False,
        "mt4_object_writeback": False,
        "state_mutated": False,
        "missing_inputs": missing_inputs,
        "line_count": len(lines),
        "candidate_join_counts": match_counts,
        "quality_counts": quality_counts,
        "readiness_counts": readiness_counts,
        "timeframes": timeframes,
        "evidence_contract": {
            "pivot_retracement": "RECOVERED_FROM_CONFIRMED_PIVOT",
            "decision_hl": "RECOVERED_FROM_CHANNEL_CANDIDATE",
            "hl_break": "RECOVERED_FROM_CHANNEL_CANDIDATE",
            "break_by_close": "TRUE_WHEN_HL_BREAK_MODE_STARTS_CLOSED_BAR_CLOSE",
            "candidate_id": "RECOVERED_BY_EXACT_STATE_GEOMETRY_JOIN",
            "contacts_turn_span_unbroken": "RECOVERED_FROM_CHANNEL_CANDIDATE",
            "selector_reason": "FULL_HISTORY_DIRECT_SELECTOR_ONLY",
            "ownership": "NOT_ASSIGNED_BY_THIS_TOOL; join cross-TF/ownership artifact separately",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build audit-only per-TL evidence sidecar from state + OHLC.")
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--state", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--input-prefix", default="NVT", choices=["NVT", "NORMAL"])
    ap.add_argument("--include-history", action="store_true")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    state_path = Path(args.state)
    state = load_json(state_path)
    result = build_evidence(
        state=state,
        symbol=args.symbol.strip(),
        input_dir=Path(args.input_dir),
        input_prefix=args.input_prefix,
        include_history=bool(args.include_history),
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": result["status"],
        "line_count": result["line_count"],
        "candidate_join_counts": result["candidate_join_counts"],
        "quality_counts": result["quality_counts"],
        "readiness_counts": result["readiness_counts"],
        "output": str(out),
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS_AUDIT_EVIDENCE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
