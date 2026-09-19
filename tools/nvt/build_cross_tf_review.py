from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

TF_ORDER = ("D1", "H4", "H1", "M15")
ADJACENT = (("D1", "H4"), ("H4", "H1"), ("H1", "M15"))


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def line_value(state: dict, t: datetime, channel: bool = False) -> float:
    t1 = dt(state["anchor1_time"])
    t2 = dt(state["anchor2_time"])
    p1 = float(state["anchor1_price"])
    p2 = float(state["anchor2_price"])
    sec = (t2 - t1).total_seconds()
    if sec <= 0:
        raise ValueError(f"bad anchor order: {state['line_id']}")
    slope = (p2 - p1) / sec
    value = p1 + (t - t1).total_seconds() * slope
    if channel:
        value += float(state["ch_offset"])
    return value


def slope_per_day(state: dict) -> float:
    t1 = dt(state["anchor1_time"])
    t2 = dt(state["anchor2_time"])
    sec = (t2 - t1).total_seconds()
    return (float(state["anchor2_price"]) - float(state["anchor1_price"])) / sec * 86400.0


def latest_input_time(path: Path) -> datetime | None:
    if not path.exists():
        return None
    last = None
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            raw = row.get("time") or row.get("Time") or row.get("datetime") or row.get("Datetime")
            if not raw:
                continue
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
                try:
                    last = datetime.strptime(raw[:19], fmt)
                    break
                except Exception:
                    pass
    return last


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def current_sets(state: dict, symbol: str) -> dict[str, list[dict]]:
    result = {tf: [] for tf in TF_ORDER}
    for slot in state.get("slots", {}).values():
        s = slot.get("current")
        if not s or s.get("symbol") != symbol:
            continue
        tf = s.get("timeframe")
        if tf in result:
            result[tf].append(dict(s))
    for tf in result:
        result[tf].sort(key=lambda s: (s.get("structure_level", ""), s.get("line_id", "")))
    return result


def compare(parent: dict, child: dict, eval_end: datetime | None) -> dict:
    eval_start = max(dt(parent["anchor2_time"]), dt(child["anchor2_time"]))
    if eval_end is None or eval_end < eval_start:
        eval_end = eval_start

    p_tl_start = line_value(parent, eval_start)
    c_tl_start = line_value(child, eval_start)
    p_tl_end = line_value(parent, eval_end)
    c_tl_end = line_value(child, eval_end)
    p_ch_start = line_value(parent, eval_start, True)
    c_ch_start = line_value(child, eval_start, True)
    p_ch_end = line_value(parent, eval_end, True)
    c_ch_end = line_value(child, eval_end, True)

    p_slope = slope_per_day(parent)
    c_slope = slope_per_day(child)

    exact_geometry = (
        parent.get("direction") == child.get("direction")
        and parent.get("anchor1_time") == child.get("anchor1_time")
        and float(parent.get("anchor1_price")) == float(child.get("anchor1_price"))
        and parent.get("anchor2_time") == child.get("anchor2_time")
        and float(parent.get("anchor2_price")) == float(child.get("anchor2_price"))
    )

    if parent.get("direction") != child.get("direction"):
        relation = "DISTINCT_DIRECTION_EVIDENCE"
    elif exact_geometry:
        relation = "EXACT_GEOMETRY_SAME_FAMILY"
    else:
        relation = "PENDING_TEACHER_CALIBRATION"

    p_width = abs(float(parent.get("ch_offset", 0.0)))
    c_width = abs(float(child.get("ch_offset", 0.0)))
    scale = max(p_width, c_width, 1e-12)

    return {
        "parent_tf": parent["timeframe"],
        "parent_level": parent["structure_level"],
        "parent_line_id": parent["line_id"],
        "parent_direction": parent["direction"],
        "child_tf": child["timeframe"],
        "child_level": child["structure_level"],
        "child_line_id": child["line_id"],
        "child_direction": child["direction"],
        "direction_match": parent["direction"] == child["direction"],
        "relation_without_threshold": relation,
        "eval_start": eval_start.isoformat(),
        "eval_end": eval_end.isoformat(),
        "parent_slope_price_per_day": p_slope,
        "child_slope_price_per_day": c_slope,
        "slope_abs_diff_price_per_day": abs(p_slope - c_slope),
        "tl_gap_at_eval_start": abs(p_tl_start - c_tl_start),
        "tl_gap_at_eval_end": abs(p_tl_end - c_tl_end),
        "tl_gap_change_abs": abs(abs(p_tl_end - c_tl_end) - abs(p_tl_start - c_tl_start)),
        "ch_gap_at_eval_start": abs(p_ch_start - c_ch_start),
        "ch_gap_at_eval_end": abs(p_ch_end - c_ch_end),
        "max_channel_width_for_scale": scale,
        "tl_gap_end_over_max_channel_width": abs(p_tl_end - c_tl_end) / scale,
        "anchor1_time_diff_hours": abs((dt(parent["anchor1_time"]) - dt(child["anchor1_time"])).total_seconds()) / 3600.0,
        "anchor1_price_diff": abs(float(parent["anchor1_price"]) - float(child["anchor1_price"])),
        "anchor2_time_diff_hours": abs((dt(parent["anchor2_time"]) - dt(child["anchor2_time"])).total_seconds()) / 3600.0,
        "anchor2_price_diff": abs(float(parent["anchor2_price"]) - float(child["anchor2_price"])),
        "parent_ch_offset": float(parent["ch_offset"]),
        "child_ch_offset": float(child["ch_offset"]),
        "note": "Metrics only. No numeric same-family threshold is frozen in V0.1."
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build threshold-free cross-timeframe ownership review matrix.")
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

    state = load_state(state_path)
    sets = current_sets(state, symbol)

    safe = symbol.replace("/", "_").replace(chr(92), "_")
    latest = {tf: latest_input_time(input_dir / f"NORMAL_{safe}_{tf}.csv") for tf in TF_ORDER}

    comparisons = []
    for parent_tf, child_tf in ADJACENT:
        common_latest = min(latest[parent_tf], latest[child_tf]) if latest[parent_tf] and latest[child_tf] else None
        for p in sets[parent_tf]:
            for c in sets[child_tf]:
                comparisons.append(compare(p, c, common_latest))

    comparisons.sort(key=lambda x: (
        0 if x["direction_match"] else 1,
        TF_ORDER.index(x["parent_tf"]),
        x["tl_gap_at_eval_end"],
        x["slope_abs_diff_price_per_day"],
    ))

    payload = {
        "schema": "nvt9-cross-tf-review/0.1",
        "status": "PASS",
        "symbol": symbol,
        "mode": "THRESHOLD_FREE_REVIEW_MATRIX",
        "production_changed": False,
        "renderer_changed": False,
        "snapshot_changed": False,
        "nca_draw_writeback": False,
        "current_line_sets": sets,
        "latest_input_time": {k: (v.isoformat() if v else None) for k, v in latest.items()},
        "comparison_count": len(comparisons),
        "comparisons": comparisons,
        "classification_policy": {
            "exact_geometry": "EXACT_GEOMETRY_SAME_FAMILY",
            "opposite_direction": "DISTINCT_DIRECTION_EVIDENCE",
            "same_direction_non_exact": "PENDING_TEACHER_CALIBRATION",
            "numeric_threshold_frozen": False
        },
        "0919_user_observation_hypotheses": [
            {"source_tf": "H4", "teacher_owner_candidate": "D1"},
            {"source_tf": "H1", "teacher_owner_candidate": "H4"},
            {"source_tf": "M15", "teacher_owner_candidate": "H1"}
        ]
    }

    json_path = outdir / "NVT9_USDJPY_CROSS_TF_0919.json"
    csv_path = outdir / "NVT9_USDJPY_CROSS_TF_0919.csv"
    txt_path = outdir / "NVT9_USDJPY_CROSS_TF_0919.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fields = list(comparisons[0].keys()) if comparisons else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        if fields:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(comparisons)

    lines = [
        "NVT9 CROSS-TF OWNERSHIP REVIEW - 09/19",
        f"symbol={symbol}",
        "mode=THRESHOLD_FREE_REVIEW_MATRIX",
        "",
        "IMPORTANT: numeric distance is review evidence only, not an automatic SAME_FAMILY decision.",
        ""
    ]
    for parent_tf, child_tf in ADJACENT:
        lines.append(f"[{parent_tf} <-> {child_tf}]")
        rows = [x for x in comparisons if x["parent_tf"] == parent_tf and x["child_tf"] == child_tf]
        rows.sort(key=lambda x: (0 if x["direction_match"] else 1, x["tl_gap_at_eval_end"], x["slope_abs_diff_price_per_day"]))
        for x in rows:
            lines.append(
                f"  {x['parent_level']} {x['parent_direction']} <-> {x['child_level']} {x['child_direction']} | "
                f"rel={x['relation_without_threshold']} | TLgapEnd={x['tl_gap_at_eval_end']:.6f} | "
                f"slopeDiff/day={x['slope_abs_diff_price_per_day']:.6f} | A2timeDiff={x['anchor2_time_diff_hours']:.1f}h"
            )
        lines.append("")
    lines += [
        "Next adjudication:",
        "  H4: teacher D1 same-family / H4-local / ambiguous",
        "  H1: teacher H4 same-family / H1-local / ambiguous",
        "  M15: teacher H1 same-family / M15-local / ambiguous",
        "",
        "No Production file was changed."
    ]
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "comparison_count": len(comparisons),
        "json": str(json_path),
        "csv": str(csv_path),
        "txt": str(txt_path),
        "production_changed": False
    }, ensure_ascii=False, indent=2))
    print("")
    print("TOP REVIEW PAIRS")
    for parent_tf, child_tf in ADJACENT:
        rows = [x for x in comparisons if x["parent_tf"] == parent_tf and x["child_tf"] == child_tf]
        rows.sort(key=lambda x: (0 if x["direction_match"] else 1, x["tl_gap_at_eval_end"], x["slope_abs_diff_price_per_day"]))
        print(f"{parent_tf} <-> {child_tf}")
        for x in rows[:4]:
            print(
                f"  {x['parent_level']} <-> {x['child_level']} "
                f"dir={x['parent_direction']}/{x['child_direction']} "
                f"TLgap={x['tl_gap_at_eval_end']:.6f} "
                f"slopeDiff/day={x['slope_abs_diff_price_per_day']:.6f} "
                f"relation={x['relation_without_threshold']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
