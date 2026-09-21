from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

ROLES = ("TL", "CH", "TL_ZONE_EDGE", "CH_ZONE_EDGE")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mt4_time(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%Y.%m.%d %H:%M:%S")


def points(line: dict, role: str) -> tuple[float, float]:
    p1 = float(line["anchor1_price"])
    p2 = float(line["anchor2_price"])
    offset = float(line["ch_offset"])
    width = float(line["zone_width"])
    direction = line["direction"]
    if role == "TL":
        return p1, p2
    if role == "CH":
        return p1 + offset, p2 + offset
    if role == "TL_ZONE_EDGE":
        z = width if direction == "RISING" else -width
        return p1 + z, p2 + z
    if role == "CH_ZONE_EDGE":
        z = -width if direction == "RISING" else width
        return p1 + offset + z, p2 + offset + z
    raise ValueError(role)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build frozen 09/19 reference drawing with stable numbering.")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--diagnostic", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    diagnostic_path = Path(args.diagnostic)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = load_json(manifest_path)
    diagnostic = load_json(diagnostic_path)
    selected_refs = set(diagnostic.get("production_600_display_selected_refs") or [])
    suppressed_refs = {
        line["reference_id"]
        for line in payload.get("lines", [])
        if (line.get("display_override") or {}).get("status") == "SUPPRESSED"
    }
    selected_refs = selected_refs - suppressed_refs
    result_by_ref = {
        row["reference_id"]: row for row in diagnostic.get("results", [])
    }
    if not selected_refs:
        raise ValueError("no selected 09/19 reference families remain after display overrides")

    rows = []
    index_rows = []
    for line in payload["lines"]:
        rid = line["reference_id"]
        if rid not in selected_refs:
            continue
        tf = line["timeframe"]
        level = line["structure_level"]
        level_code = "L" if level == "LARGE_DOW" else "M"
        for role in ROLES:
            if role in ("TL_ZONE_EDGE", "CH_ZONE_EDGE") and abs(float(line["zone_width"])) <= 1e-12:
                continue
            p1, p2 = points(line, role)
            oid = f"{rid}_SRC_{tf}_{level_code}_{role}"
            rows.append([
                oid,
                payload["symbol"],
                tf,
                level,
                role,
                mt4_time(line["anchor1_time"]),
                f"{p1:.8f}",
                mt4_time(line["anchor2_time"]),
                f"{p2:.8f}",
                "REFERENCE",
                str(line["generation"]),
                line["status"],
                "RAY_RIGHT",
            ])
        diag = result_by_ref.get(rid) or {}
        p600 = diag.get("production_600_replay") or {}
        current = p600.get("current") or {}
        reference_candidate = p600.get("reference_candidate") or {}
        selector_decision = p600.get("selector_trace_decision") or {}
        reference_candidate_audit = p600.get("reference_candidate_audit") or {}
        selector_reason = p600.get("selector_reason")
        selector_reason_status = p600.get("selector_reason_status")
        display_detail = p600.get("display_reason_detail") or {}

        hl_id = f"{rid}-HL"
        hl_kind = reference_candidate.get("decision_hl_kind")
        hl_time = reference_candidate.get("decision_hl_time")
        hl_price = reference_candidate.get("decision_hl_price")
        last_bar = (diagnostic.get("input_coverage", {}).get(tf) or {}).get("last_replay_bar")

        hl_status = "PENDING_HISTORICAL_HL_NOT_REPRODUCED"
        if hl_kind and hl_time and hl_price is not None and last_bar:
            hl_status = "RECOVERED_FROM_600BAR_REFERENCE_CANDIDATE"
            rows.append([
                hl_id,
                payload["symbol"],
                tf,
                f"HL_{hl_kind}",
                "HL",
                mt4_time(hl_time),
                f"{float(hl_price):.8f}",
                mt4_time(last_bar),
                f"{float(hl_price):.8f}",
                "REFERENCE",
                str(line["generation"]),
                "ACTIVE",
                "RAY_RIGHT",
            ])

        index_rows.append({
            "reference_id": rid,
            "reference_no": line["reference_no"],
            "timeframe": tf,
            "structure_level": level,
            "direction": line["direction"],
            "source_line_id": line["line_id"],
            "anchor1_id": f"{rid}-A1",
            "anchor1_time": line["anchor1_time"],
            "anchor1_price": line["anchor1_price"],
            "anchor2_id": f"{rid}-A2",
            "anchor2_time": line["anchor2_time"],
            "anchor2_price": line["anchor2_price"],
            "ch_offset": line["ch_offset"],
            "zone_width": line["zone_width"],
            "hl_id": hl_id,
            "hl_status": hl_status,
            "hl_kind": hl_kind,
            "hl_time": hl_time,
            "hl_price": float(hl_price) if hl_price is not None else None,
            "hl_break_time": reference_candidate.get("hl_break_time"),
            "hl_break_mode": reference_candidate.get("hl_break_mode"),
            "reference_candidate_id": reference_candidate.get("candidate_id"),
            "reference_candidate_turn_span": reference_candidate.get("turn_span"),
            "reference_candidate_tl_contacts": reference_candidate.get("tl_contacts"),
            "reference_candidate_ch_contacts": reference_candidate.get("ch_contacts"),
            "reference_candidate_unbroken_close": reference_candidate.get("unbroken_close"),
            "selector_reason_status": selector_reason_status,
            "reference_candidate_audit_id": reference_candidate_audit.get("candidate_audit_id"),
            "reference_anchor1_pivot_id": reference_candidate_audit.get("anchor1_pivot_id"),
            "reference_anchor2_pivot_id": reference_candidate_audit.get("anchor2_pivot_id"),
            "reference_channel_anchor_pivot_id": reference_candidate_audit.get("channel_anchor_pivot_id"),
            "selector_candidate_audit_id": selector_decision.get("selected_candidate_audit_id"),
            "selector_native_candidate_id": selector_decision.get("selected_native_candidate_id"),
            "selector_anchor1_pivot_id": selector_decision.get("anchor1_pivot_id"),
            "selector_anchor2_pivot_id": selector_decision.get("anchor2_pivot_id"),
            "selector_priority_order": selector_decision.get("priority_order"),
            "selector_selected_metrics": selector_decision.get("selected_metrics"),
            "selector_reason": selector_reason,
            "display_reason": p600.get("display_reason"),
            "display_reason_detail": display_detail,
        })

    header = [
        "object_id","symbol","timeframe","structure_level","role",
        "t1","p1","t2","p2","generation_role","generation","status","extent",
    ]
    csv_path = outdir / "NVT9_0919_REFERENCE_DRAW.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    hl_recovered = [x["reference_id"] for x in index_rows if x.get("hl_status") == "RECOVERED_FROM_600BAR_REFERENCE_CANDIDATE"]
    hl_pending = [x["reference_id"] for x in index_rows if x.get("hl_status") != "RECOVERED_FROM_600BAR_REFERENCE_CANDIDATE"]

    index_json = outdir / "NVT9_0919_REFERENCE_INDEX.json"
    index_json.write_text(json.dumps({
        "schema": "nvt9-0919-reference-index/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_0919_SELECTED_REFERENCE_WITH_HL_AND_REASON_LINKS",
        "manifest": str(manifest_path),
        "diagnostic": str(diagnostic_path),
        "selected_reference_ids": sorted(selected_refs),
        "suppressed_reference_ids": sorted(suppressed_refs),
        "reference_count": len(index_rows),
        "suppressed_reference_ids": sorted(suppressed_refs),
        "draw_row_count": len(rows),
        "hl_recovered_count": len(hl_recovered),
        "hl_recovered_reference_ids": hl_recovered,
        "hl_pending_count": len(hl_pending),
        "hl_pending_reference_ids": hl_pending,
        "lines": index_rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    txt = [
        "NVT9 09/19 FROZEN REFERENCE INDEX",
        "Audit ID: ID10IQ200",
        "",
    ]
    for x in index_rows:
        txt += [
            f"{x['reference_id']}  {x['timeframe']} {x['structure_level']} {x['direction']}",
            f"  source={x['source_line_id']}",
            f"  A1={x['anchor1_id']} {x['anchor1_time']} {x['anchor1_price']}",
            f"  A2={x['anchor2_id']} {x['anchor2_time']} {x['anchor2_price']}",
            f"  CH offset={x['ch_offset']}  zone={x['zone_width']}",
            f"  HL={x['hl_id']} status={x.get('hl_status')} {x['hl_kind']} {x['hl_time']} {x['hl_price']} break={x['hl_break_time']}",
            f"  Reference candidate={x.get('reference_candidate_id')} audit={x.get('reference_candidate_audit_id')} span={x.get('reference_candidate_turn_span')} TLc={x.get('reference_candidate_tl_contacts')} CHc={x.get('reference_candidate_ch_contacts')} unbroken={x.get('reference_candidate_unbroken_close')}",
            f"  Reference Pivot IDs={x.get('reference_anchor1_pivot_id')} -> {x.get('reference_anchor2_pivot_id')} CH={x.get('reference_channel_anchor_pivot_id')}",
            f"  Selector reason status={x.get('selector_reason_status')}",
            f"  Selector winner={x.get('selector_candidate_audit_id')} native={x.get('selector_native_candidate_id')}",
            f"  Winner Pivot IDs={x.get('selector_anchor1_pivot_id')} -> {x.get('selector_anchor2_pivot_id')}",
            f"  Selector priority={x.get('selector_priority_order')}",
            f"  Selector reason={x.get('selector_reason')}",
            f"  Display reason={x.get('display_reason')} {x.get('display_reason_detail')}",
            "",
        ]
    txt_path = outdir / "NVT9_0919_REFERENCE_INDEX.txt"
    txt_path.write_text("\n".join(txt), encoding="utf-8")

    print(json.dumps({
        "status": "PASS_0919_SELECTED_REFERENCE_WITH_HL_AND_REASON_LINKS",
        "reference_count": len(index_rows),
        "draw_row_count": len(rows),
        "hl_recovered_count": len(hl_recovered),
        "hl_pending_count": len(hl_pending),
        "hl_pending_reference_ids": hl_pending,
        "csv": str(csv_path),
        "index_json": str(index_json),
        "index_txt": str(txt_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
