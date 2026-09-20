from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from live_draw.market_input import load_ohlc_csv
from live_draw.normal_run import safe_symbol_filename

ROLES = ("TL", "CH", "TL_ZONE_EDGE", "CH_ZONE_EDGE")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mt4_datetime(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%Y.%m.%d %H:%M:%S")


def projected_values(s: dict, at: datetime) -> tuple[float, float]:
    t1 = datetime.fromisoformat(s["anchor1_time"])
    t2 = datetime.fromisoformat(s["anchor2_time"])
    p1 = float(s["anchor1_price"])
    p2 = float(s["anchor2_price"])
    sec = (t2 - t1).total_seconds()
    slope = (p2 - p1) / sec
    tl = p1 + slope * (at - t1).total_seconds()
    ch = tl + float(s["ch_offset"])
    return tl, ch


def channel_distance(price: float, tl: float, ch: float) -> float:
    lo, hi = sorted((tl, ch))
    if lo <= price <= hi:
        return 0.0
    return min(abs(price - lo), abs(price - hi))


def line_points(s: dict, role: str) -> tuple[float, float]:
    p1 = float(s["anchor1_price"])
    p2 = float(s["anchor2_price"])
    offset = float(s["ch_offset"])
    width = float(s["zone_width"])
    direction = s["direction"]

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


def geometry_key(s: dict) -> tuple:
    return (
        s.get("direction"),
        s.get("anchor1_time"),
        round(float(s.get("anchor1_price")), 10),
        s.get("anchor2_time"),
        round(float(s.get("anchor2_price")), 10),
        round(float(s.get("ch_offset")), 10),
        round(float(s.get("zone_width")), 10),
    )


def family_record(s: dict, gen_role: str, display_tf: str, price: float, eval_time: datetime) -> dict:
    tl, ch = projected_values(s, eval_time)
    return {
        "source_tf": s["timeframe"],
        "display_tf": display_tf,
        "line_id": s["line_id"],
        "structure_level": s["structure_level"],
        "generation_role": gen_role.upper(),
        "generation": int(s["generation"]),
        "status": s["status"],
        "direction": s["direction"],
        "anchor1_time": s["anchor1_time"],
        "anchor1_price": float(s["anchor1_price"]),
        "anchor2_time": s["anchor2_time"],
        "anchor2_price": float(s["anchor2_price"]),
        "ch_offset": float(s["ch_offset"]),
        "zone_width": float(s["zone_width"]),
        "projected_tl": tl,
        "projected_ch": ch,
        "current_price": price,
        "distance_to_channel": channel_distance(price, tl, ch),
        "inside_channel": channel_distance(price, tl, ch) == 0.0,
        "_state": s,
    }


def select_source_families(
    candidates: list[dict],
    source_tf: str,
    per_source: int,
) -> list[dict]:
    # Selection is made ONCE on the SOURCE timeframe using the source
    # timeframe's own latest closed bar / current price. The chosen geometry
    # is then copied unchanged to every display chart in Plan B.
    by_geom: dict[tuple, list[dict]] = defaultdict(list)
    for c in candidates:
        if c["source_tf"] != source_tf:
            continue
        by_geom[geometry_key(c["_state"])].append(c)

    deduped = []
    for group in by_geom.values():
        group.sort(key=lambda x: (
            x["distance_to_channel"],
            0 if x["generation_role"] == "CURRENT" else 1,
            0 if x["structure_level"] == "LARGE_DOW" else 1,
            x["line_id"],
        ))
        chosen = group[0]
        chosen["exact_geometry_duplicate_count"] = len(group) - 1
        deduped.append(chosen)

    ranked = sorted(
        deduped,
        key=lambda x: (
            x["distance_to_channel"],
            0 if x["generation_role"] == "CURRENT" else 1,
            0 if x["structure_level"] == "LARGE_DOW" else 1,
            x["line_id"],
        ),
    )
    selected = []
    for c in ranked[:per_source]:
        item = dict(c)
        item["display_reason"] = "SOURCE_TF_NEAREST_FAMILY"
        item["display_roles"] = list(ROLES)
        selected.append(item)
    return selected

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a price-relevant local+parent TF research display preview."
    )
    ap.add_argument("--state", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--input-prefix", default="NVT", choices=["NVT", "NORMAL"])
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    state_path = Path(args.state)
    policy_path = Path(args.policy)
    input_dir = Path(args.input_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    state = load_json(state_path)
    policy = load_json(policy_path)
    display_sources = policy.get("display_sources") or {}
    vis = policy.get("visibility_policy") or {}
    per_source = int(vis.get("near_price_family_per_source_tf", 1))
    context_max = int(vis.get("far_direction_context_max_families", 0))

    if state.get("schema") != "nca-live-state/1.0":
        raise ValueError(f"unexpected state schema: {state.get('schema')}")
    research_status = state.get("research_status")
    if research_status is not None and research_status != "PASS_DEEP_LIFECYCLE_STATE":
        raise ValueError(f"research lifecycle state is not PASS: {research_status}")

    symbol = state.get("symbol") or policy.get("symbol")
    safe = safe_symbol_filename(symbol)

    latest = {}
    missing = []
    for display_tf in display_sources:
        src = input_dir / f"{args.input_prefix}_{safe}_{display_tf}.csv"
        if not src.exists():
            missing.append(str(src))
            continue
        bars = load_ohlc_csv(src)
        if not bars:
            missing.append(str(src))
            continue
        latest[display_tf] = {
            "time": bars[-1].time,
            "close": float(bars[-1].close),
        }
    if missing:
        raise ValueError(f"missing display timeframe input: {missing}")

    rows = []
    audit_rows = []
    display_counts = Counter()
    selected_family_counts = Counter()
    selected_source_counts: dict[str, Counter] = {}
    source_selection: dict[str, list[dict]] = {}

    slots = state.get("slots") or {}
    source_to_display = policy.get("source_to_display_tfs") or {}
    if not source_to_display:
        raise ValueError("policy missing source_to_display_tfs")

    # 1) Select the source family on its OWN timeframe.
    for source_tf, display_tfs in source_to_display.items():
        if source_tf not in latest:
            raise ValueError(f"missing latest source market data for {source_tf}")
        eval_time = latest[source_tf]["time"]
        current_price = latest[source_tf]["close"]
        candidates = []
        for _, slot in sorted(slots.items()):
            for gen_role in ("previous", "current"):
                s = slot.get(gen_role)
                if not s or s.get("timeframe") != source_tf:
                    continue
                candidates.append(family_record(s, gen_role, source_tf, current_price, eval_time))

        selected = select_source_families(candidates, source_tf, per_source)
        if len(selected) < per_source:
            raise ValueError(
                f"source selection missing: {source_tf} selected={len(selected)} expected={per_source}"
            )
        source_selection[source_tf] = selected

    # 2) Copy the EXACT selected source geometry to every Plan-B display TF.
    for source_tf, display_tfs in source_to_display.items():
        for fam in source_selection[source_tf]:
            s = fam["_state"]
            geometry_signature = geometry_key(s)
            for display_tf in display_tfs:
                selected_source_counts.setdefault(display_tf, Counter())
                selected_source_counts[display_tf][source_tf] += 1
                selected_family_counts[display_tf] += 1

                for role in fam["display_roles"]:
                    p1, p2 = line_points(s, role)
                    level_code = "L" if s["structure_level"] == "LARGE_DOW" else "M"
                    gen_role_code = "C" if fam["generation_role"] == "CURRENT" else "P"
                    oid = (
                        f"SRC_{source_tf}_DST_{display_tf}_"
                        f"{level_code}_G{s['generation']}_{gen_role_code}_{role}"
                    )
                    rows.append([
                        oid, s["symbol"], display_tf, s["structure_level"], role,
                        mt4_datetime(s["anchor1_time"]), f"{p1:.8f}",
                        mt4_datetime(s["anchor2_time"]), f"{p2:.8f}",
                        fam["generation_role"], str(s["generation"]), s["status"], "RAY_RIGHT",
                    ])
                    display_counts[display_tf] += 1

                audit_rows.append({
                    **{k: v for k, v in fam.items() if k != "_state"},
                    "source_selection_tf": source_tf,
                    "display_tf": display_tf,
                    "geometry_signature": list(geometry_signature),
                    "copied_without_reselection": True,
                })

    header = [
        "object_id","symbol","timeframe","structure_level","role",
        "t1","p1","t2","p2","generation_role","generation","status","extent",
    ]
    csv_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919.csv"
    audit_path = outdir / "NVT9_USDJPY_TF_MAPPED_PREVIEW_0919_AUDIT.json"

    # Match Production snapshot encoding: no UTF-8 BOM.
    # MT4 opens this file with FILE_ANSI; a BOM would prefix the first header
    # token and make ReadAndValidateHeader() reject "object_id".
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    payload = {
        "schema": "nvt9-tf-mapped-preview/0.2",
        "status": "PASS_TF_MAPPED_PREVIEW",
        "audit_id": "ID10IQ200",
        "source_state": str(state_path),
        "source_state_mode": (
            "NORMAL_RUN_LIVE_STATE" if args.input_prefix == "NORMAL"
            else "DEEP_NVT_RESEARCH_STATE"
        ),
        "input_prefix": args.input_prefix,
        "display_policy": str(policy_path),
        "display_sources": display_sources,
        "source_to_display_tfs": source_to_display,
        "source_selection": {
            tf: [
                {
                    **{k: v for k, v in fam.items() if k != "_state"},
                    "geometry_signature": list(geometry_key(fam["_state"])),
                }
                for fam in fams
            ]
            for tf, fams in source_selection.items()
        },
        "latest_display_prices": {
            tf: {"time": x["time"].isoformat(), "close": x["close"]} for tf, x in latest.items()
        },
        "candidate_family_counts": dict(candidate_counts),
        "selected_family_counts": dict(selected_family_counts),
        "selected_source_counts": {
            tf: dict(counts) for tf, counts in selected_source_counts.items()
        },
        "display_row_counts": dict(display_counts),
        "selected_families": audit_rows,
        "object_name_policy": {
            "renderer_prefix": "NVT9_TFMAP__",
            "max_full_object_name_length": max(
                [len("NVT9_TFMAP__" + row[0]) for row in rows] or [0]
            ),
            "mt4_name_limit_guard": 63,
        },
        "selection_policy": {
            "near_price_family_per_source_tf": per_source,
            "far_direction_context_max_families": context_max,
            "fixed_pip_threshold_used": False,
            "atr_threshold_used": False,
            "far_direction_roles": ["TL", "CH"],
        },
        "semantics": {
            "structural_owner_tf": "SOURCE_TF",
            "display_tf": "CHART_TF",
            "h1_h4_nonexact_merge": "NOT_AUTOMATIC",
        },
        "production_changed": False,
        "production_snapshot_changed": False,
        "production_renderer_changed": False,
        "nca_draw_writeback": False,
        "trade_authority": False,
    }
    source_presence_problems = []
    for source_tf, display_tfs in source_to_display.items():
        for display_tf in display_tfs:
            counts = selected_source_counts.get(display_tf, Counter())
            if counts.get(source_tf, 0) < per_source:
                source_presence_problems.append({
                    "display_tf": display_tf,
                    "missing_source_tf": source_tf,
                    "reason": "PLAN_B_ASSIGNED_SOURCE_NOT_COPIED",
                })
    payload["source_presence_problems"] = source_presence_problems
    if source_presence_problems:
        payload["status"] = "FAIL_PLAN_B_SOURCE_PRESENCE"

    audit_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if source_presence_problems:
        raise ValueError(f"Plan B source presence failure: {source_presence_problems}")

    if payload["object_name_policy"]["max_full_object_name_length"] > payload["object_name_policy"]["mt4_name_limit_guard"]:
        raise ValueError(
            "TFMap MT4 object name exceeds 63 characters: "
            f"{payload['object_name_policy']['max_full_object_name_length']}"
        )

    print(json.dumps({
        "status": payload["status"],
        "display_sources": display_sources,
        "selected_family_counts": dict(selected_family_counts),
        "selected_source_counts": {
            tf: dict(counts) for tf, counts in selected_source_counts.items()
        },
        "display_row_counts": dict(display_counts),
        "csv": str(csv_path),
        "audit": str(audit_path),
        "production_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
