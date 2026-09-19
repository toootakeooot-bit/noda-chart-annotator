from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.geometry import build_channel_candidates, select_large_mid
from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import TFS, normal_input_name, safe_symbol_filename
from live_draw.turn_detector import detect_turns

ROLES = ("TL", "CH", "TL_ZONE_EDGE", "CH_ZONE_EDGE")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def selector_rule(level: str) -> str:
    if level == "LARGE_DOW":
        return (
            "close-unbroken candidates only; select by turn_span, then CH contacts, "
            "then TL contacts, then gentler slope"
        )
    return (
        "smaller/recent candidate inside active Large context; select by latest anchor2, "
        "then CH contacts, then TL contacts, then gentler slope"
    )


def role_reason(role: str) -> str:
    return {
        "TL": "trend line through selected anchor1 and anchor2",
        "CH": "parallel channel using opposite-side pivot offset; CH contacts are maximized before latest CH-anchor tie-break",
        "TL_ZONE_EDGE": "parallel TL zone edge; width is anchor1 candle wick-to-body distance",
        "CH_ZONE_EDGE": "parallel CH zone edge using the same zone width as TL side",
    }.get(role, "unknown role")


def visibility_reason(generation_role: str) -> str:
    if generation_role == "CURRENT":
        return "current selected generation"
    return "immediately previous generation retained by BASELINE_V1 lifecycle and rendered as reference"


def candidate_payload(c) -> dict:
    return {
        "candidate_id": c.id_key,
        "direction": c.direction,
        "anchor1_time": c.anchor1.time.isoformat(),
        "anchor1_price": c.anchor1.price,
        "anchor1_kind": c.anchor1.kind,
        "anchor1_confirmed_by_time": c.anchor1.confirmed_by_time.isoformat(),
        "anchor2_time": c.anchor2.time.isoformat(),
        "anchor2_price": c.anchor2.price,
        "anchor2_kind": c.anchor2.kind,
        "anchor2_confirmed_by_time": c.anchor2.confirmed_by_time.isoformat(),
        "turn_span": c.turn_span,
        "tl_contacts": c.tl_contacts,
        "ch_contacts": c.ch_contacts,
        "unbroken_close": c.unbroken_close,
        "slope_per_second": c.slope_per_second,
        "ch_anchor_time": c.ch_anchor.time.isoformat(),
        "ch_anchor_price": c.ch_anchor.price,
        "ch_offset": c.ch_offset,
        "zone_width": c.zone_width,
    }


def find_transition(tf_audit: dict, line_id: str, level: str, generation: int):
    for tr in tf_audit.get("transitions", []):
        if (
            tr.get("line_id") == line_id
            and tr.get("level") == level
            and int(tr.get("generation", -1)) == int(generation)
        ):
            return tr
    return None


def reconstruct_evidence(bars, symbol: str, tf: str, level: str, tr: dict) -> dict:
    end_index = int(tr["closed_bar_index"])
    if end_index < 0 or end_index >= len(bars):
        return {"status": "ERROR", "reason": "closed_bar_index outside exported history"}

    prefix = bars[: end_index + 1]
    turns = detect_turns(prefix)
    candidates = build_channel_candidates(prefix, turns.pivots)
    large, mid, class_audit = select_large_mid(symbol, tf, candidates)
    selected = large if level == "LARGE_DOW" else mid

    if selected is None:
        return {
            "status": "ERROR",
            "reason": "no selected structure when replaying transition",
            "closed_bar_index": end_index,
            "candidate_count": len(candidates),
        }

    if level == "LARGE_DOW":
        eligible = [c for c in candidates if c.unbroken_close]
    else:
        if large is None:
            eligible = []
        else:
            lc = large.candidate
            eligible = [
                c for c in candidates
                if c.id_key != lc.id_key
                and c.anchor1.time >= lc.anchor1.time
                and c.turn_span < lc.turn_span
            ]

    recorded = tr.get("candidate_id")
    actual = selected.candidate.id_key
    return {
        "status": "PASS" if recorded == actual else "MISMATCH",
        "closed_bar_index": end_index,
        "closed_bar_time": tr.get("closed_bar_time"),
        "recorded_candidate_id": recorded,
        "reconstructed_candidate_id": actual,
        "candidate_id_match": recorded == actual,
        "confirmed_turn_count": len(turns.pivots),
        "all_candidate_count": len(candidates),
        "eligible_pool_count": len(eligible),
        "selector_rule": selector_rule(level),
        "selector_audit": class_audit,
        "selected_candidate": candidate_payload(selected.candidate),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Explain every published NCA drawing row.")
    ap.add_argument("--symbol", default="USDJPY#")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    symbol = args.symbol.strip()
    safe = safe_symbol_filename(symbol)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    snapshot_path = output_dir / f"NORMAL_{safe}_live_snapshot.csv"
    state_path = output_dir / f"NORMAL_{safe}_live_state.json"
    audit_path = output_dir / f"NORMAL_{safe}_run_audit.json"

    missing = [str(p) for p in (snapshot_path, state_path, audit_path) if not p.exists()]
    if missing:
        print(json.dumps({"status": "FAIL", "missing": missing}, ensure_ascii=False, indent=2))
        return 2

    state = load_json(state_path)
    run_audit = load_json(audit_path)
    with snapshot_path.open("r", encoding="utf-8-sig", newline="") as f:
        snapshot_rows = list(csv.DictReader(f))

    bars_by_tf = {}
    for tf in TFS:
        src = input_dir / normal_input_name(symbol, tf)
        if src.exists():
            bars_by_tf[tf] = load_ohlc_csv(src)

    state_by_line_id = {}
    for slot in state.get("slots", {}).values():
        for gen_role in ("previous", "current"):
            s = slot.get(gen_role)
            if s:
                state_by_line_id[s["line_id"]] = {**s, "generation_role": gen_role.upper()}

    evidence_cache = {}
    rows = []
    warnings = []

    for snap in snapshot_rows:
        if snap.get("symbol") != symbol:
            continue
        tf = snap["timeframe"]
        role = snap["role"]
        object_id = snap["object_id"]
        line_id = object_id.split("__", 1)[0]
        s = state_by_line_id.get(line_id)
        if not s:
            warnings.append({"object_id": object_id, "reason": "STATE_LINE_NOT_FOUND"})
            continue

        level = s["structure_level"]
        generation = int(s["generation"])
        cache_key = (tf, line_id, generation)
        if cache_key not in evidence_cache:
            tf_audit = (run_audit.get("timeframes") or {}).get(tf, {})
            tr = find_transition(tf_audit, line_id, level, generation)
            if tr is None:
                evidence = {"status": "NO_TRANSITION_EVIDENCE"}
            elif tf not in bars_by_tf:
                evidence = {"status": "NO_INPUT_BARS"}
            else:
                evidence = reconstruct_evidence(bars_by_tf[tf], symbol, tf, level, tr)
            evidence_cache[cache_key] = evidence
            if evidence.get("status") not in ("PASS",):
                warnings.append({
                    "timeframe": tf,
                    "line_id": line_id,
                    "generation": generation,
                    "evidence": evidence,
                })
        else:
            evidence = evidence_cache[cache_key]

        cand = evidence.get("selected_candidate") or {}
        rows.append({
            "timeframe": tf,
            "structure_level": level,
            "generation_role": s["generation_role"],
            "generation": generation,
            "line_id": line_id,
            "object_id": object_id,
            "role": role,
            "status": s["status"],
            "direction": s["direction"],
            "anchor1_time": s["anchor1_time"],
            "anchor1_price": s["anchor1_price"],
            "anchor2_time": s["anchor2_time"],
            "anchor2_price": s["anchor2_price"],
            "transition_time": evidence.get("closed_bar_time", ""),
            "candidate_id": evidence.get("recorded_candidate_id", ""),
            "evidence_status": evidence.get("status", ""),
            "eligible_pool_count": evidence.get("eligible_pool_count", ""),
            "all_candidate_count": evidence.get("all_candidate_count", ""),
            "turn_span": cand.get("turn_span", ""),
            "tl_contacts": cand.get("tl_contacts", ""),
            "ch_contacts": cand.get("ch_contacts", ""),
            "unbroken_close": cand.get("unbroken_close", ""),
            "slope_per_second": cand.get("slope_per_second", ""),
            "ch_anchor_time": cand.get("ch_anchor_time", ""),
            "ch_anchor_price": cand.get("ch_anchor_price", ""),
            "ch_offset": s["ch_offset"],
            "zone_width": s["zone_width"],
            "selector_rule": selector_rule(level),
            "visibility_reason": visibility_reason(s["generation_role"]),
            "role_reason": role_reason(role),
        })

    report = {
        "schema": "nvt9-draw-rationale/1.0",
        "status": "PASS" if not warnings else "PASS_WITH_EVIDENCE_WARNINGS",
        "symbol": symbol,
        "snapshot_rows": len(rows),
        "display_formula": "2 structure levels x current+previous x 4 roles = up to 16 objects per timeframe",
        "selection_semantics_changed": False,
        "renderer_changed": False,
        "nca_draw_behavior_changed": False,
        "timeframes": {},
        "warnings": warnings,
    }

    for tf in TFS:
        tf_rows = [r for r in rows if r["timeframe"] == tf]
        sets = {}
        for r in tf_rows:
            k = (r["line_id"], r["generation_role"], r["generation"])
            sets.setdefault(k, {
                "line_id": r["line_id"],
                "structure_level": r["structure_level"],
                "generation_role": r["generation_role"],
                "generation": r["generation"],
                "status": r["status"],
                "direction": r["direction"],
                "anchor1_time": r["anchor1_time"],
                "anchor1_price": r["anchor1_price"],
                "anchor2_time": r["anchor2_time"],
                "anchor2_price": r["anchor2_price"],
                "roles": [],
                "selection_evidence": evidence_cache.get((tf, r["line_id"], r["generation"]), {}),
            })
            sets[k]["roles"].append(r["role"])
        report["timeframes"][tf] = {
            "published_rows": len(tf_rows),
            "line_set_count": len(sets),
            "line_sets": list(sets.values()),
        }

    json_path = output_dir / f"NVT9_{safe}_draw_rationale.json"
    csv_path = output_dir / f"NVT9_{safe}_draw_rationale.csv"
    txt_path = output_dir / f"NVT9_{safe}_draw_rationale.txt"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fields = [
        "timeframe","structure_level","generation_role","generation","line_id","object_id",
        "role","status","direction","anchor1_time","anchor1_price","anchor2_time","anchor2_price",
        "transition_time","candidate_id","evidence_status","eligible_pool_count","all_candidate_count",
        "turn_span","tl_contacts","ch_contacts","unbroken_close","slope_per_second",
        "ch_anchor_time","ch_anchor_price","ch_offset","zone_width",
        "selector_rule","visibility_reason","role_reason",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})

    summary = [
        "NVT9 DRAW RATIONALE",
        f"symbol={symbol}",
        f"status={report['status']}",
        f"snapshot_rows={report['snapshot_rows']}",
        "",
        "Why 16 objects/timeframe:",
        "2 structure levels x current+previous x 4 roles = 16",
        "roles = TL / CH / TL_ZONE_EDGE / CH_ZONE_EDGE",
        "",
    ]
    for tf in TFS:
        s = report["timeframes"][tf]
        summary.append(f"[{tf}] rows={s['published_rows']} line_sets={s['line_set_count']}")
        for item in s["line_sets"]:
            ev = item.get("selection_evidence") or {}
            c = ev.get("selected_candidate") or {}
            summary.append(
                f"  {item['structure_level']} {item['generation_role']} G{item['generation']} "
                f"{item['direction']} A1={item['anchor1_time']}@{item['anchor1_price']} "
                f"A2={item['anchor2_time']}@{item['anchor2_price']} "
                f"span={c.get('turn_span','')} TLc={c.get('tl_contacts','')} "
                f"CHc={c.get('ch_contacts','')} evidence={ev.get('status','')}"
            )
        summary.append("")
    txt_path.write_text("\n".join(summary), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "symbol": symbol,
        "snapshot_rows": report["snapshot_rows"],
        "json": str(json_path),
        "csv": str(csv_path),
        "txt": str(txt_path),
        "warning_count": len(warnings),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
